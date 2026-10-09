"""
Convert images dialog: population image sets (OpenDEP Control, OpenDEP Compute 1.x) -> grayness-factor spectra.

Choose a folder (one experiment, or a folder holding several); check the grid of each set on its image (left click
adds a line, dragging a line moves it, right click removes the nearest line; "Snap to edges" moves new and dragged
lines to the nearest edge of the profile); convert the ticked sets into the project.
"""
from dataclasses import replace
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
                             QListWidget,
                             QListWidgetItem, QMessageBox, QProgressBar, QSpinBox, QSplitter, QVBoxLayout, QWidget)

from src.conversion import control_grid as cg
from src.conversion.population import (ALIGNMENTS, BKG_REGIONS, GRID_CONTROL, GridSettings, ImageSet,
                                       average_profile, convert, darker_first, detect_grid, find_image_sets, grid_for,
                                       lines_to_grid, read_image, snap_line)
from ui.context import AppContext
from src.report.plotting import style_axes
from ui.widgets import PlotCanvas, button, card, label

LIGHT = (('Bright-field (cells darker than the medium)', True), ('Fluorescence (cells brighter)', False))
ELECTRODES = (('Regions 1, 3, 5, …', True), ('Regions 2, 4, 6, …', False))


class ConvertThread(QThread):
    """
    Converts the ticked sets off the GUI thread.
    """
    progress = pyqtSignal(int, int, str)
    finished_set = pyqtSignal(object, object)               # ImageSet, ImportResult
    failed = pyqtSignal(str)

    def __init__(self, jobs: list[tuple[ImageSet, GridSettings]]) -> None:
        super().__init__()
        self.jobs = jobs

    def run(self) -> None:
        for image_set, grid in self.jobs:
            try:
                result, _ = convert(image_set, grid,
                                    lambda done, total, n=image_set.name: self.progress.emit(done, total, n))
                self.finished_set.emit(image_set, result)
            except (ValueError, OSError) as e:                 # shown to the user, never swallowed
                self.failed.emit(f'{image_set.name}: {e}')


class ConvertDialog(QDialog):
    """
    Image sets -> spectra.
    """

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Convert images')
        self.resize(1300, 820)
        self.ctx = ctx
        self.sets: list[ImageSet] = []
        self.grids: dict[int, GridSettings] = {}             # per set index, as edited
        self.lines: dict[int, list[int]] = {}                # raw px of the lines of edited / detected grids
        self.profiles: dict[int, np.ndarray] = {}            # averaged profiles (for snapping), computed on demand
        self.messages: list[str] = []
        self.converted = 0
        self._thread: ConvertThread | None = None
        self._image: np.ndarray | None = None
        self._loading = False

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(label('Folder'))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText('An experiment folder (with _DATA), or a folder holding several')
        self.folder_edit.returnPressed.connect(lambda: self.open_folder(self.folder_edit.text()))
        row.addWidget(self.folder_edit, 1)
        browse = button('Browse…')
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        lay.addLayout(row)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_preview())
        splitter.setSizes([380, 920])
        lay.addWidget(splitter, 1)
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.hide()
        bottom.addWidget(self.progress, 1)
        self.convert_button = button('Convert ticked sets', 'primary', None, 'Compute the spectra and add them to '
                                     'the project')
        self.convert_button.clicked.connect(self.run_conversion)
        close = button('Close')
        close.clicked.connect(self.accept)
        bottom.addWidget(self.convert_button)
        bottom.addWidget(close)
        lay.addLayout(bottom)
        self._set_enabled(False)

    ## Layout ##

    def _build_left(self) -> QWidget:
        frame, lay = card(spacing=8)
        lay.addWidget(label('Image sets', 'section'))
        self.set_list = QListWidget()
        self.set_list.currentRowChanged.connect(self._show_set)
        lay.addWidget(self.set_list, 1)
        lay.addWidget(label('Grid and sampling of the selected set', 'section'))
        form = QFormLayout()
        self.grid_label = label('', 'muted', wrap=True)
        form.addRow('Grid', self.grid_label)
        self.light_combo = QComboBox()
        for text, value in LIGHT:
            self.light_combo.addItem(text, value)
        form.addRow('Light', self.light_combo)
        self.alignment_combo = QComboBox()
        self.alignment_combo.addItems(ALIGNMENTS)
        self.alignment_combo.setToolTip('Direction of the electrode edges in the image')
        form.addRow('Edges', self.alignment_combo)
        self.electrode_combo = QComboBox()
        for text, value in ELECTRODES:
            self.electrode_combo.addItem(text, value)
        self.electrode_combo.setToolTip('Which regions between consecutive lines are electrodes (numbered from the '
                                        'left / top of the image)')
        form.addRow('Electrodes', self.electrode_combo)
        self.edge_spin = QSpinBox()
        self.edge_spin.setRange(0, 50)
        self.edge_spin.setToolTip('Half-width (px) sampled around each line')
        form.addRow('Edge width (px)', self.edge_spin)
        self.bkg_spin = QSpinBox()
        self.bkg_spin.setRange(1, 200)
        self.bkg_spin.setToolTip('Width (px) of each background window, at the middle of the regions')
        form.addRow('Background width (px)', self.bkg_spin)
        self.region_combo = QComboBox()
        self.region_combo.addItems(BKG_REGIONS)
        form.addRow('Background region', self.region_combo)
        lay.addLayout(form)
        for w in (self.light_combo, self.electrode_combo, self.region_combo):
            w.currentIndexChanged.connect(self._on_settings)
        for w in (self.edge_spin, self.bkg_spin):
            w.valueChanged.connect(self._on_settings)
        self.alignment_combo.currentIndexChanged.connect(self._on_alignment)
        row = QHBoxLayout()
        self.detect_button = button('Detect lines again', None, None, 'Replace the lines by detected ones (from the '
                                    'edges image when there is one, otherwise from the averaged images)')
        self.detect_button.clicked.connect(self.redetect)
        self.snap_check = QCheckBox('Snap to edges')
        self.snap_check.setChecked(True)
        self.snap_check.setToolTip('New and dragged lines move to the nearest edge of the profile. Untick to place '
                                   'a line exactly where you click or release it.')
        row.addWidget(self.detect_button)
        row.addWidget(self.snap_check)
        row.addStretch(1)
        lay.addLayout(row)
        return frame

    def _build_preview(self) -> QWidget:
        frame, lay = card(spacing=6)
        lay.addWidget(label('Check the grid: lines on the electrode edges, electrodes shaded. Drag a line to move it, '
                            'left click elsewhere adds one, right click removes the nearest one. On the image or on '
                            'the profile below it.', 'muted', wrap=True))
        self.canvas = PlotCanvas(8, 6)
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self._drag: int | None = None                   # index of the line being dragged
        self._line_artists: list[tuple] = []            # (image line, profile line) per line, as drawn
        self._image_ax = self._profile_ax = None
        lay.addWidget(self.canvas, 1)
        return frame

    def _set_enabled(self, on: bool) -> None:
        for w in (self.light_combo, self.alignment_combo, self.electrode_combo, self.edge_spin, self.bkg_spin,
                  self.region_combo, self.detect_button, self.snap_check, self.convert_button):
            w.setEnabled(on)

    ## Sets ##

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Folder with image sets', self.folder_edit.text())
        if folder:
            self.open_folder(folder)

    def open_folder(self, folder: str) -> int:
        """Find the image sets in a folder; returns how many."""
        self.folder_edit.setText(folder)
        self.sets = find_image_sets(folder) if folder and Path(folder).is_dir() else []
        self.grids, self.lines, self.profiles = {}, {}, {}
        self.set_list.clear()
        for s in self.sets:
            item = QListWidgetItem(f'{s.name}   ({len(s.data)} images{", background" if s.background else ""})')
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.set_list.addItem(item)
        self._set_enabled(bool(self.sets))
        if self.sets:
            self.set_list.setCurrentRow(0)
        else:
            self.canvas.clear()
            self.canvas.draw_idle()
            QMessageBox.information(self, 'Convert images', 'No image set found: a set is a folder with a _DATA '
                                    'subfolder of images named ..._<frequency>Hz.')
        return len(self.sets)

    def grid(self, index: int) -> GridSettings:
        """The grid of a set (Control's, or detected), created on first use."""
        if index not in self.grids:
            s = self.sets[index]
            try:
                self.grids[index] = grid_for(s, self.alignment_combo.currentText())
            except ValueError as e:
                self.messages.append(f'{s.name}: {e}')
                self.grids[index] = GridSettings([], [], self.alignment_combo.currentText(), source='none')
        return self.grids[index]

    def _show_set(self, index: int) -> None:
        if index < 0 or index >= len(self.sets):
            return
        g = self.grid(index)
        self._loading = True
        self.light_combo.setCurrentIndex(0 if g.invert_sign else 1)
        self.alignment_combo.setCurrentText(g.alignment)
        self.edge_spin.setValue(g.edge_width)
        self.bkg_spin.setValue(g.bkg_width)
        self.region_combo.setCurrentText(g.bkg_region)
        self._loading = False
        self._image = read_image(self.sets[index].preview_image())
        self._draw()

    def _axis_len(self) -> int:
        g = self.grids[self.set_list.currentRow()]
        return self._image.shape[1] if g.alignment == 'Vertical' else self._image.shape[0]

    def current_lines(self) -> list[int]:
        """Line positions (raw px) of the selected set."""
        i = self.set_list.currentRow()
        if i in self.lines:
            return self.lines[i]
        return self.grids[i].edge_px(self._axis_len())

    ## Editing ##

    def _on_settings(self) -> None:
        if self._loading or self.set_list.currentRow() < 0:
            return
        i = self.set_list.currentRow()
        g = self.grids[i]
        self.grids[i] = replace(g, invert_sign=self.light_combo.currentData(), edge_width=self.edge_spin.value(),
                                bkg_width=self.bkg_spin.value(), bkg_region=self.region_combo.currentText())
        if self.sender() is self.electrode_combo:
            self.set_lines(self.current_lines(), keep_parity=False)
        self._draw()

    def _on_alignment(self) -> None:
        if not self._loading and self.set_list.currentRow() >= 0:
            self.redetect()

    def _profile(self) -> np.ndarray:
        """Averaged profile of the selected set (cells average out, edges stay)."""
        i = self.set_list.currentRow()
        alignment = self.alignment_combo.currentText()
        if (i, alignment) not in self.profiles:
            self.profiles[(i, alignment)] = average_profile(self.sets[i], alignment)
        return self.profiles[(i, alignment)]

    def set_lines(self, lines: list[int], keep_parity: bool = True) -> None:
        """Replace the lines of the selected set (raw px); electrodes alternate between them."""
        i = self.set_list.currentRow()
        lines = sorted(set(int(x) for x in lines))
        self.lines[i] = lines
        old = self.grids[i]
        first = self.electrode_combo.currentData()
        if keep_parity and len(lines) >= 2:
            first = darker_first(self._profile(), lines)
            self._loading = True
            self.electrode_combo.setCurrentIndex(0 if first else 1)
            self._loading = False
        new = lines_to_grid(lines, self._axis_len(), self.alignment_combo.currentText(), first,
                            'edited' if old.source != 'none' else 'placed by hand')
        self.grids[i] = replace(new, edge_width=old.edge_width, bkg_width=old.bkg_width,
                                bkg_region=old.bkg_region, invert_sign=old.invert_sign)

    def redetect(self) -> None:
        i = self.set_list.currentRow()
        try:
            g = detect_grid(self.sets[i], self.alignment_combo.currentText())
        except ValueError as e:
            QMessageBox.information(self, 'Detect lines', str(e))
            return
        old = self.grids[i]
        self.grids[i] = replace(g, edge_width=old.edge_width, bkg_width=old.bkg_width, bkg_region=old.bkg_region,
                                invert_sign=old.invert_sign)
        self.lines.pop(i, None)
        self._draw()

    def _position(self, event) -> float | None:
        """Position (raw px along the axis across the lines) of a mouse event on the image or the profile."""
        if event.inaxes is None or event.xdata is None or self.set_list.currentRow() < 0:
            return None
        if event.inaxes is self._profile_ax:
            return event.xdata                          # the profile's x axis is always the position
        if event.inaxes is self._image_ax:
            vertical = self.grids[self.set_list.currentRow()].alignment == 'Vertical'
            return event.xdata if vertical else event.ydata
        return None

    def _placed(self, pos: float) -> int:
        """Where a new or dragged line lands: the nearest edge with Snap on, else exactly there."""
        n = self._axis_len()
        x = snap_line(self._profile(), pos) if self.snap_check.isChecked() else round(pos)
        return int(min(max(x, 0), n - 1))

    def _on_click(self, event) -> None:
        pos = self._position(event)
        if pos is None:
            return
        lines = list(self.current_lines())
        if event.button == 1:
            # On (or very near) a line: drag it; elsewhere: a new line
            tolerance = max(3.0, 0.012 * self._axis_len())
            near = int(np.argmin([abs(x - pos) for x in lines])) if lines else None
            if near is not None and abs(lines[near] - pos) <= tolerance:
                self._drag = near
                return
            lines.append(self._placed(pos))
        elif event.button == 3 and lines:
            lines.pop(int(np.argmin([abs(x - pos) for x in lines])))
        else:
            return
        self.set_lines(lines)
        self._draw()

    def _on_motion(self, event) -> None:
        """While dragging, only the two artists of the line move (no full redraw)."""
        if self._drag is None:
            return
        pos = self._position(event)
        if pos is None or self._drag >= len(self._line_artists):
            return
        image_line, profile_line = self._line_artists[self._drag]
        vertical = self.grids[self.set_list.currentRow()].alignment == 'Vertical'
        (image_line.set_xdata if vertical else image_line.set_ydata)([pos, pos])
        profile_line.set_xdata([pos, pos])
        self.canvas.draw_idle()

    def _on_release(self, event) -> None:
        if self._drag is None:
            return
        index, self._drag = self._drag, None
        pos = self._position(event)
        lines = list(self.current_lines())
        if pos is not None and index < len(lines):
            lines[index] = self._placed(pos)
            self.set_lines(lines)
        self._draw()                                    # also when released outside: the line goes back

    ## Drawing ##

    def _draw(self) -> None:
        i = self.set_list.currentRow()
        self.canvas.clear()
        if i < 0 or self._image is None:
            self.canvas.draw_idle()
            return
        g = self.grids[i]
        n = self._axis_len()
        lines = self.current_lines()
        electrodes = g.electrode_px(n)
        self.grid_label.setText(f'{g.source}, {len(lines)} lines' if lines else 'no lines yet: click on the edges')
        gs = self.canvas.figure.add_gridspec(2, 1, height_ratios=[3, 1])
        ax = self.canvas.figure.add_subplot(gs[0])
        prof_ax = self.canvas.figure.add_subplot(gs[1])
        self._image_ax, self._profile_ax = ax, prof_ax
        image = self._image[:, :, ::-1] if self._image.ndim == 3 else self._image
        ax.imshow(image, cmap='gray' if image.ndim == 2 else None)
        ax.set_xticks([])
        ax.set_yticks([])
        vertical = g.alignment == 'Vertical'
        profile = cg.frame_profile(self._image, g.alignment)
        prof_ax.plot(profile, color='#475569', linewidth=0.8)
        for a, b in zip(lines[:-1], lines[1:]):
            if any(a <= e <= b for e in electrodes):
                (ax.axvspan if vertical else ax.axhspan)(a, b, color='#2563EB', alpha=0.15)
                prof_ax.axvspan(a, b, color='#2563EB', alpha=0.15)
        self._line_artists = []
        for x in lines:
            self._line_artists.append(((ax.axvline if vertical else ax.axhline)(x, color='#DC2626', linewidth=0.9),
                                       prof_ax.axvline(x, color='#DC2626', linewidth=0.8)))
        prof_ax.set_xlim(0, n - 1)
        prof_ax.set_ylabel('Profile')
        style_axes(prof_ax)
        self.canvas.draw_idle()

    ## Conversion ##

    def jobs(self) -> list[tuple[ImageSet, GridSettings]]:
        """(set, grid) of every ticked set with at least two lines."""
        out = []
        for i, s in enumerate(self.sets):
            if self.set_list.item(i).checkState() == Qt.CheckState.Checked:
                g = self.grid(i)
                if len(g.grid_positions) >= 2:
                    out.append((s, g))
                else:
                    self.messages.append(f'{s.name}: no grid, left out')
        return out

    def run_conversion(self) -> None:
        jobs = self.jobs()
        if not jobs:
            QMessageBox.information(self, 'Convert images', 'Tick at least one set with a grid.')
            return
        self.convert_button.setEnabled(False)
        self.progress.show()
        self._thread = ConvertThread(jobs)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_set.connect(self._on_set_done)
        self._thread.failed.connect(lambda m: self.messages.append(m))
        self._thread.finished.connect(self._on_all_done)
        self._thread.start()

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.progress.setFormat(f'{name}: %v / %m images')

    def _on_set_done(self, image_set: ImageSet, result) -> None:
        sids, _ = self.ctx.project.add_import(result, image_set.folder.parent.name)
        self.converted += len(sids)
        self.messages += [f'{image_set.name}: {w}' for w in result.warnings]
        self.ctx.mark_dirty()
        self.ctx.spectra_changed.emit()

    def _on_all_done(self) -> None:
        self.convert_button.setEnabled(True)
        self.progress.hide()
        self.ctx.message.emit(f'🆕 {self.converted} spectra converted from images')
        text = f'{self.converted} spectra added to the project.'
        if self.messages:
            text += '\n\n' + '\n'.join(self.messages)
        QMessageBox.information(self, 'Convert images', text)
        self.messages = []
