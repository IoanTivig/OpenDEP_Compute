"""
Report Bug window (as in OpenDEP Control and OpenDEP View): a form for a new report and the list of saved reports.

Not modal, so it stays open while the problem is reproduced. The screenshot of the main window is taken when the
window opens, before it covers anything. Unhandled errors open it with the traceback filled in (install_crash_handler).
A report is sent to the OpenDEP website (tester account, src/diagnostics/bug_upload.py; ADR-014) or saved as a file
(src/diagnostics/bug_reports.py). Network calls run in a thread, so the window never freezes.
"""
import logging
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QObject, QSettings, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QHeaderView, QLineEdit,
                             QPlainTextEdit, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.diagnostics import bug_reports, bug_upload
from ui.widgets import SegmentedBar, button, card, label

# Where the tester's website account is kept (the token, never the password)
SERVER_KEY, USER_KEY, TOKEN_KEY = 'bug_reports/server', 'bug_reports/username', 'bug_reports/token'

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


## Website calls in the background ##


class NetworkCall(QObject):
    """
    Runs one website call in a thread; `done` (its result) or `failed` (a message for the tester and the HTTP status,
    0 without one) arrive in the GUI thread, because this object lives there.
    """
    done = pyqtSignal(object)
    failed = pyqtSignal(str, int)

    def __init__(self, function, *args) -> None:
        super().__init__()
        self.function, self.args = function, args

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            result = self.function(*self.args)
        except bug_upload.UploadError as e:
            self.failed.emit(str(e), e.status)
        except Exception as e:                          # never an unhandled error from a background call
            logger.exception('Website call failed')
            self.failed.emit(f'Unexpected error: {e}', 0)
        else:
            self.done.emit(result)


class SignInDialog(QDialog):
    """Sign in with the tester account the OpenDEP team created; keeps the website's token, not the password."""

    def __init__(self, parent: QWidget | None, settings: QSettings) -> None:
        super().__init__(parent)
        self.setWindowTitle('Sign in to the OpenDEP website')
        self.setMinimumWidth(420)
        self.settings = settings
        self.call: NetworkCall | None = None
        lay = QVBoxLayout(self)
        lay.setSpacing(6)
        lay.addWidget(label('Bug reports are accepted only from tester accounts. Ask the OpenDEP team for one.',
                            'muted', wrap=True))
        lay.addWidget(label('Website'))
        self.server_edit = QLineEdit(str(settings.value(SERVER_KEY, '') or bug_upload.default_server()))
        self.server_edit.setPlaceholderText('https://…')
        lay.addWidget(self.server_edit)
        lay.addWidget(label('User name'))
        self.user_edit = QLineEdit(str(settings.value(USER_KEY, '') or ''))
        lay.addWidget(self.user_edit)
        lay.addWidget(label('Password'))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(self.password_edit)
        self.status_label = label('', 'muted', wrap=True)
        lay.addWidget(self.status_label)
        row = QHBoxLayout()
        row.addStretch(1)
        self.sign_in_button = button('Sign in', 'primary')
        cancel = button('Cancel')
        self.sign_in_button.clicked.connect(self.sign_in)
        cancel.clicked.connect(self.reject)
        self.password_edit.returnPressed.connect(self.sign_in)
        row.addWidget(self.sign_in_button)
        row.addWidget(cancel)
        lay.addLayout(row)
        (self.password_edit if self.user_edit.text() else self.user_edit).setFocus()

    def sign_in(self) -> None:
        server, user, password = self.server_edit.text().strip(), self.user_edit.text().strip(), \
            self.password_edit.text()
        if not (server and user and password):
            self.status_label.setText('Fill in the website, your user name and your password.')
            return
        self.sign_in_button.setEnabled(False)
        self.status_label.setText('Signing in …')
        self.call = NetworkCall(bug_upload.sign_in, server, user, password)
        self.call.done.connect(lambda token: self._signed_in(server, user, token))
        self.call.failed.connect(self._failed)
        self.call.start()

    def _signed_in(self, server: str, user: str, token: str) -> None:
        self.settings.setValue(SERVER_KEY, server)
        self.settings.setValue(USER_KEY, user)
        self.settings.setValue(TOKEN_KEY, token)
        self.password_edit.clear()
        self.accept()

    def _failed(self, message: str, status: int = 0) -> None:
        self.status_label.setText(message)
        self.sign_in_button.setEnabled(True)


class BugReportDialog(QWidget):
    """
    New report (title, what I did / expected / happened, the error, console output and screenshot) and the saved
    reports (date, status, title; open one, open the folder).
    """

    def __init__(self, main_window: QWidget | None = None, reports_folder: Path = bug_reports.REPORTS_FOLDER,
                 settings: QSettings | None = None) -> None:
        super().__init__(main_window, Qt.WindowType.Window)
        self.setObjectName('ToolWindow')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle('OpenDEP Compute - Report a Bug')
        self.resize(760, 760)
        self.main_window = main_window
        self.reports_folder = Path(reports_folder)
        self.screenshot: bytes | None = None
        ctx = getattr(main_window, 'ctx', None)
        self.settings = settings or getattr(ctx, 'settings', None) or QSettings('OpenDEP', 'OpenDEP Compute')
        self.call: NetworkCall | None = None

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
        self.update_account()

    ## Layout ##

    def _build_new(self) -> QWidget:
        frame, lay = card(spacing=6)
        where = 'the bug_reports folder of the program' if not getattr(sys, 'frozen', False) else \
            str(self.reports_folder)
        lay.addWidget(label(f'Describe what went wrong. Send the report to the OpenDEP team (tester account needed), '
                            f'or save it as a file in {where}.', 'muted', wrap=True))
        account = QHBoxLayout()
        self.account_label = label('', 'muted')
        self.account_button = button('Sign in…', 'ghost')
        self.account_button.clicked.connect(self.toggle_account)
        account.addWidget(self.account_label, 1)
        account.addWidget(self.account_button)
        lay.addLayout(account)
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
        self.send_button = button('Send to OpenDEP', 'primary', None, 'Send the report to the OpenDEP team')
        self.save_button = button('Save report', None, None, 'Save the report as a file on this computer')
        self.close_button = button('Close')
        self.send_button.clicked.connect(self.send)
        self.save_button.clicked.connect(self.save)
        self.close_button.clicked.connect(self.close)
        row.addWidget(self.send_button)
        row.addWidget(self.save_button)
        row.addWidget(self.close_button)
        lay.addLayout(row)
        return frame

    def _build_list(self) -> QWidget:
        frame, lay = card(spacing=8)
        self.summary_label = label('', 'muted', wrap=True)
        lay.addWidget(self.summary_label)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Date', 'Status', 'Sent', 'Title'])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)   # several to send at once
        header = self.table.horizontalHeader()
        for column in (0, 1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.itemDoubleClicked.connect(lambda _: self.open_selected())
        lay.addWidget(self.table, 1)
        self.list_status_label = label('', 'muted', wrap=True)
        lay.addWidget(self.list_status_label)
        row = QHBoxLayout()
        self.send_selected_button = button('Send selected', 'primary', None,
                                           'Send the selected reports to the OpenDEP team (Ctrl/Shift for several)')
        self.send_unsent_button = button('Send all unsent', None, None,
                                         'Send every saved report that is not on the OpenDEP website yet')
        self.send_selected_button.clicked.connect(self.send_selected)
        self.send_unsent_button.clicked.connect(self.send_unsent)
        row.addWidget(self.send_selected_button)
        row.addWidget(self.send_unsent_button)
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
        self.clear_form()
        hint = 'Commit and push it when you finish.' if not getattr(sys, 'frozen', False) else \
            'Send it to the developers.'
        self.status_label.setText(f'Saved as {path.name}. {hint}')
        self.refresh()
        return path

    def clear_form(self) -> None:
        for edit in (self.title_edit, self.steps_edit, self.expected_edit, self.actual_edit):
            edit.clear()
        self.set_error('')
        self.screenshot_check.setChecked(False)

    ## Sending to the website ##

    def account(self) -> tuple[str, str, str]:
        """(website, user name, token) of the signed-in tester; empty token = not signed in."""
        return (str(self.settings.value(SERVER_KEY, '') or ''), str(self.settings.value(USER_KEY, '') or ''),
                str(self.settings.value(TOKEN_KEY, '') or ''))

    def update_account(self) -> None:
        server, user, token = self.account()
        if token:
            self.account_label.setText(f'Signed in to the OpenDEP website as {user}')
            self.account_button.setText('Sign out')
        else:
            self.account_label.setText('Not signed in to the OpenDEP website')
            self.account_button.setText('Sign in…')

    def toggle_account(self) -> None:
        server, _, token = self.account()
        if token:
            self.settings.remove(TOKEN_KEY)
            threading.Thread(target=bug_upload.sign_out, args=(server, token), daemon=True).start()
            self.update_account()
        else:
            self.sign_in()

    def sign_in(self) -> bool:
        """The sign-in window; True when the tester is signed in afterwards."""
        dialog = SignInDialog(self, self.settings)
        signed_in = dialog.exec() == QDialog.DialogCode.Accepted
        self.update_account()
        return signed_in

    def send(self) -> None:
        """Send the report to the website (signing in first if needed); the form is cleared once it arrived."""
        report = self.build_report()
        if not report['title']:
            self.status_label.setText('Give the report a title first.')
            self.title_edit.setFocus()
            return
        if not self.account()[2] and not self.sign_in():
            return
        server, _, token = self.account()
        self.send_button.setEnabled(False)
        self.status_label.setText('Sending …')
        self.call = NetworkCall(bug_upload.send_report, server, token, report)
        self.call.done.connect(self._sent)
        self.call.failed.connect(self._send_failed)
        self.call.start()

    def _sent(self, sent: bug_upload.Sent) -> None:
        self.send_button.setEnabled(True)
        self.clear_form()
        self.status_label.setText(f'Already on the website as report #{sent.number}: not sent again.'
                                  if sent.duplicate else f'Sent as report #{sent.number}. Thank you!')

    def _send_failed(self, message: str, status: int = 0) -> None:
        self.send_button.setEnabled(True)
        if status == 401:                               # token revoked by the team: sign in again
            self.forget_token()
        self.status_label.setText(f'Not sent: {message} You can also save the report as a file.')

    def forget_token(self) -> None:
        self.settings.remove(TOKEN_KEY)
        self.update_account()

    ## Sending saved reports ##

    def selected_paths(self) -> list[Path]:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        return [Path(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)) for row in rows]

    def send_selected(self) -> None:
        """Send the selected saved reports (those already sent are confirmed by the website, not stored twice)."""
        paths = self.selected_paths()
        if not paths:
            self.list_status_label.setText('Select the reports to send (Ctrl or Shift for several).')
            return
        self.send_saved(paths)

    def send_unsent(self) -> None:
        """Send every saved report that has no website number yet."""
        paths = [e['path'] for e in bug_reports.list_reports(self.reports_folder) if not e['sent_as']]
        if not paths:
            self.list_status_label.setText('Every saved report is already on the OpenDEP website.')
            return
        self.send_saved(paths)

    def send_saved(self, paths: list[Path]) -> None:
        """Send saved reports one by one in the background (signing in first if needed)."""
        if not self.account()[2] and not self.sign_in():
            return
        server, _, token = self.account()
        for b in (self.send_selected_button, self.send_unsent_button):
            b.setEnabled(False)
        noun = 'report' if len(paths) == 1 else 'reports'
        self.list_status_label.setText(f'Sending {len(paths)} {noun} …')
        self.call = NetworkCall(bug_upload.send_saved, server, token, paths)
        self.call.done.connect(self._saved_sent)
        self.call.failed.connect(self._saved_failed)
        self.call.start()

    def _saved_failed(self, message: str, status: int = 0) -> None:
        self._saved_sent([])
        self.list_status_label.setText(f'Not sent: {message}')

    def _saved_sent(self, results: list[dict]) -> None:
        for b in (self.send_selected_button, self.send_unsent_button):
            b.setEnabled(True)
        if any(r['status'] == 401 for r in results):    # token revoked by the team: sign in again
            self.forget_token()
        self.refresh()
        if results:
            self.list_status_label.setText(bug_upload.summary(results))

    ## Saved reports ##

    def refresh(self) -> None:
        entries = bug_reports.list_reports(self.reports_folder)
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            date = QTableWidgetItem(entry['date'])
            date.setData(Qt.ItemDataRole.UserRole, str(entry['path']))
            self.table.setItem(row, 0, date)
            self.table.setItem(row, 1, QTableWidgetItem(entry['status']))
            self.table.setItem(row, 2, QTableWidgetItem(f'#{entry["sent_as"]}' if entry['sent_as'] else ''))
            self.table.setItem(row, 3, QTableWidgetItem(entry['title']))
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
