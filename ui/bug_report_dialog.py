"""
Report Bug window (as in OpenDEP Control and OpenDEP View): a form for a new report and the list of saved reports.

Not modal, so it stays open while the problem is reproduced. The screenshot of the main window is taken when the
window opens, before it covers anything. Unhandled errors open it with the traceback filled in (install_crash_handler).
The report files are written by src/diagnostics/bug_reports.py.
"""
import logging
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QHBoxLayout, QHeaderView, QLineEdit, QPlainTextEdit,
                             QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.diagnostics import bug_reports
from ui.widgets import SegmentedBar, button, card, label

logger = logging.getLogger(__name__)


def widget_png(widget: QWidget) -> bytes | None:
    """PNG of a widget as currently drawn (None when it cannot be grabbed)."""
    pixmap = widget.grab()
    if pixmap.isNull():
        return None
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, 'PNG')
    return bytes(buffer.data())


def _text_box(placeholder: str, height: int = 70) -> QPlainTextEdit:
    box = QPlainTextEdit()
    box.setPlaceholderText(placeholder)
    box.setMinimumHeight(height)
    return box


class BugReportDialog(QWidget):
    """
    New report (title, what I did / expected / happened, the error, console output and screenshot) and the saved
    reports (date, status, title; open one, open the folder).
    """

    def __init__(self, main_window: QWidget | None = None, reports_folder: Path = bug_reports.REPORTS_FOLDER) -> None:
        super().__init__(main_window, Qt.WindowType.Window)
        self.setObjectName('ToolWindow')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle('OpenDEP Compute - Report a Bug')
        self.resize(760, 720)
        self.main_window = main_window
        self.reports_folder = Path(reports_folder)
        self.screenshot: bytes | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        self.tabs = SegmentedBar(['New report', 'Reports'])
        self.tabs.changed.connect(self.show_tab)
        top = QHBoxLayout()
        top.addWidget(self.tabs)
        top.addStretch(1)
        lay.addLayout(top)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_new())
        self.stack.addWidget(self._build_list())
        lay.addWidget(self.stack, 1)
        self.set_error('')
        self.refresh()

    ## Layout ##

    def _build_new(self) -> QWidget:
        frame, lay = card(spacing=6)
        where = 'in the bug_reports folder of the program. Commit and push it with the code when you finish testing.' \
            if not getattr(sys, 'frozen', False) else f'in {self.reports_folder}. Send it (with its .png) to the ' \
                                                       f'developers.'
        lay.addWidget(label(f'Describe what went wrong. The report is saved {where} Nothing is sent anywhere.',
                            'muted', wrap=True))
        lay.addWidget(label('Title'))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Short title, e.g. 'Fit stops with an error for the four-shell model'")
        lay.addWidget(self.title_edit)
        lay.addWidget(label('What I did'))
        self.steps_edit = _text_box('Files imported, model, settings and the clicks that led to the problem')
        lay.addWidget(self.steps_edit)
        lay.addWidget(label('What I expected'))
        self.expected_edit = _text_box('What should have happened', 50)
        lay.addWidget(self.expected_edit)
        lay.addWidget(label('What happened instead'))
        self.actual_edit = _text_box('Message, wrong value or curve, freeze …', 50)
        lay.addWidget(self.actual_edit)
        self.error_label = label('Error (filled in automatically)')
        lay.addWidget(self.error_label)
        self.error_edit = _text_box('', 90)
        self.error_edit.setReadOnly(True)
        lay.addWidget(self.error_edit)
        self.output_check = QCheckBox(f'Attach the console and log (last {bug_reports.LOG_LINES} lines)')
        self.output_check.setChecked(True)
        self.screenshot_check = QCheckBox('Attach a screenshot of the main window')
        lay.addWidget(self.output_check)
        lay.addWidget(self.screenshot_check)
        row = QHBoxLayout()
        self.status_label = label('', 'muted', wrap=True)
        row.addWidget(self.status_label, 1)
        self.save_button = button('Save report', 'primary')
        self.close_button = button('Close')
        self.save_button.clicked.connect(self.save)
        self.close_button.clicked.connect(self.close)
        row.addWidget(self.save_button)
        row.addWidget(self.close_button)
        lay.addLayout(row)
        return frame

    def _build_list(self) -> QWidget:
        frame, lay = card(spacing=8)
        self.summary_label = label('', 'muted', wrap=True)
        lay.addWidget(self.summary_label)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Date', 'Status', 'Title'])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.itemDoubleClicked.connect(lambda _: self.open_selected())
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        for text, slot, tip in (('Open report', self.open_selected, 'Open the selected report (double-click)'),
                                ('Open folder', self.open_folder, 'Open the reports folder'),
                                ('Refresh', self.refresh, 'Read the folder again')):
            b = button(text, None, None, tip)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        return frame

    def show_tab(self, index: int) -> None:
        self.tabs.set_index(index)
        self.stack.setCurrentIndex(index)

    ## New report ##

    def start_report(self, error: str = '') -> None:
        """An empty form (with the error, if any); the screenshot is taken now, before this window covers anything."""
        self.screenshot = widget_png(self.main_window) if self.main_window is not None else None
        self.set_error(error or bug_reports.last_error())
        self.status_label.setText('')
        self.show_tab(0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.title_edit.setFocus()

    def show_error(self, error: str) -> None:
        """An unhandled error: a new report with it, or, when the window is open, the error updated."""
        if not self.isVisible():
            self.start_report(error)
            return
        self.set_error(error)
        self.show_tab(0)
        self.raise_()

    def set_error(self, error: str) -> None:
        self.error_edit.setPlainText(error.strip())
        has_error = bool(error.strip())
        self.error_label.setVisible(has_error)
        self.error_edit.setVisible(has_error)
        if has_error and not self.title_edit.text().strip():
            self.title_edit.setText(f'Crash: {error.strip().splitlines()[-1]}'[:100])

    def context(self) -> dict:
        """Where the program was when the bug was reported (written in the report header)."""
        main = self.main_window
        if main is None or not hasattr(main, 'bug_report_context'):
            return {}
        try:
            return main.bug_report_context()
        except Exception as e:                          # the report must be saved even if this fails
            return {'context_error': repr(e)}

    def build_report(self) -> dict:
        return {'title': self.title_edit.text().strip(), 'steps': self.steps_edit.toPlainText(),
                'expected': self.expected_edit.toPlainText(), 'actual': self.actual_edit.toPlainText(),
                'error': self.error_edit.toPlainText(),
                'output': bug_reports.recent_output() if self.output_check.isChecked() else '',
                'context': {key: str(value) for key, value in self.context().items()},
                'screenshot_png': self.screenshot if self.screenshot_check.isChecked() else None}

    def save(self) -> Path | None:
        """Save the report and clear the form for the next one."""
        report = self.build_report()
        if not report['title']:
            self.status_label.setText('Give the report a title first.')
            self.title_edit.setFocus()
            return None
        try:
            path = bug_reports.save_report(report, self.reports_folder)
        except OSError as e:
            logger.error('Could not save the bug report: %s', e)
            self.status_label.setText(f'Could not save the report: {e}')
            return None
        for edit in (self.title_edit, self.steps_edit, self.expected_edit, self.actual_edit):
            edit.clear()
        self.set_error('')
        self.screenshot_check.setChecked(False)
        hint = 'Commit and push it when you finish.' if not getattr(sys, 'frozen', False) else \
            'Send it to the developers.'
        self.status_label.setText(f'Saved as {path.name}. {hint}')
        self.refresh()
        return path

    ## Saved reports ##

    def refresh(self) -> None:
        entries = bug_reports.list_reports(self.reports_folder)
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            date = QTableWidgetItem(entry['date'])
            date.setData(Qt.ItemDataRole.UserRole, str(entry['path']))
            self.table.setItem(row, 0, date)
            self.table.setItem(row, 1, QTableWidgetItem(entry['status']))
            self.table.setItem(row, 2, QTableWidgetItem(entry['title']))
        n_open = sum(entry['status'] == 'open' for entry in entries)
        noun = 'report' if len(entries) == 1 else 'reports'
        self.summary_label.setText(f'{len(entries)} {noun}, {n_open} open   ·   {self.reports_folder}' if entries
                                   else f'No reports yet   ·   {self.reports_folder}')
        self.tabs.buttons[1].setText(f'Reports ({n_open} open)' if n_open else 'Reports')

    def open_selected(self) -> None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(item.data(Qt.ItemDataRole.UserRole)))

    def open_folder(self) -> None:
        self.reports_folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.reports_folder)))


## Unhandled errors -> report window ##


class CrashNotifier(QObject):
    """Carries unhandled errors from any thread to the GUI thread."""
    crashed = pyqtSignal(str)


_crash_notifier: CrashNotifier | None = None


def install_crash_handler(on_crash) -> CrashNotifier:
    """
    Record unhandled exceptions (any thread) and pass their traceback to on_crash in the GUI thread.

    Call in the GUI thread, after the QApplication exists.
    """
    global _crash_notifier
    _crash_notifier = CrashNotifier()
    _crash_notifier.crashed.connect(on_crash)

    def handle(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        try:
            _crash_notifier.crashed.emit(bug_reports.record_error(exc_type, exc_value, exc_tb))
        except Exception:                               # the handler itself must never raise
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)    # also printed (terminal, and the attached output)

    sys.excepthook = handle
    threading.excepthook = lambda args: handle(args.exc_type, args.exc_value, args.exc_traceback)
    return _crash_notifier
