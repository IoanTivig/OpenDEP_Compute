"""
OpenDEP visual style (shared with OpenDEP View): slate palette, white cards, Segoe UI 14 px.

Resources are loaded by file path (PyQt6 has no pyrcc): `icons:<file>` and `logos:<file>`.
Widgets choose a look with dynamic properties, e.g. button.setProperty('variant', 'primary').
"""
from pathlib import Path
from PyQt6.QtCore import QDir, QEvent, QObject
from PyQt6.QtGui import QColor, QFont, QIcon, QPalette
from PyQt6.QtWidgets import QApplication, QComboBox, QStyledItemDelegate

RESOURCES = Path(__file__).resolve().parent / 'resources'

## Palette (OpenDEP View tokens) ##

BACKGROUND = '#F1F5F9'        # slate-100, window background
CARD = '#FFFFFF'
BORDER = '#E2E8F0'            # slate-200
BORDER_STRONG = '#CBD5E1'     # slate-300
TEXT = '#0F172A'              # slate-900
TEXT_MUTED = '#64748B'        # slate-500
PRIMARY = '#0F172A'
PRIMARY_HOVER = '#334155'
PRIMARY_PRESSED = '#5F728C'
SELECTED = '#DEE8F2'          # segmented tab / selection
ACCENT = '#FFB85C'            # OpenDEP logo amber
OK = '#16A34A'
WARNING = '#D97706'
ERROR = '#DC2626'

STATUS_COLORS = {'ok': OK, 'no_pattern': WARNING, 'cannot_analyse': ERROR, 'not processed': TEXT_MUTED}
STATUS_TEXT = {'ok': 'OK', 'no_pattern': 'No pattern', 'cannot_analyse': 'Cannot analyse', 'not processed': 'Not processed'}

FONT_STACK = "'Segoe UI', 'Noto Sans', 'DejaVu Sans', sans-serif"

STYLESHEET = f"""
QWidget {{
    font-family: {FONT_STACK};
    font-size: 14px;
    color: {TEXT};
}}
QMainWindow, QDialog, QWidget#Root {{ background: {BACKGROUND}; }}
QWidget#Page {{ background: transparent; }}

/* Cards */
QFrame[card="true"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QFrame[card="true"] QLabel {{ border: none; background: transparent; }}
/* A scroll area inside a card (area, viewport, content) shows the card, not a grey inner frame */
QFrame[card="true"] QScrollArea, QFrame[card="true"] QScrollArea > QWidget,
QFrame[card="true"] QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* Parameter groups inside a card (as in OpenDEP View's curve panel) */
QFrame[group="true"] {{
    background: #F8FAFC;
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QFrame[group="true"] QLabel {{ border: none; background: transparent; }}
QLabel[role="group-title"] {{ font-size: 13px; font-weight: 600; color: #334155; }}
QLabel[role="value-fitted"] {{ font-weight: 600; }}
QLabel[role="value-fixed"] {{ color: {TEXT_MUTED}; }}
QLabel[role="status-fitted"] {{ color: {OK}; font-size: 12px; }}
QLabel[role="status-fixed"] {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel[role="status-warning"] {{ color: {WARNING}; font-size: 12px; font-weight: 600; }}

/* Labels */
QLabel[role="title"] {{ font-size: 18px; font-weight: 600; }}
QLabel[role="section"] {{ font-size: 15px; font-weight: 600; }}
QLabel[role="muted"] {{ color: {TEXT_MUTED}; font-size: 13px; }}
QLabel[role="tile-value"] {{ font-size: 22px; font-weight: 600; }}
QLabel[role="tile-label"] {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel[role="banner"], QFrame[card="true"] QLabel[role="banner"] {{
    background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 6px; padding: 8px 10px; color: #9A3412;
}}
QLabel[role="info"], QFrame[card="true"] QLabel[role="info"] {{
    background: #F8FAFC; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px 10px; color: #334155;
}}

/* Buttons */
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}}
QPushButton:hover {{ background: {BACKGROUND}; }}
QPushButton:pressed {{ background: {SELECTED}; }}
QPushButton:disabled {{ color: #A0AEC0; background: #F8FAFC; border-color: #EDF2F7; }}
QPushButton[variant="primary"] {{ background: {PRIMARY}; color: #FFFFFF; border: none; }}
QPushButton[variant="primary"]:hover {{ background: {PRIMARY_HOVER}; }}
QPushButton[variant="primary"]:pressed {{ background: {PRIMARY_PRESSED}; }}
QPushButton[variant="primary"]:disabled {{ background: {BORDER_STRONG}; color: #FFFFFF; }}
QPushButton[variant="secondary"] {{ background: {BACKGROUND}; border: none; }}
QPushButton[variant="secondary"]:hover {{ background: {BORDER}; }}
QPushButton[variant="secondary"]:pressed {{ background: #C9D6E8; }}
QPushButton[variant="ghost"] {{ background: transparent; border: none; padding: 6px 8px; }}
QPushButton[variant="ghost"]:hover {{ background: {BACKGROUND}; }}
QPushButton[variant="ghost"]:pressed {{ background: {SELECTED}; }}
QPushButton[variant="danger"] {{ color: #B91C1C; }}
QPushButton[variant="danger"]:hover {{ background: #FEF2F2; }}
QPushButton[variant="danger"]:disabled {{ color: #A0AEC0; background: #F8FAFC; }}
QPushButton[segment="true"] {{ background: transparent; border: none; padding: 7px 18px; color: {TEXT}; }}
QPushButton[segment="true"]:hover {{ background: {BACKGROUND}; }}
QPushButton[segment="true"]:checked {{ background: {SELECTED}; }}   /* no bold: Qt sizes buttons with the regular weight */

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {SELECTED};
    selection-color: {TEXT};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid #94A3B8; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: #D2D7DD; border: 1px solid #D2D7DD;
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url(icons:chevron_down.png); width: 14px; height: 10px; }}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {BORDER}; selection-background-color: {SELECTED}; selection-color: {TEXT};
    outline: none; padding: 2px;
}}
QComboBox QAbstractItemView::item {{ padding: 5px 8px; border: none; border-radius: 4px; }}   /* no Fusion outline */
QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {{ background: {SELECTED}; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    border: none; width: 16px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url(icons:up_icon.png); width: 10px; height: 10px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url(icons:down_icon.png); width: 10px; height: 10px; }}

QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QTableView::indicator, QListView::indicator {{
    width: 16px; height: 16px; border: 1px solid {BORDER_STRONG}; border-radius: 4px; background: {CARD};
}}
QCheckBox::indicator:hover, QTableView::indicator:hover, QListView::indicator:hover {{ border-color: #94A3B8; }}
QCheckBox::indicator:checked, QTableView::indicator:checked, QListView::indicator:checked {{
    background: {PRIMARY}; border-color: {PRIMARY}; image: url(icons:check_white.png);
}}
QCheckBox::indicator:disabled {{ background: {BACKGROUND}; border-color: {BORDER}; }}
QRadioButton {{ spacing: 8px; background: transparent; }}
QRadioButton::indicator {{ width: 20px; height: 20px; }}
QRadioButton::indicator:unchecked {{ image: url(icons:radiobutton_unchecked.png); }}
QRadioButton::indicator:checked {{ image: url(icons:radiobutton_checked.png); }}

/* Tables and lists */
QTableWidget, QTableView, QListWidget, QTreeWidget {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: {BACKGROUND};
    alternate-background-color: #F8FAFC;
    selection-background-color: {SELECTED};
    selection-color: {TEXT};
    outline: none;
}}
QListWidget::item {{ padding: 5px 4px; border-radius: 4px; }}
QListWidget::item:hover {{ background: #F1F5F9; }}
QListWidget::item:selected {{ background: {SELECTED}; color: {TEXT}; }}   /* styled items need their own selection */

/* User guide window (as in OpenDEP View and Control): contents in a card, the page in a white frame */
QWidget#HelpWindow, QWidget#ToolWindow {{ background: {BACKGROUND}; }}   /* own windows: Help, Report bug */
QTextBrowser#HelpPage {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
}}
QTreeWidget#HelpContents {{ background: transparent; border: none; outline: 0; }}
QTreeWidget#HelpContents::item {{ padding: 4px 2px; border-radius: 4px; }}
QTreeWidget#HelpContents::item:hover {{ background: {BACKGROUND}; }}
QTreeWidget#HelpContents::item:selected {{ background: {SELECTED}; color: {TEXT}; }}

/* Thin vertical divider between groups of header buttons (as in OpenDEP Control) */
QFrame#headerDivider {{ background: {BORDER}; border: none; }}
QHeaderView::section {{
    background: #F8FAFC;
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    font-weight: 600;
    color: #334155;
}}
QTableCornerButton::section {{ background: #F8FAFC; border: none; }}

/* Progress, scrollbars, status bar, tooltips, menus */
QProgressBar {{ background: {BORDER}; border: none; border-radius: 4px; max-height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; border-radius: 5px; min-height: 24px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDER_STRONG}; border-radius: 5px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QStatusBar {{ background: {CARD}; border-top: 1px solid {BORDER}; }}
QToolTip {{ background: {PRIMARY}; color: #FFFFFF; border: none; padding: 4px 8px; }}
QMenu {{ background: {CARD}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background: {BACKGROUND}; }}
QSplitter::handle {{ background: transparent; }}
"""


class _ComboItems(QObject):
    """
    Gives every combo box a standard item delegate, so its list follows the stylesheet (flat selection, no outline).
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if (event.type() == QEvent.Type.Polish and isinstance(obj, QComboBox)
                and not isinstance(obj.itemDelegate(), QStyledItemDelegate)):
            obj.setItemDelegate(QStyledItemDelegate(obj))
        return False


def apply(app: QApplication) -> None:
    """
    Apply the OpenDEP style to the whole application.

    Args:
        app (QApplication): Application.
    """
    QDir.addSearchPath('icons', str(RESOURCES / 'icons'))
    QDir.addSearchPath('logos', str(RESOURCES / 'logos'))
    app.setStyle('Fusion')                                   # same look on Windows and Linux
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BACKGROUND))
    palette.setColor(QPalette.ColorRole.Base, QColor(CARD))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(SELECTED))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT))
    app.setPalette(palette)
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(STYLESHEET)
    app._combo_items = _ComboItems(app)                      # kept alive with the application
    app.installEventFilter(app._combo_items)
    app.setWindowIcon(QIcon(str(RESOURCES / 'icon.png')))


def icon(name: str) -> QIcon:
    """
    Icon from ui/resources/icons.

    Args:
        name (str): File name without '.png' (e.g. 'add_icon').

    Returns:
        QIcon: The icon.
    """
    return QIcon(str(RESOURCES / 'icons' / f'{name}.png'))
