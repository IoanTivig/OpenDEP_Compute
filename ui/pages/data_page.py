"""
Data page: import files, the project's spectra, the points of a spectrum (use / outlier); export or send the
selected spectra.
"""
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QMenu,
                             QMessageBox, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.data.outliers import suggest_outliers
from src.formats import OPEN_FILTER, read_file, write_view_scatter
from src.formats.opendep_json import SPECTRUM_SUFFIX, write_scatter
from src.project.sorting import SPECTRA_SORTS, spectra_order
from src.report.fit_export import write_spectrum_csv
from ui.context import AppContext
from ui.plots import dep_labels, draw_spectrum, frequency_axis, point_style_bar
from ui.view_link import send_to_view, view_folder
from ui.widgets import PlotCanvas, button, card, label, read_only, safe_name, set_combo_key, sort_combo

SPECTRUM_COLUMNS = ('Name', 'Sample', 'Quantity', 'Points used', 'Source')
POINT_COLUMNS = ('Frequency (Hz)', 'Value', 'Error', 'Use', 'Outlier')


def _check_item(checked: bool) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
    item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    return item


class DataPage(QWidget):
    """
    Spectra of the project.
    """

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName('Page')
        self.ctx = ctx
        self._filling = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_lists())
        splitter.addWidget(self._build_detail())
        splitter.setSizes([620, 800])
        lay.addWidget(splitter)
        ctx.project_changed.connect(self.refresh)
        ctx.spectra_changed.connect(self.refresh)
        ctx.point_style_changed.connect(self._on_selection)
        ctx.sort_changed.connect(self._on_sort_changed)

    ## Layout ##

    def _build_lists(self) -> QWidget:
        frame, lay = card(spacing=8)
        head = QHBoxLayout()
        head.addWidget(label('Spectra', 'section'))
        head.addStretch(1)
        self.import_button = button('Import…', 'primary', 'add_icon', 'Open spectra from OpenDEP Control, '
                                    'OpenDEP View, OpenDEP Compute 1.x or 3DEP files')
        self.convert_button = button('Convert images…', None, None, 'Compute grayness-factor spectra from image '
                                     'sets (OpenDEP Control, OpenDEP Compute 1.x)')
        self.convert_button.clicked.connect(self.convert_images)
        self.sample_button = button('Sample…', None, None, 'Set the sample (replicate group) of the selected spectra')
        self.rename_button = button('Rename…')
        self.remove_button = button('Remove', 'danger', None, 'Remove the selected spectra from the project '
                                    '(the original files are not touched)')
        self.send_button = button('Send to View', None, None, 'Open the selected spectra in OpenDEP View now, as '
                                  'measured (a fit sends them on the curve: Fit page); starts View when it is not '
                                  'running')
        self.export_button = button('Export', None, None, 'Write the selected spectra to a folder you choose: '
                                    f'OpenDEP Spectrum ({SPECTRUM_SUFFIX}, every point with its flags) or View '
                                    'Excel (the points in use)')
        menu = QMenu(self.export_button)
        menu.addAction(f'OpenDEP Spectrum ({SPECTRUM_SUFFIX})', lambda: self.export_spectra(SPECTRUM_SUFFIX))
        menu.addAction('View Excel (.xlsx)', lambda: self.export_spectra('.xlsx'))
        menu.addAction('CSV table (.csv): every point with its error and flags', lambda: self.export_spectra('.csv'))
        self.export_button.setMenu(menu)
        self.import_button.clicked.connect(self.import_files)
        self.sample_button.clicked.connect(self.set_sample)
        self.rename_button.clicked.connect(self.rename)
        self.remove_button.clicked.connect(self.remove_spectra)
        self.send_button.clicked.connect(self.send_to_view)
        for b in (self.import_button, self.convert_button, self.sample_button, self.rename_button, self.export_button,
                  self.send_button, self.remove_button):
            head.addWidget(b)
        lay.addLayout(head)
        self.banner = label('', 'banner', wrap=True)
        self.banner.hide()
        lay.addWidget(self.banner)
        sort_row = QHBoxLayout()
        sort_row.addStretch(1)
        sort_row.addWidget(label('Sort', 'muted'))
        self.sort_combo = sort_combo(SPECTRA_SORTS, self.ctx.spectra_sort, self.ctx.set_spectra_sort,
                                     'Order of the spectra, here and on the Fit page. Sample: the replicates of each '
                                     'sample together, names A–Z inside a sample')
        sort_row.addWidget(self.sort_combo)
        lay.addLayout(sort_row)
        self.table = QTableWidget(0, len(SPECTRUM_COLUMNS))
        self.table.setHorizontalHeaderLabels(SPECTRUM_COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._on_selection)
        lay.addWidget(self.table, 3)

        return frame

    def _build_detail(self) -> QWidget:
        frame, lay = card(spacing=8)
        head = QHBoxLayout()
        head.addWidget(label('Selected spectra', 'section'))
        head.addStretch(1)
        head.addWidget(point_style_bar(self.ctx))
        lay.addLayout(head)
        self.canvas = PlotCanvas(6, 3.6)
        lay.addWidget(self.canvas, 3)
        lay.addWidget(label('Points of the selected spectrum: untick "Use" to leave a point out of fits; '
                            'outliers are left out too and marked in red.', 'muted', wrap=True))
        self.points = QTableWidget(0, len(POINT_COLUMNS))
        self.points.setHorizontalHeaderLabels(POINT_COLUMNS)
        self.points.verticalHeader().hide()
        self.points.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.points.itemChanged.connect(self._on_point_changed)
        lay.addWidget(self.points, 2)
        row = QHBoxLayout()
        self.outlier_button = button('Suggest outliers', None, None, 'Find points that deviate strongly from their '
                                     'neighbours in the selected spectra (you confirm first)')
        self.outlier_button.clicked.connect(self.suggest_outliers)
        row.addWidget(self.outlier_button)
        row.addStretch(1)
        lay.addLayout(row)
        return frame

    ## Content ##

    def refresh(self) -> None:
        self._fill_spectra()
        self._on_selection()

    def _on_sort_changed(self) -> None:
        """The order changed here or on the Fit page: same list, same order (the selection is kept)."""
        set_combo_key(self.sort_combo, self.ctx.spectra_sort)
        self._fill_spectra()

    def _fill_spectra(self) -> None:
        project = self.ctx.project
        selected = set(self.selected_ids())
        self.table.setRowCount(0)
        if project is None:
            return
        for sid in spectra_order(project, self.ctx.spectra_sort):
            e = project.spectra[sid]
            s = e.spectrum
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = read_only(s.name)
            name.setData(Qt.ItemDataRole.UserRole, sid)
            source = s.source.get('software') or s.source.get('format', '')
            for col, item in enumerate((name, read_only(e.sample), read_only(s.label),
                                        read_only(f'{int(s.usable.sum())} / {len(s)}', True), read_only(source))):
                self.table.setItem(row, col, item)
            if sid in selected:
                self.table.selectRow(row)

    def selected_ids(self) -> list[str]:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in rows if self.table.item(r, 0)]

    def _on_selection(self) -> None:
        project = self.ctx.project
        ids = self.selected_ids() if project else []
        self.canvas.clear()
        ax = self.canvas.figure.add_subplot(111)
        frequency_axis(ax)
        for sid in ids:
            draw_spectrum(ax, project.spectra[sid].spectrum, connect=True, style=self.ctx.point_style)
        if ids:
            labels = {project.spectra[s].spectrum.label for s in ids}
            ax.set_ylabel(labels.pop() if len(labels) == 1 else 'Value')
            dep_labels(ax)
            ax.legend(fontsize=8, frameon=False)
        self.canvas.draw_idle()
        self._fill_points(ids[0] if len(ids) == 1 else None)

    def _fill_points(self, sid: str | None) -> None:
        self._filling = True
        self.points.setRowCount(0)
        self._points_id = sid
        if sid is not None:
            s = self.ctx.project.spectra[sid].spectrum
            for i in range(len(s)):
                row = self.points.rowCount()
                self.points.insertRow(row)
                self.points.setItem(row, 0, read_only(f'{s.frequencies[i]:.6g}', True))
                self.points.setItem(row, 1, read_only(f'{s.values[i]:.5g}', True))
                self.points.setItem(row, 2, read_only(f'{s.errors[i]:.3g}' if s.errors[i] > 0 else '', True))
                self.points.setItem(row, 3, _check_item(bool(s.enabled[i])))
                self.points.setItem(row, 4, _check_item(bool(s.outlier[i])))
        self._filling = False

    def _on_point_changed(self, item: QTableWidgetItem) -> None:
        if self._filling or self._points_id is None or item.column() not in (3, 4):
            return
        s = self.ctx.project.spectra[self._points_id].spectrum
        checked = item.checkState() == Qt.CheckState.Checked
        (s.enabled if item.column() == 3 else s.outlier)[item.row()] = checked
        self.ctx.mark_dirty()
        self.ctx.spectra_changed.emit()

    ## Actions ##

    def import_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, 'Import spectra', '', OPEN_FILTER)
        if paths:
            self.import_paths(paths)

    def import_paths(self, paths: list[str]) -> list[str]:
        """
        Import files into the project (also used by tests and drag and drop).

        Args:
            paths (list[str]): Files.

        Returns:
            list[str]: Messages shown in the banner (warnings and errors).
        """
        project = self.ctx.project
        messages, n_spectra, n_fits = [], 0, 0
        for path in paths:
            name = Path(path).name
            try:
                result = read_file(path)
            except (ValueError, OSError, KeyError) as e:
                messages.append(f'{name}: {e}')
                continue
            if not result.spectra:
                messages.append(f'{name}: a model curve file, without measured points (open it in OpenDEP View)')
                continue
            result.curves = []                       # curves stored in data files are not used here
            sids, _ = project.add_import(result)
            n_spectra += len(sids)
            n_fits += len(result.fits)
            messages += [f'{name}: {w}' for w in result.warnings if 'curve' not in w.lower()]
        self.banner.setText('\n'.join(messages))
        self.banner.setVisible(bool(messages))
        self.ctx.mark_dirty()
        self.ctx.spectra_changed.emit()
        if n_fits:
            self.ctx.fits_changed.emit()
        fits = f' and {n_fits} memorized fit(s)' if n_fits else ''
        self.ctx.message.emit(f'🆕 Imported {n_spectra} spectra{fits}')
        return messages

    def convert_images(self) -> None:
        from ui.convert_dialog import ConvertDialog
        ConvertDialog(self.ctx, self).exec()

    def outlier_suggestions(self) -> list[tuple[str, int]]:
        """(spectrum id, point index) of every suggested outlier in the selected spectra."""
        found = []
        for sid in self.selected_ids():
            mask = suggest_outliers(self.ctx.project.spectra[sid].spectrum)
            found += [(sid, int(j)) for j in np.nonzero(mask)[0]]
        return found

    def suggest_outliers(self) -> None:
        if not self.selected_ids():
            QMessageBox.information(self, 'Outliers', 'Select one or more spectra first.')
            return
        found = self.outlier_suggestions()
        if not found:
            QMessageBox.information(self, 'Outliers', 'No point deviates strongly from its neighbours.')
            return
        spectra = self.ctx.project.spectra
        listing = '\n'.join(f'{spectra[sid].spectrum.name}: {spectra[sid].spectrum.frequencies[j]:.4g} Hz'
                             for sid, j in found)
        if QMessageBox.question(self, 'Outliers', f'These points deviate strongly from their neighbours. '
                                f'Mark them as outliers?\n\n{listing}') == QMessageBox.StandardButton.Yes:
            for sid, j in found:
                spectra[sid].spectrum.outlier[j] = True
            self.ctx.mark_dirty()
            self.ctx.spectra_changed.emit()

    def set_sample(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        project = self.ctx.project
        current = project.spectra[ids[0]].sample
        name, ok = QInputDialog.getItem(self, 'Sample', 'Sample (replicates of one sample share it):',
                                        project.samples() or [current], editable=True)
        if ok:
            for sid in ids:
                project.spectra[sid].sample = name.strip()
            self.ctx.mark_dirty()
            self.ctx.spectra_changed.emit()

    def rename(self) -> None:
        ids = self.selected_ids()
        if len(ids) != 1:
            return
        s = self.ctx.project.spectra[ids[0]].spectrum
        name, ok = QInputDialog.getText(self, 'Rename', 'Name:', text=s.name)
        if ok and name.strip():
            s.name = name.strip()
            self.ctx.mark_dirty()
            self.ctx.spectra_changed.emit()

    def send_to_view(self) -> str:
        """
        Open the selected spectra in OpenDEP View: one .odspec each (exports/for View/), as measured.

        Returns:
            str: "sent", "started" or "" (see ui.view_link.send_to_view).
        """
        ids = self.selected_ids()
        if not ids:
            QMessageBox.information(self, 'Send to View', 'Select one or more spectra first.')
            return ''
        folder = view_folder(self.ctx)
        try:
            paths = [write_scatter(self.ctx.project.spectra[sid].spectrum,
                                   folder / f'{safe_name(self.ctx.project.spectra[sid].spectrum.name)}'
                                            f'{SPECTRUM_SUFFIX}') for sid in ids]
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, 'Send to View', str(e))
            return ''
        return send_to_view(self.ctx, paths, self)

    def export_spectra(self, suffix: str) -> list[Path]:
        """
        Write the selected spectra to a folder the user chooses.

        Args:
            suffix (str): '.odspec' (OpenDEP Spectrum), '.xlsx' (View Excel scatter) or '.csv' (plain table).

        Returns:
            list[Path]: Files written.
        """
        ids = self.selected_ids()
        if not ids:
            QMessageBox.information(self, 'Export', 'Select one or more spectra first.')
            return []
        folder = self.ctx.choose_export_folder(self, 'Folder for the spectra')
        if folder is None:
            return []
        written = []
        for sid in ids:
            s = self.ctx.project.spectra[sid].spectrum
            target = folder / f'{safe_name(s.name)}{suffix}'
            writer = {SPECTRUM_SUFFIX: write_scatter, '.xlsx': write_view_scatter, '.csv': write_spectrum_csv}[suffix]
            written.append(writer(s, target))
        self.ctx.message.emit(f'🆕 {len(written)} file(s) written to {folder}')
        return written

    def remove_spectra(self) -> None:
        ids = self.selected_ids()
        if not ids or QMessageBox.question(self, 'Remove', f'Remove {len(ids)} spectra from the project?') \
                != QMessageBox.StandardButton.Yes:
            return
        for sid in ids:
            self.ctx.project.spectra.pop(sid, None)
        self.ctx.mark_dirty()
        self.ctx.spectra_changed.emit()
