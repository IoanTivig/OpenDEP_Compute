"""
The user guide inside the application (as in OpenDEP Control).

The guide is the Markdown in docs/ (also readable on GitHub). Qt renders Markdown itself (QTextBrowser), so no
build step, browser or internet is needed. Help / F1 opens the page of the page in use (HELP_PAGES); links between
pages, "#section" links and a full-text search work inside the window; web links open in the browser.
"""
from pathlib import Path
import re
import sys

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QKeySequence, QPalette, QShortcut, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (QHBoxLayout, QLineEdit, QSplitter, QTextBrowser, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from ui.widgets import button, card, label

# Frozen application: docs/ is shipped next to the program (PyInstaller data)
DOCS_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])) / 'docs'

# Table of contents: (section, [(title, page relative to docs/)])
CONTENTS: list[tuple[str, list[tuple[str, str]]]] = [
    ('Getting started', [
        ('Overview', 'index.md'),
        ('Installation', 'installation.md'),
        ('Quick start', 'quickstart.md'),
    ]),
    ('User guide', [
        ('Projects, data and fitting', 'user-guide/workflow.md'),
        ('Converting images', 'user-guide/conversion.md'),
        ('Figures and reports', 'user-guide/reports.md'),
        ('File formats', 'user-guide/file-formats.md'),
    ]),
    ('Concepts', [
        ('Dielectric models', 'concepts/models.md'),
        ('Fitting', 'concepts/fitting.md'),
    ]),
    ('Help', [
        ('Troubleshooting', 'troubleshooting.md'),
        ('Changes', 'changelog.md'),
    ]),
]

# Page for each page of the program (MainWindow.help_page builds the key)
HELP_PAGES: dict[str, str] = {
    'start': 'quickstart.md',
    'Data': 'user-guide/workflow.md#data',
    'Fit': 'user-guide/workflow.md#fit',
}

# Markdown niceties Qt shows plainly: tables get borders and padding
LINK = '#2563EB'

# Markdown as in OpenDEP View's guide: heading sizes, bordered tables, code and quote backgrounds, blue links
_STYLE = """
h1 { font-size: 22px; font-weight: 600; }
h2 { font-size: 18px; font-weight: 600; margin-top: 16px; }
h3 { font-size: 15px; font-weight: 600; margin-top: 12px; }
table { border-collapse: collapse; margin: 6px 0; }
th, td { border: 1px solid #CBD5E1; padding: 4px 8px; }
th { background-color: #F1F5F9; }
code { background-color: #F1F5F9; font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: 13px; }
blockquote { background-color: #F8FAFC; margin: 6px 0; }
a { color: #2563EB; }
"""


def slug(text: str) -> str:
    """GitHub-style heading anchor: "Converting images" -> "converting-images"."""
    text = re.sub(r'[^\w\s-]', '', text.strip().lower())
    return re.sub(r'\s+', '-', text)


class HelpWindow(QWidget):
    """
    Table of contents, search and the rendered page.
    """

    def __init__(self, parent: QWidget | None = None, docs_dir: Path = DOCS_DIR) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        # Its own window: "Page" (transparent, for pages inside the main window) left it black
        self.setObjectName('HelpWindow')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.docs_dir = docs_dir
        self.setWindowTitle('OpenDEP Compute - User Guide')
        self.resize(1100, 760)
        self._search_terms: list[str] = []

        self.back_button = button('← Back', None, None, 'Previous page (Alt+Left)')
        self.forward_button = button('Forward →', None, None, 'Next page (Alt+Right)')
        self.home_button = button('Contents', None, None, 'The overview page of the guide')
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search the guide (Ctrl+F)…')
        self.search.setClearButtonEnabled(True)
        self.matches_label = label('', 'muted')
        bar = QHBoxLayout()
        for b in (self.back_button, self.forward_button, self.home_button):
            bar.addWidget(b)
        bar.addSpacing(12)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.matches_label)

        self.tree = QTreeWidget()
        self.tree.setObjectName('HelpContents')
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(230)
        self._items: dict[str, QTreeWidgetItem] = {}
        for section, pages in CONTENTS:
            parent_item = QTreeWidgetItem([section])
            parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            self.tree.addTopLevelItem(parent_item)
            for title, page in pages:
                item = QTreeWidgetItem([title])
                item.setData(0, Qt.ItemDataRole.UserRole, page)
                parent_item.addChild(item)
                self._items[page] = item
        self.tree.expandAll()

        self.browser = QTextBrowser()
        self.browser.setObjectName('HelpPage')
        palette = self.browser.palette()                 # links in the suite's blue, visited or not
        palette.setColor(QPalette.ColorRole.Link, QColor(LINK))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(LINK))
        self.browser.setPalette(palette)
        self.browser.setOpenLinks(False)                 # links handled in _on_link (pages, anchors, web)
        self.browser.document().setDefaultStyleSheet(_STYLE)
        self.browser.setSearchPaths([str(self.docs_dir)])

        contents, contents_lay = card(margins=8)
        contents_lay.addWidget(self.tree)
        splitter = QSplitter()
        splitter.addWidget(contents)
        splitter.addWidget(self.browser)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 840])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        lay.addLayout(bar)
        lay.addWidget(splitter, 1)

        self.back_button.clicked.connect(self.browser.backward)
        self.forward_button.clicked.connect(self.browser.forward)
        self.home_button.clicked.connect(lambda: self.open_page('index.md'))
        self.browser.backwardAvailable.connect(self.back_button.setEnabled)
        self.browser.forwardAvailable.connect(self.forward_button.setEnabled)
        self.browser.anchorClicked.connect(self._on_link)
        self.browser.sourceChanged.connect(self._on_source_changed)
        self.tree.itemClicked.connect(self._on_tree_item)
        self.search.textChanged.connect(self._on_search)
        self.search.returnPressed.connect(self._find_next)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self.search.setFocus)
        QShortcut(QKeySequence.StandardKey.FindNext, self, activated=self._find_next)
        QShortcut(QKeySequence('Alt+Left'), self, activated=self.browser.backward)
        QShortcut(QKeySequence('Alt+Right'), self, activated=self.browser.forward)
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)

    ## Navigation ##

    def open_page(self, page: str) -> bool:
        """
        Show a page ('user-guide/workflow.md', optionally with '#section').

        Returns:
            bool: True when the page exists (otherwise the contents page is shown).
        """
        path_part, _, fragment = page.partition('#')
        path = self.docs_dir / path_part
        if not path.is_file():
            path, fragment = self.docs_dir / 'index.md', ''
            if not path.is_file():
                self.browser.setPlainText(f'The user guide was not found in {self.docs_dir}.')
                return False
        url = QUrl.fromLocalFile(str(path))
        if fragment:
            url.setFragment(fragment)
        self.browser.setSource(url, QTextDocument.ResourceType.MarkdownResource)
        return path_part == str(path.relative_to(self.docs_dir)).replace('\\', '/')

    def current_page(self) -> str:
        """Page shown now, relative to docs/."""
        return self._page_of(self.browser.source())

    def _page_of(self, url: QUrl) -> str:
        try:
            return str(Path(url.toLocalFile()).resolve().relative_to(self.docs_dir.resolve())).replace('\\', '/')
        except ValueError:
            return ''

    def _on_link(self, url: QUrl) -> None:
        """Pages and anchors open here; web links in the browser."""
        if url.scheme() in ('http', 'https', 'mailto'):
            QDesktopServices.openUrl(url)
            return
        if url.isRelative() and not url.path():          # "#section" on this page
            self._scroll_to(url.fragment())
            return
        target = self.browser.source().resolved(url)
        local = Path(target.toLocalFile())
        if local.suffix.lower() == '.md' and local.is_file():
            self.browser.setSource(target, QTextDocument.ResourceType.MarkdownResource)
        elif local.is_file():
            QDesktopServices.openUrl(target)

    def _on_source_changed(self, url: QUrl) -> None:
        """Select the page in the tree, jump to the section, highlight the search words."""
        item = self._items.get(self._page_of(url))
        if item is not None:
            self.tree.setCurrentItem(item)
        if url.fragment():
            self._scroll_to(url.fragment())
        if self._search_terms:
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            self._find_next()

    def _scroll_to(self, fragment: str) -> None:
        """Scroll to the heading whose GitHub-style anchor is `fragment`."""
        block = self.browser.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel() > 0 and slug(block.text()) == fragment:
                self.browser.setTextCursor(QTextCursor(block))
                self.browser.verticalScrollBar().setValue(
                    int(self.browser.document().documentLayout().blockBoundingRect(block).top()))
                return
            block = block.next()

    def _on_tree_item(self, item: QTreeWidgetItem) -> None:
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page:
            self.open_page(page)

    ## Search ##

    def _page_text(self, page: str) -> str:
        try:
            return (self.docs_dir / page).read_text(encoding='utf-8').lower()
        except OSError:
            return ''

    def _on_search(self, text: str) -> None:
        """Show only the pages containing every word; highlight the first match."""
        self._search_terms = [w for w in text.lower().split() if w]
        matches = 0
        for page, item in self._items.items():
            hit = not self._search_terms or all(t in self._page_text(page) for t in self._search_terms)
            item.setHidden(not hit)
            matches += hit
        for i in range(self.tree.topLevelItemCount()):
            section = self.tree.topLevelItem(i)
            section.setHidden(all(section.child(k).isHidden() for k in range(section.childCount())))
        self.matches_label.setText(f'{matches} page{"s" if matches != 1 else ""}' if self._search_terms else '')
        if self._search_terms and self.current_page() in self._items and self._items[self.current_page()].isHidden():
            first = next((p for p, it in self._items.items() if not it.isHidden()), None)
            if first:
                self.open_page(first)
                return
        if self._search_terms:
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            self._find_next()

    def _find_next(self) -> None:
        """Highlight the next occurrence of the first search word on the page (wraps)."""
        if not self._search_terms:
            return
        word = self._search_terms[0]
        if not self.browser.find(word):
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            self.browser.find(word)
