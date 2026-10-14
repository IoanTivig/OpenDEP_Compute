"""
Fit page: choose spectra (replicates) and a model, set the parameters (grouped: Buffer, Cell, Membrane, ...),
fit, and read the crossovers, R² and the fitted values. The fit on screen is saved as a file (.odfit), drawn as a
figure, reported (PDF) or sent to OpenDEP View; "Memorize fit" keeps it in the project's list of memorized fits, which exports
many fits at once (reports, .odfit files, one table) and opens a listed fit again.
"""
from dataclasses import asdict
import math
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QSizePolicy, QSplitter,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.data.spectrum import ModelCurve
from src.fitting.engine import (SCALE_AUTO, SCALE_FIXED, SCALE_FREE, WEIGHT_ERRORS, WEIGHT_NONE, FitResult,
                                FitSettings, ParameterResult, fit_spectra, fit_summary, result_from_summary)
from src.models.catalog import MODELS, full_label, grouped_parameters
from src.report.plotting import CROSSOVER_RANGE, fit_crossovers, frequency_text
from src.formats.opendep_fit import FIT_SUFFIX, fit_document, write_fit
from src.report.fit_export import (curve_spectrum, saved_fit_document, scaled_spectrum, write_fit_table,
                                   write_fit_tables)
from src.report.report import FitReport, report_for_fit, value_text, write_fit_report
from ui.context import AppContext
from ui.figure_dialog import FigureDialog
from ui.plots import draw_fit, point_style_bar
from ui.view_export_dialog import ViewExportDialog
from ui.view_link import send_to_view, view_folder
from src.project.sorting import FIT_SORTS, SPECTRA_SORTS, fit_order, spectra_order
from ui.widgets import (PlotCanvas, StatTile, button, card, label, read_only, safe_name, set_combo_key,
                        sort_combo)

# Fitted by default: what a DEP spectrum usually determines (docs/concepts/fitting.md)
DEFAULT_FREE = {'homogeneous': ['eps_p', 'sigma_p'], 'single_shell': ['eps_mem', 'sigma_cyto'],
                'two_shell': ['eps_mem', 'sigma_cyto', 'sigma_wall'],
                'three_shell': ['eps_mem', 'sigma_cyto', 'sigma_np'],
                'four_shell': ['eps_mem', 'sigma_cyto', 'sigma_wall']}
PARAM_COLUMNS = ('Fit', 'Parameter', 'Value', 'Min', 'Max', 'Unit')
COL_FIT, COL_NAME, COL_VALUE, COL_MIN, COL_MAX, COL_UNIT = range(len(PARAM_COLUMNS))
NUMBER_COLUMNS = (COL_VALUE, COL_MIN, COL_MAX)
SCALES = (('Automatic', SCALE_AUTO), ('Free', SCALE_FREE), ('Fixed at 1', SCALE_FIXED))
WEIGHTS = (('Error bars', WEIGHT_ERRORS), ('None', WEIGHT_NONE))


def fmt(value: float | None) -> str:
    """Compact number for tables."""
    if value is None or not math.isfinite(value):
        return ''
    return f'{value:.4g}'


def _group_row(table: QTableWidget, title: str) -> None:
    """A bold header row spanning the table."""
    row = table.rowCount()
    table.insertRow(row)
    item = QTableWidgetItem(title)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    font = QFont()
    font.setBold(True)
    item.setFont(font)
    item.setBackground(Qt.GlobalColor.transparent)
    table.setItem(row, 0, item)
    table.setSpan(row, 0, 1, table.columnCount())


def short_label(text: str, group: str) -> str:
    """'Buffer permittivity' under the Buffer group is just 'Permittivity' (the group says the rest)."""
    if text.lower().startswith(group.lower() + ' '):
        rest = text[len(group) + 1:]
        return rest[:1].upper() + rest[1:]
    return text


def status_of(p: ParameterResult) -> str:
    """'fitted', 'fixed', 'not determined' or 'at bound' (what to trust, fix or widen)."""
    if not p.free:
        return 'fixed'
    return 'not determined' if not p.determined else ('at bound' if p.at_bound else 'fitted')


class ResultGroups(QWidget):
    """
    The fitted values in the groups of OpenDEP View's curve panel (Buffer, Cytoplasm, Other, Shell dimensions,
    Membrane, ...), one card per group, on a grid: all columns equally wide, the cards of a row equally tall. As
    many columns as fit the width (at most MAX_COLUMNS); resizing re-places the cards. Each row of a card: the
    quantity, its value ± standard error, the unit and the status; fixed values grey, problems ("not determined",
    "at bound") orange. The widget is as tall as its rows, so the plot above gets the free height.
    """
    MAX_COLUMNS = 4
    SPACING = 8

    def __init__(self) -> None:
        super().__init__()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(self.SPACING)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.empty = label('Fit, or open a memorized fit, to see the values here.', 'muted')
        self.cards: list[QFrame] = []
        self.columns = 0
        self._card_width = 0                            # every card's width (measured once per result)
        self.titles: list[str] = []                     # group titles on screen (tests, help)
        self.texts: dict[str, str] = {}                 # parameter key -> value text on screen
        self._place(force=True)

    def show_result(self, result: FitResult | None) -> None:
        for frame in self.cards:
            frame.hide()                                # at once; deleteLater waits for the event loop
            frame.deleteLater()
        self.cards, self.titles, self.texts = [], [], {}
        if result is not None:
            for group, params in grouped_parameters(result.model):
                self.cards.append(self._group_card(group, params, result))
                self.titles.append(group)
            self._align_columns()
        # Measured once here, not at every resize; and the widget's minimum width is ONE card, set explicitly so
        # the grid of the current columns does not become the minimum (that held the panel wide: the columns
        # could not drop again when the panel was narrowed)
        self._card_width = max((c.sizeHint().width() for c in self.cards), default=0)
        self.setMinimumWidth(self._card_width)
        self._place(force=True)

    def _align_columns(self) -> None:
        """Same inner column widths in every card (name, value, unit, status), so the cards read like one table."""
        widths = [0, 0, 0, 0]
        for frame in self.cards:
            grid = frame.layout()
            for row in range(1, grid.rowCount()):
                for col in range(4):
                    item = grid.itemAtPosition(row, col)
                    if item is not None and item.widget() is not None:
                        widths[col] = max(widths[col], item.widget().sizeHint().width())
        for frame in self.cards:
            for col, w in enumerate(widths):
                frame.layout().setColumnMinimumWidth(col, w)

    def columns_for(self, width: int) -> int:
        """Columns that fit the width: each as wide as the widest card."""
        if not self.cards:
            return 1
        fit = (width + self.SPACING) // (self._card_width + self.SPACING)
        return max(1, min(fit, self.MAX_COLUMNS, len(self.cards)))

    def _place(self, force: bool = False) -> None:
        n = self.columns_for(self.width())
        if n == self.columns and not force:
            return
        while self._grid.count():
            self._grid.takeAt(0)                        # the widgets stay; only their cells change
        for col in range(self.MAX_COLUMNS):
            self._grid.setColumnStretch(col, 1 if col < n else 0)   # equal widths
        self.empty.setVisible(not self.cards)
        if not self.cards:
            self._grid.addWidget(self.empty, 0, 0)
        for i, frame in enumerate(self.cards):
            self._grid.addWidget(frame, i // n, i % n)
        self.columns = n
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place()

    def _group_card(self, group: str, params: list, result: FitResult) -> QFrame:
        frame = QFrame(self)
        frame.setProperty('group', True)
        grid = QGridLayout(frame)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        grid.addWidget(label(group, 'group-title'), 0, 0, 1, 4)
        for row, d in enumerate(params, 1):
            p = result.parameters[d.key]
            status = status_of(p)
            name = label(f'{short_label(d.label, group)} ({d.symbol})')
            name.setToolTip(d.description or full_label(d))
            text = value_text(p.value, p.stderr if p.free else None)
            value = label(text, 'value-fixed' if status == 'fixed' else 'value-fitted')
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)   # copy a value
            role = {'fitted': 'status-fitted', 'fixed': 'status-fixed'}.get(status, 'status-warning')
            for col, widget in enumerate((name, value, label(d.unit, 'muted'), label(status, role))):
                grid.addWidget(widget, row, col)
            self.texts[d.key] = text
        grid.setColumnStretch(4, 1)                     # spare width after the status: values stay by their names
        grid.setRowStretch(len(params) + 1, 1)          # a taller card (same row) keeps its rows at the top
        return frame


class FitThread(QThread):
    """
    Runs one fit off the GUI thread.
    """
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, spectra: list, settings: FitSettings) -> None:
        super().__init__()
        self.spectra, self.settings = spectra, settings

    def run(self) -> None:
        try:
            self.done.emit(fit_spectra(self.spectra, self.settings))
        except Exception as e:                       # shown to the user, never swallowed
            self.failed.emit(str(e))


class FitPage(QWidget):
    """
    Model fitting.
    """

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName('Page')
        self.ctx = ctx
        self.result: FitResult | None = None
        self.settings_used: FitSettings | None = None
        self.spectra_used: list[str] = []
        self.saved_name: str | None = None              # name of the saved fit on screen (None: a new fit)
        self._thread: FitThread | None = None
        self._filling = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_setup())
        splitter.addWidget(self._build_results())
        splitter.setSizes([600, 820])
        lay.addWidget(splitter)
        ctx.project_changed.connect(self.refresh)
        ctx.spectra_changed.connect(self._fill_spectra)
        ctx.fits_changed.connect(self._fill_saved)
        ctx.point_style_changed.connect(self._show_result)
        ctx.sort_changed.connect(self._on_sort_changed)
        self._set_model(self.model_combo.currentData())

    ## Layout ##

    def _build_setup(self) -> QWidget:
        """Spectra on top (the list takes the free height), the model settings below; the border can be dragged."""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # 1. Spectra
        frame, lay = card(spacing=8)
        head = QHBoxLayout()
        head.addWidget(label('Spectra', 'section'))
        head.addStretch(1)
        head.addWidget(label('Sort', 'muted'))
        self.spectra_sort_combo = sort_combo(SPECTRA_SORTS, self.ctx.spectra_sort, self.ctx.set_spectra_sort,
                                             'Order of the spectra, here and on the Data page. Sample: the replicates '
                                             'of each sample together, names A–Z inside a sample')
        head.addWidget(self.spectra_sort_combo)
        lay.addLayout(head)
        lay.addWidget(label('Tick one spectrum, or several replicates of one sample: they share the model '
                            'parameters and each gets its own scale factor.', 'muted', wrap=True))
        self.spectra_list = QListWidget()
        self.spectra_list.setMinimumHeight(80)
        self.spectra_list.itemChanged.connect(self._on_spectra_ticked)
        lay.addWidget(self.spectra_list, 1)
        splitter.addWidget(frame)

        # 2. Model settings: model, scale factor, weighting, parameters, Fit
        frame, lay = card(spacing=8)
        lay.addWidget(label('Model settings', 'section'))
        grid = QGridLayout()
        grid.addWidget(label('Model'), 0, 0)
        self.model_combo = QComboBox()
        for key, m in MODELS.items():
            self.model_combo.addItem(m.name, key)
        self.model_combo.setCurrentIndex(list(MODELS).index('single_shell'))
        self.model_combo.currentIndexChanged.connect(lambda: self._set_model(self.model_combo.currentData()))
        grid.addWidget(self.model_combo, 0, 1)
        grid.addWidget(label('Scale factor'), 1, 0)
        self.scale_combo = QComboBox()
        self.scale_combo.setToolTip('Automatic: free for spectra proportional to Re[K] (grayness factor, DEP rate, '
                                    '3DEP intensity), 1 for spectra that are Re[K] itself')
        for text, key in SCALES:
            self.scale_combo.addItem(text, key)
        grid.addWidget(self.scale_combo, 1, 1)
        grid.addWidget(label('Weighting'), 2, 0)
        self.weight_combo = QComboBox()
        self.weight_combo.setToolTip('Error bars: points weighted by 1 / error when every point has one')
        for text, key in WEIGHTS:
            self.weight_combo.addItem(text, key)
        grid.addWidget(self.weight_combo, 2, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        self.model_info = label('', 'muted', wrap=True)
        lay.addWidget(self.model_info)
        lay.addWidget(label('Tick "Fit" for the parameters to fit; unticked ones stay fixed at their value. Enter '
                            'what you have measured (buffer conductivity, cell radius).', 'muted', wrap=True))
        self.params = QTableWidget(0, len(PARAM_COLUMNS))
        self.params.setHorizontalHeaderLabels(PARAM_COLUMNS)
        self.params.verticalHeader().hide()
        header = self.params.horizontalHeader()
        for col in range(len(PARAM_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch if col == COL_NAME
                                        else QHeaderView.ResizeMode.ResizeToContents)
        self.params.horizontalHeaderItem(COL_FIT).setToolTip('Ticked: fitted. Unticked: fixed at its value')
        self.params.setMinimumHeight(160)
        self.params.itemChanged.connect(self._on_param_changed)
        lay.addWidget(self.params, 1)
        self.fit_button = button('Fit', 'primary', None, 'Fit the ticked spectra')
        self.fit_button.clicked.connect(self.run_fit)
        lay.addWidget(self.fit_button)
        splitter.addWidget(frame)

        # 3. Memorized fits (kept in the project; "saved fits" in the code): open one again, export many at once
        frame, lay = card(spacing=8)
        head = QHBoxLayout()
        head.addWidget(label('Memorized fits', 'section'))
        head.addStretch(1)
        head.addWidget(label('Sort', 'muted'))
        self.saved_sort_combo = sort_combo(FIT_SORTS, self.ctx.fit_sort, self.ctx.set_fit_sort,
                                           'Order of the memorized fits: by when they were memorized, or by name')
        head.addWidget(self.saved_sort_combo)
        lay.addLayout(head)
        lay.addWidget(label('Export and Send to View use the selected fits, or all of them when none is '
                            'selected.', 'muted', wrap=True))
        self.saved_list = QListWidget()
        self.saved_list.setMinimumHeight(60)
        self.saved_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.saved_list.setToolTip('Double-click to open a fit again. Exports act on the selected fits, or on all '
                                   'of them when none is selected')
        self.saved_list.itemDoubleClicked.connect(lambda item: self.open_saved(item.data(Qt.ItemDataRole.UserRole)))
        lay.addWidget(self.saved_list, 1)
        row = QHBoxLayout()
        self.open_saved_button = button('Open', None, None, 'Show the selected fit again: spectra, model, settings '
                                        'and results (no refit)')
        self.open_saved_button.clicked.connect(lambda: self.open_saved())
        self.select_all_button = button('Select all', None, None, 'Select every memorized fit')
        self.select_all_button.clicked.connect(self.saved_list.selectAll)
        self.saved_export_button = button('Export', None, None, 'The selected fits (all when none is selected), to '
                                          'a folder you choose')
        menu = QMenu(self.saved_export_button)
        menu.addAction(f'Fit files ({FIT_SUFFIX}, one per fit)', self.export_saved_fit_files)
        menu.addAction('Data tables (CSV, data + curve per fit)', self.export_saved_tables)
        menu.addAction('PDF reports (one per fit)', self.export_saved_reports)
        menu.addAction('Figure… (one fit)', self.export_saved_figure)
        menu.addSeparator()
        menu.addAction('Table of all fits (CSV)', self.export_fit_table)
        self.saved_export_button.setMenu(menu)
        self.saved_send_button = button('Send to View', None, None, 'Open the selected fits (all when none is '
                                        'selected) in OpenDEP View now, each with its spectra linked to the curve')
        self.saved_send_button.clicked.connect(self.send_saved_to_view)
        self.remove_saved_button = button('Remove', 'danger', None, 'Remove the selected fits from the project (the '
                                          'the project; exported files stay)')
        self.remove_saved_button.clicked.connect(self.remove_saved)
        for b in (self.open_saved_button, self.select_all_button, self.saved_export_button, self.saved_send_button):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.remove_saved_button)
        lay.addLayout(row)
        splitter.addWidget(frame)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)                 # the parameter table gets most of the height
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([170, 600, 150])
        return splitter

    def _build_results(self) -> QWidget:
        """The fit on screen: tiles and plot (all free height), then the Results card (as tall as its content)."""
        column = QWidget()
        outer = QVBoxLayout(column)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        # 1. Crossovers, R², plot, warnings
        frame, lay = card(spacing=8)
        tiles = QHBoxLayout()
        self.tile_first = StatTile('First crossover (nDEP → pDEP)')
        self.tile_second = StatTile('Second crossover (pDEP → nDEP)')
        self.tile_r2 = StatTile('R² (fit quality)')
        for t in (self.tile_first, self.tile_second, self.tile_r2):
            tiles.addWidget(t)
        lay.addLayout(tiles)
        style_row = QHBoxLayout()
        style_row.addStretch(1)
        style_row.addWidget(point_style_bar(self.ctx))
        lay.addLayout(style_row)
        self.canvas = PlotCanvas(6, 4.2)
        self.canvas.setMinimumHeight(220)
        lay.addWidget(self.canvas, 1)
        self.warning_label = label('', 'banner', wrap=True)
        self.warning_label.hide()
        lay.addWidget(self.warning_label)
        outer.addWidget(frame, 1)

        # 2. Results: the values in group cards, and what to do with the fit
        frame, lay = card(spacing=8)
        lay.addWidget(label('Results', 'section'))
        self.result_groups = ResultGroups()
        lay.addWidget(self.result_groups)
        actions = QHBoxLayout()
        self.save_button = button('Memorize fit', None, 'add_icon', 'Add this fit to the Memorized fits list '
                                  '(kept in the project: it can be opened again and exported with the others)')
        self.odc_button = button('Export fit…', None, None, 'Export this fit as a file (.odfit: the spectra, the '
                                 'fitted curve, the scale factors and the results; OpenDEP View and Compute open '
                                 'it); separate curve / spectrum files optional')
        self.send_button = button('Send to View', None, None, 'Open this fit in OpenDEP View now (the spectra linked '
                                  'to the fitted curve); starts View when it is not running')
        self.send_button.clicked.connect(self.send_to_view)
        self.figure_button = button('Figure…', None, None, 'Publication figure of this fit (PNG, TIFF, SVG, PDF)')
        self.report_button = button('Report…', None, None, 'PDF report: figure, parameters with errors, settings, '
                                    'data and references')
        self.save_button.clicked.connect(self.save_fit)
        self.odc_button.clicked.connect(self.export_for_view)
        self.figure_button.clicked.connect(self.export_figure)
        self.report_button.clicked.connect(self.export_report)
        for b in self.result_buttons():
            actions.addWidget(b)
            b.setEnabled(False)
        actions.addStretch(1)
        lay.addLayout(actions)
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        outer.addWidget(frame, 0)
        return column

    ## Spectra ##

    def refresh(self) -> None:
        self.result = None
        self.saved_name = None
        self._fill_spectra()
        self._fill_saved()
        self._show_result()

    def _fill_spectra(self) -> None:
        project = self.ctx.project
        ticked = set(self.ticked_ids())
        self._filling = True
        self.spectra_list.clear()
        if project is not None:
            for sid in spectra_order(project, self.ctx.spectra_sort):
                e = project.spectra[sid]
                text = e.spectrum.name + (f'   [{e.sample}]' if e.sample else '')
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, sid)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if sid in ticked else Qt.CheckState.Unchecked)
                self.spectra_list.addItem(item)
        self._filling = False

    def ticked_ids(self) -> list[str]:
        """The ticked spectra in the project's (import) order, whatever the list's sort: a fit does not depend on it."""
        ticked = {self.spectra_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.spectra_list.count())
                  if self.spectra_list.item(i).checkState() == Qt.CheckState.Checked}
        order = list(self.ctx.project.spectra) if self.ctx.project is not None else []
        return [sid for sid in order if sid in ticked]

    def _on_spectra_ticked(self, *_) -> None:
        """Known parameters of the ticked spectra (e.g. a measured radius) are entered as values."""
        if self._filling or self.ctx.project is None:
            return
        for sid in self.ticked_ids():
            for key, value in self.ctx.project.spectra[sid].spectrum.known_parameters.items():
                self.set_value(key, value)

    ## Parameters ##

    def _param_rows(self) -> list[int]:
        """Rows holding a parameter (not group headers)."""
        return [r for r in range(self.params.rowCount())
                if self.params.item(r, COL_NAME) is not None
                and self.params.item(r, COL_NAME).data(Qt.ItemDataRole.UserRole)]

    def _set_model(self, key: str) -> None:
        model = MODELS[key]
        self.model_info.setText(model.description)
        keep = {}
        for row in self._param_rows():
            try:
                v = self._row_values(row)
            except ValueError:
                continue
            if v['key'].startswith('medium') or v['key'] == 'radius':
                keep[v['key']] = v['value']             # buffer and radius carry over between models
        self._filling = True
        self.params.clearSpans()
        self.params.setRowCount(0)
        for group, params in grouped_parameters(key):
            _group_row(self.params, group)
            for p in params:
                row = self.params.rowCount()
                self.params.insertRow(row)
                name = read_only(f'{short_label(p.label, group)} ({p.symbol})')
                name.setData(Qt.ItemDataRole.UserRole, p.key)
                name.setToolTip(p.description or p.label)
                check = QTableWidgetItem()
                check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                check.setCheckState(Qt.CheckState.Checked if p.key in DEFAULT_FREE.get(key, [])
                                    else Qt.CheckState.Unchecked)
                cells = {COL_FIT: check, COL_NAME: name, COL_VALUE: QTableWidgetItem(fmt(keep.get(p.key, p.default))),
                         COL_MIN: QTableWidgetItem(fmt(p.minimum)), COL_MAX: QTableWidgetItem(fmt(p.maximum)),
                         COL_UNIT: read_only(p.unit)}
                for col, item in cells.items():
                    self.params.setItem(row, col, item)
        self._filling = False

    def _row_values(self, row: int) -> dict:
        def num(col: int) -> float:
            return float(self.params.item(row, col).text().replace(',', '.'))
        return {'key': self.params.item(row, COL_NAME).data(Qt.ItemDataRole.UserRole), 'value': num(COL_VALUE),
                'free': self.params.item(row, COL_FIT).checkState() == Qt.CheckState.Checked,
                'min': num(COL_MIN), 'max': num(COL_MAX)}

    def _on_param_changed(self, item: QTableWidgetItem) -> None:
        if self._filling or item.column() not in NUMBER_COLUMNS:
            return
        try:
            float(item.text().replace(',', '.'))
            item.setForeground(Qt.GlobalColor.black)
        except ValueError:
            item.setForeground(Qt.GlobalColor.red)
            self.ctx.message.emit(f'⚠️ "{item.text()}" is not a number')

    def set_value(self, key: str, value: float) -> None:
        """Set a parameter's value (no effect when the model has no such parameter)."""
        for row in self._param_rows():
            if self.params.item(row, COL_NAME).data(Qt.ItemDataRole.UserRole) == key:
                self.params.item(row, COL_VALUE).setText(fmt(value))

    def set_free(self, keys: list[str]) -> None:
        """Fit exactly these parameters."""
        for row in self._param_rows():
            key = self.params.item(row, COL_NAME).data(Qt.ItemDataRole.UserRole)
            self.params.item(row, COL_FIT).setCheckState(Qt.CheckState.Checked if key in keys
                                                         else Qt.CheckState.Unchecked)

    def current_settings(self) -> FitSettings:
        """
        Settings from the page.

        Raises:
            ValueError: A cell is not a number, or a fitted value lies outside its range.
        """
        values, free, bounds = {}, [], {}
        for row in self._param_rows():
            try:
                v = self._row_values(row)
            except ValueError:
                raise ValueError(f'⚠️ "{self.params.item(row, COL_NAME).text().strip()}" has a value that is not a '
                                 f'number') from None
            values[v['key']] = v['value']
            bounds[v['key']] = (v['min'], v['max'])
            if v['free']:
                if not v['min'] <= v['value'] <= v['max']:
                    raise ValueError(f'⚠️ {self.params.item(row, COL_NAME).text().strip()}: the value lies outside its '
                                     f'range')
                free.append(v['key'])
        return FitSettings(self.model_combo.currentData(), values, free, bounds, self.scale_combo.currentData(),
                           self.weight_combo.currentData())

    ## Fit ##

    def run_fit(self) -> None:
        ids = self.ticked_ids()
        if not ids:
            QMessageBox.information(self, 'Fit', 'Tick at least one spectrum.')
            return
        try:
            settings = self.current_settings()
        except ValueError as e:
            QMessageBox.warning(self, 'Fit', str(e))
            return
        self.fit_button.setEnabled(False)
        self.fit_button.setText('Fitting…')
        self.saved_name = None                          # a new fit, even when a saved one was opened before
        self.spectra_used = ids
        self.settings_used = settings
        self._thread = FitThread([self.ctx.project.spectra[i].spectrum for i in ids], settings)
        self._thread.done.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _finish(self) -> None:
        self.fit_button.setEnabled(True)
        self.fit_button.setText('Fit')

    def _on_failed(self, message: str) -> None:
        self._finish()
        QMessageBox.warning(self, 'Fit', message)

    def _on_done(self, result: FitResult) -> None:
        self._finish()
        self.result = result
        self._show_result()
        self.ctx.message.emit(f'ℹ️ Fit finished: R² {result.r_squared:.4f}')

    def crossovers(self) -> tuple[float | None, float | None]:
        """First and second crossover of the fitted curve (Hz), or None."""
        if self.result is None:
            return None, None
        return fit_crossovers(self.result.model, self.result.values)

    def _show_result(self) -> None:
        r = self.result
        for b in self.result_buttons():
            b.setEnabled(r is not None)
        self.canvas.clear()
        if r is None:
            for t in (self.tile_first, self.tile_second, self.tile_r2):
                t.set_value('-')
            self.result_groups.show_result(None)
            self.warning_label.hide()
            self.canvas.draw_idle()
            return
        first, second = self.crossovers()
        self.tile_first.set_value(frequency_text(first))
        self.tile_second.set_value(frequency_text(second))
        self.tile_r2.set_value(f'{r.r_squared:.4f}')

        # 1. Plot: data divided by their scale (Re[K] axis), fitted curve, residuals
        project = self.ctx.project
        spectra = [project.spectra[i].spectrum for i in self.spectra_used if i in project.spectra]
        draw_fit(self.canvas.figure, spectra, r.model, r.values, r.scales, self.ctx.point_style)
        self.canvas.draw_idle()

        # 2. Values in group cards (Buffer, Cell, Membrane, ...), as in OpenDEP View
        self.result_groups.show_result(r)

        # 3. Warnings (undetermined parameters, bounds, scatter)
        self.warning_label.setText('\n'.join(r.warnings))
        self.warning_label.setVisible(bool(r.warnings))

    ## Actions ##

    def result_buttons(self) -> tuple:
        return self.odc_button, self.figure_button, self.report_button, self.send_button, self.save_button

    def _fit_name(self) -> str:
        if self.saved_name:
            return self.saved_name
        return f'{MODELS[self.result.model].name} - ' + ', '.join(
            self.ctx.project.spectra[i].spectrum.name for i in self.spectra_used[:2])

    def _spectra_used(self) -> list:
        return [self.ctx.project.spectra[i].spectrum for i in self.spectra_used]

    def figure_dialog(self) -> FigureDialog:
        r = self.result
        return FigureDialog(self._spectra_used(), r.model, r.values, r.scales, self.ctx.point_style,
                            self.ctx.export_folder() / f'{safe_name(self._fit_name())}.png', self,
                            remember=self.ctx.remember_export_folder)

    def export_figure(self) -> None:
        if self.result is not None:
            self.figure_dialog().exec()

    def report(self) -> FitReport:
        return FitReport(self._fit_name(), self._spectra_used(), asdict(self.settings_used),
                         fit_summary(self.result, *CROSSOVER_RANGE), self.ctx.project.name)

    def export_report(self) -> None:
        if self.result is None:
            return
        path = self.ctx.choose_export_file(self, 'Fit report', f'{safe_name(self._fit_name())}.pdf', 'PDF (*.pdf)')
        if path:
            write_fit_report(self.report(), path, self.ctx.point_style)
            self.ctx.message.emit(f'🆕 Report written: {path}')

    def save_fit(self) -> None:
        if self.result is None:
            return
        default = self._fit_name()
        name, ok = QInputDialog.getText(self, 'Memorize fit', 'Name of the fit:', text=default)
        if ok and name.strip():
            fid = self.ctx.project.add_fit(name.strip(), self.spectra_used, asdict(self.settings_used),
                                           fit_summary(self.result, *CROSSOVER_RANGE))
            self.saved_name = name.strip()
            self.ctx.mark_dirty()
            self.ctx.fits_changed.emit()
            self._select_saved([fid])
            self.ctx.message.emit(f'🆕 Fit "{name.strip()}" added to the Memorized fits')

    def fitted_curve(self) -> ModelCurve:
        names = ', '.join(self.ctx.project.spectra[i].spectrum.name for i in self.spectra_used[:2])
        return ModelCurve(f'Fit: {names}', self.result.model, dict(self.result.values),
                          {'software': 'OpenDEP Compute', 'fit_r_squared': self.result.r_squared})

    def fit_file_document(self) -> dict:
        """OpenDEP Fit document of the current fit: original spectra, fitted curve, scale factors, results."""
        r = self.result
        spectra = self._spectra_used()
        curve = self.fitted_curve()
        if len(spectra) == 1:                        # one spectrum: the curve in its colour, as on the Fit page
            curve.color = spectra[0].color
        samples = [self.ctx.project.spectra[i].sample for i in self.spectra_used]
        return fit_document(self._fit_name(), spectra, curve, r.scales, r.scale_errors, samples,
                            asdict(self.settings_used), fit_summary(r, *CROSSOVER_RANGE))

    def view_files(self) -> tuple:
        """(fit document, fitted curve, fitted spectra on the Re[K] scale, fitted curve as points) for View."""
        r = self.result
        spectra = self._spectra_used()
        scaled = [scaled_spectrum(sp, scale, r.model, r.r_squared) for sp, scale in zip(spectra, r.scales)]
        f = np.concatenate([sp.frequencies[sp.frequencies > 0] for sp in spectra])
        points = curve_spectrum(f'{self._fit_name()} - curve', r.model, r.values, f.min() / 3, f.max() * 3)
        return self.fit_file_document(), self.fitted_curve(), scaled, points

    def export_for_view(self) -> list:
        if self.result is None:
            return []
        dialog = ViewExportDialog(self.ctx.export_folder(), self)
        if dialog.exec() != ViewExportDialog.DialogCode.Accepted:
            return []
        try:
            written = dialog.write(self._fit_name(), *self.view_files(), tables=self.write_tables)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, 'Export', str(e))
            return []
        self.ctx.remember_export_folder(dialog.folder_edit.text())
        self.ctx.message.emit(f'🆕 {len(written)} file(s) for OpenDEP View written to {dialog.folder_edit.text()}')
        return written

    def write_tables(self, folder: Path) -> list[Path]:
        """The fit on screen as CSV tables (data and curve) in a folder."""
        r = self.result
        samples = [self.ctx.project.spectra[i].sample for i in self.spectra_used]
        return write_fit_tables(folder, safe_name(self._fit_name()), self._spectra_used(), samples, r.model, r.values,
                                r.scales)

    def send_to_view(self) -> str:
        """
        Open the current fit in OpenDEP View: its .odfit (exports/for View/), sent to the running View or opened by a
        View started for it.

        Returns:
            str: "sent", "started" or "" (see ui.view_link.send_to_view).
        """
        if self.result is None:
            return ''
        try:
            path = write_fit(self.fit_file_document(), view_folder(self.ctx) / f'{safe_name(self._fit_name())}'
                                                                             f'{FIT_SUFFIX}')
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, 'Send to View', str(e))
            return ''
        return send_to_view(self.ctx, [path], self)

    ## Memorized fits ("saved fits" in the code) ##

    def _on_sort_changed(self) -> None:
        """An order changed (spectra here or on the Data page, or the memorized fits): ticks and selection kept."""
        set_combo_key(self.spectra_sort_combo, self.ctx.spectra_sort)
        set_combo_key(self.saved_sort_combo, self.ctx.fit_sort)
        self._fill_spectra()
        self._fill_saved()

    def _fill_saved(self) -> None:
        selected = set(self.selected_saved_ids())
        self.saved_list.clear()
        project = self.ctx.project
        if project is None:
            return
        for fid in fit_order(project, self.ctx.fit_sort):
            f = project.fits[fid]
            item = QListWidgetItem(f'{f.name}   (R² {f.result["statistics"]["r_squared"]:.3f})')
            item.setData(Qt.ItemDataRole.UserRole, fid)
            self.saved_list.addItem(item)
            item.setSelected(fid in selected)

    def selected_saved_ids(self) -> list[str]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self.saved_list.selectedItems()]

    def _select_saved(self, ids: list[str]) -> None:
        for i in range(self.saved_list.count()):
            item = self.saved_list.item(i)
            item.setSelected(item.data(Qt.ItemDataRole.UserRole) in ids)

    def _selected_fits(self, title: str, one: bool = False) -> list:
        """
        The saved fits to act on: the selected ones, or all when none is selected (the whole list by default). With one=True exactly one must be selected. A message (and []) otherwise.
        """
        project = self.ctx.project
        fits = [project.fits[fid] for fid in self.selected_saved_ids()]
        if not fits and not one:
            fits = list(project.fits.values())
        if not fits or (one and len(fits) != 1):
            QMessageBox.information(self, title, 'Select one memorized fit.' if one else
                                    'No memorized fits yet: "Memorize fit" below the results adds the fit on screen.')
            return []
        return fits

    def open_saved(self, fid: str | None = None) -> bool:
        """
        Show a saved fit again (no refit): its spectra ticked, its model and settings in the table, its results.

        Args:
            fid (str | None): Saved fit id; None = the one selected in the list.

        Returns:
            bool: True when the fit is shown.
        """
        if fid is None:
            fits = self._selected_fits('Open fit', one=True)
            if not fits:
                return False
            fid = fits[0].id
        project = self.ctx.project
        record = project.fits[fid]
        if any(s not in project.spectra for s in record.spectra):
            QMessageBox.warning(self, 'Open fit', f'⚠️ Fit "{record.name}": some of its spectra were removed from '
                                                  f'the project')
            return False
        s = dict(record.settings)
        s['bounds'] = {k: tuple(v) for k, v in s.get('bounds', {}).items()}   # JSON lists back to (min, max)
        settings = FitSettings(**s)
        # 1. Model and parameters as they were set for this fit
        self.model_combo.setCurrentIndex(list(MODELS).index(settings.model))
        self._set_model(settings.model)
        for key, value in settings.values.items():
            self.set_value(key, value)
        self.set_free(settings.free)
        for row in self._param_rows():
            key = self.params.item(row, COL_NAME).data(Qt.ItemDataRole.UserRole)
            if key in settings.bounds:
                self.params.item(row, COL_MIN).setText(fmt(settings.bounds[key][0]))
                self.params.item(row, COL_MAX).setText(fmt(settings.bounds[key][1]))
        for combo, value in ((self.scale_combo, settings.scale), (self.weight_combo, settings.weighting)):
            combo.setCurrentIndex(max(0, combo.findData(value)))
        # 2. Its spectra ticked (without taking their known parameters over the fit's values)
        self._filling = True
        for i in range(self.spectra_list.count()):
            item = self.spectra_list.item(i)
            item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in record.spectra
                               else Qt.CheckState.Unchecked)
        self._filling = False
        # 3. Its results
        self.spectra_used = list(record.spectra)
        self.settings_used = settings
        self.result = result_from_summary(record.result)
        self.saved_name = record.name
        self._select_saved([fid])
        self._show_result()
        self.ctx.message.emit(f'ℹ️ Memorized fit "{record.name}" shown (memorized {record.created.replace("T", " ")})')
        return True

    def export_saved_reports(self) -> list[Path]:
        """One PDF report per selected saved fit (or all), in a folder the user chooses."""
        written, problems = [], []
        fits = self._selected_fits('Reports')
        folder = self.ctx.choose_export_folder(self, 'Folder for the PDF reports') if fits else None
        for f in fits if folder else []:
            try:
                written.append(write_fit_report(report_for_fit(self.ctx.project, f),
                                                folder / f'{safe_name(f.name)}.pdf', self.ctx.point_style))
            except ValueError as e:
                problems.append(str(e))
        self._written(written, problems)
        return written

    def export_saved_figure(self) -> None:
        fits = self._selected_fits('Figure', one=True)
        if not fits:
            return
        try:
            report = report_for_fit(self.ctx.project, fits[0])
        except ValueError as e:
            QMessageBox.warning(self, 'Figure', str(e))
            return
        s = report.summary
        FigureDialog(report.spectra, s['model'], s['values'], s['scales'], self.ctx.point_style,
                     self.ctx.export_folder() / f'{safe_name(fits[0].name)}.png', self,
                     remember=self.ctx.remember_export_folder).exec()

    def export_saved_tables(self) -> list[Path]:
        """Two CSV tables (data, curve) per selected saved fit (or all), in a folder the user chooses."""
        written, problems = [], []
        project = self.ctx.project
        fits = self._selected_fits('Data tables')
        folder = self.ctx.choose_export_folder(self, 'Folder for the data tables') if fits else None
        for f in fits if folder else []:
            try:
                report = report_for_fit(project, f)
            except ValueError as e:
                problems.append(str(e))
                continue
            s = report.summary
            written += write_fit_tables(folder, safe_name(f.name), report.spectra,
                                        [project.spectra[i].sample for i in f.spectra], s['model'], s['values'],
                                        s['scales'])
        self._written(written, problems)
        return written

    def export_saved_fit_files(self) -> list[Path]:
        """One OpenDEP Fit file (.odfit) per selected saved fit (or all), in a folder the user chooses."""
        written, problems = [], []
        fits = self._selected_fits('Fit files')
        folder = self.ctx.choose_export_folder(self, 'Folder for the fit files') if fits else None
        for f in fits if folder else []:
            try:
                written.append(write_fit(saved_fit_document(self.ctx.project, f),
                                         folder / f'{safe_name(f.name)}{FIT_SUFFIX}'))
            except ValueError as e:
                problems.append(str(e))
        self._written(written, problems)
        return written

    def export_fit_table(self) -> Path | None:
        """Every saved fit in one table (a CSV file the user chooses)."""
        if not self.ctx.project.fits:
            QMessageBox.information(self, 'Table of all fits', 'No memorized fits yet: "Memorized fit" below the '
                                                               'results adds the fit on screen.')
            return None
        target = self.ctx.choose_export_file(self, 'Table of all fits', 'fits.csv', 'CSV (*.csv)')
        if target is None:
            return None
        path = write_fit_table(self.ctx.project, target)
        self._written([path], [])
        return path

    def send_saved_to_view(self) -> str:
        """
        Open the selected saved fits in OpenDEP View: one .odfit each (exports/for View/).

        Returns:
            str: "sent", "started" or "" (see ui.view_link.send_to_view).
        """
        paths, problems = [], []
        for f in self._selected_fits('Send to View'):
            try:
                paths.append(write_fit(saved_fit_document(self.ctx.project, f),
                                       view_folder(self.ctx) / f'{safe_name(f.name)}{FIT_SUFFIX}'))
            except (ValueError, OSError) as e:
                problems.append(f'{f.name}: {e}')
        if problems:
            QMessageBox.warning(self, 'Send to View', '\n'.join(problems))
        return send_to_view(self.ctx, paths, self) if paths else ''

    def remove_saved(self) -> None:
        ids = self.selected_saved_ids()
        if not ids or QMessageBox.question(self, 'Remove', f'Remove {len(ids)} memorized fit(s) from the project?') \
                != QMessageBox.StandardButton.Yes:
            return
        for fid in ids:
            self.ctx.project.fits.pop(fid, None)
        self.ctx.mark_dirty()
        self.ctx.fits_changed.emit()

    def _written(self, written: list[Path], problems: list[str]) -> None:
        if problems:
            QMessageBox.warning(self, 'Export', '\n'.join(problems))
        if written:
            self.ctx.message.emit(f'🆕 {len(written)} file(s) written to {written[0].parent}')
