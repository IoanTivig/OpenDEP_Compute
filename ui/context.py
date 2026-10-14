"""
Application state shared by the pages: the open project, recent projects, change signals, and where exports go.
"""
import hashlib
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QWidget

from src.project.project import Project
from src.project.sorting import FIT_SORTS, SPECTRA_SORTS

RECENT_MAX = 8
POINT_STYLES = ('errorbars', 'area')           # as in OpenDEP View: points with error bars, or a band


class AppContext(QObject):
    """
    The open project and the signals pages use to stay in sync.
    """
    project_changed = pyqtSignal()                 # opened / created / closed
    spectra_changed = pyqtSignal()                 # added, removed, renamed, flags edited
    curves_changed = pyqtSignal()
    fits_changed = pyqtSignal()
    message = pyqtSignal(str)                      # status-bar text
    point_style_changed = pyqtSignal()
    sort_changed = pyqtSignal()                    # order of the spectra (Data and Fit) or of the memorized fits

    def __init__(self, parent: QObject | None = None, settings: QSettings | None = None) -> None:
        """
        Args:
            parent (QObject | None): Parent.
            settings (QSettings | None): Settings store (tests pass a temporary one).
        """
        super().__init__(parent)
        self.settings = settings or QSettings('OpenDEP', 'OpenDEP Compute')
        self.project: Project | None = None
        self.dirty = False
        style = self.settings.value('point_style', 'errorbars')
        self.point_style = style if style in POINT_STYLES else 'errorbars'
        # Order of the lists (remembered): one for the spectra of the Data and Fit pages, one for the memorized fits
        sort = self.settings.value('sort/spectra', 'added')
        self.spectra_sort = sort if sort in SPECTRA_SORTS else 'added'
        sort = self.settings.value('sort/fits', 'added')
        self.fit_sort = sort if sort in FIT_SORTS else 'added'

    # -- project --

    def set_project(self, project: Project | None) -> None:
        self.project = project
        self.dirty = False
        if project is not None:
            self._remember(project.path)
        self.project_changed.emit()

    def mark_dirty(self) -> None:
        self.dirty = True

    def save(self) -> None:
        if self.project is not None:
            self.project.save()
            self.dirty = False
            self.message.emit(f'ℹ️ Project saved: {self.project.path}')

    def set_point_style(self, style: str) -> None:
        """How measured points are drawn: 'errorbars' or 'area' (remembered)."""
        if style in POINT_STYLES and style != self.point_style:
            self.point_style = style
            self.settings.setValue('point_style', style)
            self.point_style_changed.emit()

    def set_spectra_sort(self, sort: str) -> None:
        """Order of the spectra, the same on the Data and Fit pages (a key of SPECTRA_SORTS; remembered)."""
        if sort in SPECTRA_SORTS and sort != self.spectra_sort:
            self.spectra_sort = sort
            self.settings.setValue('sort/spectra', sort)
            self.sort_changed.emit()

    def set_fit_sort(self, sort: str) -> None:
        """Order of the memorized fits (a key of FIT_SORTS; remembered)."""
        if sort in FIT_SORTS and sort != self.fit_sort:
            self.fit_sort = sort
            self.settings.setValue('sort/fits', sort)
            self.sort_changed.emit()

    # -- export folder --
    # Every export asks where to write (a folder, or a file for a single report / table). The dialogs start in the
    # last folder used for this project (remembered in the settings), the first time in the project folder.

    def _export_key(self) -> str:
        return 'export_folder/' + hashlib.sha1(str(self.project.path.resolve()).encode()).hexdigest()[:16]

    def export_folder(self) -> Path:
        """Where the export dialogs start: the last folder used for this project, else the project folder."""
        if self.project is None:
            return Path.home()
        saved = self.settings.value(self._export_key(), '')
        return Path(saved) if saved and Path(saved).is_dir() else self.project.folder

    def remember_export_folder(self, folder: str | Path) -> None:
        if self.project is not None and folder:
            self.settings.setValue(self._export_key(), str(Path(folder)))

    def choose_export_folder(self, parent: QWidget | None, title: str) -> Path | None:
        """Ask for the folder of a batch export (None = cancelled); the choice is remembered."""
        folder = QFileDialog.getExistingDirectory(parent, title, str(self.export_folder()))
        if not folder:
            return None
        self.remember_export_folder(folder)
        return Path(folder)

    def choose_export_file(self, parent: QWidget | None, title: str, name: str, file_filter: str) -> Path | None:
        """Ask for the file of a single export, proposing `name` in the export folder (None = cancelled)."""
        path, _ = QFileDialog.getSaveFileName(parent, title, str(self.export_folder() / name), file_filter)
        if not path:
            return None
        self.remember_export_folder(Path(path).parent)
        return Path(path)

    # -- recent projects --

    def recent(self) -> list[str]:
        value = self.settings.value('recent_projects', [])
        items = [value] if isinstance(value, str) else list(value or [])
        # project files; folders of older versions (with project.json) still listed until saved as a file
        return [p for p in items if Path(p).is_file() or (Path(p) / 'project.json').is_file()]

    def _remember(self, root: Path) -> None:
        items = [str(root)] + [p for p in self.recent() if Path(p) != Path(root)]
        self.settings.setValue('recent_projects', items[:RECENT_MAX])
