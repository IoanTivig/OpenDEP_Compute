"""
Main window: header, welcome screen, the workspace pages (Data, Fit). Exports are made where their content is
(spectra: Data page; fits and memorized fits: Fit page), each to a folder or file the user chooses.
"""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                             QStackedWidget, QVBoxLayout, QWidget)

from src import __version__
from src.project.project import PROJECT_SUFFIX, Project, ProjectError
from ui import theme
from ui.context import AppContext
from ui.bug_report_dialog import BugReportDialog
from ui.help_window import HELP_PAGES, HelpWindow
from ui.pages.data_page import DataPage
from ui.pages.fit_page import FitPage
from ui.widgets import SegmentedBar, button, card, label

APP_NAME = 'OpenDEP Compute'
PROJECT_FILTER = (f'OpenDEP Compute project (*{PROJECT_SUFFIX});;'
                  'Project folder of an older version (project.json)')
PAGES = ('Data', 'Fit')


class MainWindow(QMainWindow):
    """
    Top-level window.
    """

    def __init__(self, context: AppContext | None = None) -> None:
        super().__init__()
        self.ctx = context or AppContext(self)
        self.setWindowTitle(f'{APP_NAME} {__version__}')
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        root = QWidget()
        root.setObjectName('Root')
        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)
        outer.addWidget(self._build_header())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_welcome())
        self.stack.addWidget(self._build_workspace())
        outer.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage('Ready')

        QShortcut(QKeySequence('Ctrl+N'), self, self.new_project)
        QShortcut(QKeySequence('Ctrl+O'), self, self.open_project_dialog)
        QShortcut(QKeySequence('Ctrl+S'), self, self.save_project)
        QShortcut(QKeySequence('F1'), self, self.show_help)
        self.help_window: HelpWindow | None = None
        self.bug_window: BugReportDialog | None = None
        self.ctx.project_changed.connect(self._on_project_changed)
        self.ctx.message.connect(lambda text: self.statusBar().showMessage(text, 8000))
        self._on_project_changed()

    ## Layout ##

    def _build_header(self) -> QWidget:
        frame, lay = card('h', margins=8)
        lay.addWidget(self._logo(22))
        lay.addSpacing(4)
        lay.addWidget(label(APP_NAME, 'title'))
        lay.addSpacing(16)
        self.project_label = label('', 'muted')
        lay.addWidget(self.project_label)
        lay.addStretch(1)
        self.new_button = button('New project', 'ghost', 'add_circle_icon', 'Create a new project (Ctrl+N)')
        self.open_button = button('Open project', 'ghost', 'open_folder_icon', 'Open a project (Ctrl+O)')
        self.save_button = button('Save', 'ghost', 'save_icon', 'Save the project (Ctrl+S)')
        self.help_button = button('Help', 'ghost', 'help_icon', 'User guide of the page in use (F1)')
        self.bug_button = button('Report bug', 'ghost', 'bug_icon', 'Report a bug: describe the problem, with the '
                                 'last error and output attached (saved as a file; nothing is sent)')
        self.bug_button.clicked.connect(self.show_bug_report)
        self.help_button.clicked.connect(self.show_help)
        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project_dialog)
        self.save_button.clicked.connect(self.save_project)
        for b in (self.new_button, self.open_button, self.save_button):
            lay.addWidget(b)
        lay.addWidget(self._divider())                  # project | help and bug reports
        for b in (self.help_button, self.bug_button):
            lay.addWidget(b)
        return frame

    def _build_welcome(self) -> QWidget:
        page = QWidget()
        page.setObjectName('Page')
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        frame, box = card(margins=28, spacing=12)
        frame.setFixedWidth(560)
        box.addWidget(self._logo(48))
        box.addWidget(label(f'Welcome to {APP_NAME}', 'title'))
        box.addWidget(label('Import DEP spectra from OpenDEP Control, OpenDEP View, OpenDEP Compute 1.x or 3DEP, '
                            'fit them with dielectric cell models and export the results. A project keeps copies '
                            'of the imported spectra and the fits; your original files are never modified.', 'muted', wrap=True))
        buttons = QHBoxLayout()
        create = button('Create new project', 'primary')
        open_ = button('Open project', None, 'open_folder_icon')
        create.clicked.connect(self.new_project)
        open_.clicked.connect(self.open_project_dialog)
        buttons.addWidget(create)
        buttons.addWidget(open_)
        buttons.addStretch(1)
        box.addLayout(buttons)
        box.addWidget(label('Recent projects', 'section'))
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(180)
        self.recent_list.itemActivated.connect(lambda item: self.open_project(item.data(Qt.ItemDataRole.UserRole)))
        box.addWidget(self.recent_list)
        row.addWidget(frame)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(2)
        return page

    def _build_workspace(self) -> QWidget:
        page = QWidget()
        page.setObjectName('Page')
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.tabs = SegmentedBar(list(PAGES))
        bar = QHBoxLayout()
        bar.addWidget(self.tabs)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.pages = QStackedWidget()
        self.data_page, self.fit_page = DataPage(self.ctx), FitPage(self.ctx)
        for w in (self.data_page, self.fit_page):
            self.pages.addWidget(w)
        self.tabs.changed.connect(self.show_page)
        lay.addWidget(self.pages, 1)
        return page

    @staticmethod
    def _divider() -> QFrame:
        """Thin vertical divider between groups of header buttons (as in OpenDEP Control)."""
        divider = QFrame()
        divider.setObjectName('headerDivider')
        divider.setFixedSize(1, 24)
        return divider

    @staticmethod
    def _logo(height: int):
        widget = label()
        ratio = widget.devicePixelRatioF() or 1.0
        pixmap = QPixmap(str(theme.RESOURCES / 'logos' / 'opendep_symbol_crop.png')).scaledToHeight(
            round(height * ratio), Qt.TransformationMode.SmoothTransformation)
        pixmap.setDevicePixelRatio(ratio)
        widget.setPixmap(pixmap)
        return widget

    def show_page(self, index: int) -> None:
        self.tabs.set_index(index)
        self.pages.setCurrentIndex(index)

    ## Help ##

    def help_page(self) -> str:
        """Guide page of what is on screen."""
        if self.stack.currentIndex() == 0:
            return HELP_PAGES['start']
        return HELP_PAGES[PAGES[self.pages.currentIndex()]]

    def show_help(self) -> None:
        if self.help_window is None:
            self.help_window = HelpWindow(self)
        self.help_window.open_page(self.help_page())
        self.help_window.show()
        self.help_window.raise_()
        self.help_window.activateWindow()

    ## Bug reports ##

    def bug_report_window(self) -> BugReportDialog:
        """The Report bug window, created on first use."""
        if self.bug_window is None:
            self.bug_window = BugReportDialog(self)
        return self.bug_window

    def show_bug_report(self) -> None:
        self.bug_report_window().start_report()

    def show_bug_report_for_error(self, error: str) -> None:
        """An unhandled error: the Report bug window with the traceback filled in."""
        self.bug_report_window().show_error(error)

    def bug_report_context(self) -> dict:
        """Where the program was when the bug was reported (written in the report header)."""
        project = self.ctx.project
        fit = self.fit_page
        context = {'screen': 'workspace' if project else 'welcome screen',
                   'page': PAGES[self.pages.currentIndex()] if project else '',
                   'project': str(project.path) if project else 'none',
                   'unsaved_changes': self.ctx.dirty}
        if project:
            context.update({
                'spectra': len(project.spectra), 'saved_fits': len(project.fits),
                'model': fit.model_combo.currentText(), 'ticked_spectra': len(fit.ticked_ids()),
                'fit_on_screen': (f'{fit.result.model}, R² {fit.result.r_squared:.4f}'
                                  + (f' (memorized fit "{fit.saved_name}")' if fit.saved_name else ''))
                                 if fit.result is not None else 'none'})
        return context

    ## Projects ##

    def _on_project_changed(self) -> None:
        project = self.ctx.project
        self.stack.setCurrentIndex(1 if project else 0)
        self.save_button.setEnabled(project is not None)
        self.project_label.setText(f'{project.name}   ·   {project.path}' if project else 'No project open')
        self.recent_list.clear()
        for path in self.ctx.recent():
            item = QListWidgetItem(f'{Path(path).name}   —   {path}')
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.recent_list.addItem(item)

    def _confirm_discard(self) -> bool:
        if self.ctx.project is None or not self.ctx.dirty:
            return True
        answer = QMessageBox.question(self, APP_NAME, 'Save the changes to the open project?',
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                                      | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            self.ctx.save()
        return answer != QMessageBox.StandardButton.Cancel

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        start = Path(self.ctx.recent()[0]).parent if self.ctx.recent() else Path.home()
        path, _ = QFileDialog.getSaveFileName(self, 'New project', str(start / f'New project{PROJECT_SUFFIX}'),
                                              PROJECT_FILTER.split(';;')[0])
        if not path:
            return
        try:
            self.ctx.set_project(Project.create(path))
        except (ProjectError, OSError) as e:
            QMessageBox.warning(self, APP_NAME, str(e))

    def open_project_dialog(self) -> None:
        start = str(Path(self.ctx.recent()[0]).parent) if self.ctx.recent() else ''
        path, _ = QFileDialog.getOpenFileName(self, 'Open project', start, PROJECT_FILTER)
        if path:
            self.open_project(path)

    def open_project(self, path: str) -> None:
        """Open a project file (or an older project folder); tell what could not be read or was converted."""
        if not self._confirm_discard():
            return
        try:
            project = Project.open(path)
        except ProjectError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        self.ctx.set_project(project)
        if project.converted_from is not None:
            self.ctx.mark_dirty()                        # so that closing asks to save the new file
            QMessageBox.information(self, APP_NAME, f'This is a project folder of an older version. Save writes it '
                                    f'as one file:\n\n{project.path}\n\nThe folder is left as it is; you can '
                                    f'delete it once the new file is saved.')
        if project.problems:
            listing = '\n'.join(f'• {p}' for p in project.problems[:20])
            more = f'\n… and {len(project.problems) - 20} more' if len(project.problems) > 20 else ''
            QMessageBox.warning(self, APP_NAME, f'The project opened, but {len(project.problems)} part(s) could not '
                                f'be read and are left out:\n\n{listing}{more}\n\nSaving now removes them from the '
                                f'project; the backup ({project.path.name}.bak) keeps the previous version.')

    def save_project(self) -> None:
        self.ctx.save()

    def closeEvent(self, event) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
