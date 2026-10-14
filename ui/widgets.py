"""
Reusable widgets in the OpenDEP style: cards, buttons, segmented bar, stat tiles, plots, image view.
"""
from pathlib import Path
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget, QTableWidgetItem)

from ui import theme

## Basic building blocks ##


def safe_name(name: str) -> str:
    """A file name from free text (characters Windows forbids replaced)."""
    return ''.join(c if c.isalnum() or c in ' -_.()' else '_' for c in name).strip() or 'export'


def card(layout: str = 'v', margins: int = 12, spacing: int = 8) -> tuple[QFrame, QVBoxLayout | QHBoxLayout]:
    """
    White card with a thin border.

    Args:
        layout (str): 'v' (vertical) or 'h' (horizontal).
        margins (int): Inner margin in px.
        spacing (int): Space between children.

    Returns:
        tuple[QFrame, layout]: The card and its layout.
    """
    frame = QFrame()
    frame.setProperty('card', True)
    lay = QVBoxLayout(frame) if layout == 'v' else QHBoxLayout(frame)
    lay.setContentsMargins(margins, margins, margins, margins)
    lay.setSpacing(spacing)
    return frame, lay


def label(text: str = '', role: str | None = None, wrap: bool = False) -> QLabel:
    """
    Label with an optional style role ('title', 'section', 'muted', 'banner', 'info', ...).

    Args:
        text (str): Text.
        role (str | None): Style role.
        wrap (bool): Wrap long text.

    Returns:
        QLabel: The label.
    """
    widget = QLabel(text)
    if role:
        widget.setProperty('role', role)
    widget.setWordWrap(wrap)
    return widget


def button(text: str = '', variant: str | None = None, icon_name: str | None = None, tooltip: str = '') -> QPushButton:
    """
    Button in one of the OpenDEP variants: None (outline), 'primary', 'secondary', 'ghost', 'danger'.

    Args:
        text (str): Caption.
        variant (str | None): Style variant.
        icon_name (str | None): Icon file name from ui/resources/icons (without .png).
        tooltip (str): Tooltip.

    Returns:
        QPushButton: The button.
    """
    widget = QPushButton(text)
    if variant:
        widget.setProperty('variant', variant)
    if icon_name:
        widget.setIcon(theme.icon(icon_name))
        widget.setIconSize(QSize(18, 18))
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def sort_combo(options: dict[str, str], current: str, on_change, tooltip: str = '') -> QComboBox:
    """
    Drop-down list of the orders of a list (Sort), its value the order's key.

    Args:
        options (dict[str, str]): Order key -> label (src.project.sorting).
        current (str): Key shown first.
        on_change (callable): Called with the chosen key.
        tooltip (str): Tooltip.

    Returns:
        QComboBox: The list; set_combo_key() changes it without calling on_change.
    """
    widget = QComboBox()
    for key, text in options.items():
        widget.addItem(text, key)
    set_combo_key(widget, current)
    widget.setToolTip(tooltip)
    widget.currentIndexChanged.connect(lambda: on_change(widget.currentData()))
    return widget


def set_combo_key(widget: QComboBox, key: str) -> None:
    """Show the item whose value is key (signals blocked: no on_change)."""
    widget.blockSignals(True)
    widget.setCurrentIndex(max(widget.findData(key), 0))
    widget.blockSignals(False)


def hline() -> QFrame:
    """
    Thin horizontal separator.

    Returns:
        QFrame: Separator.
    """
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f'background: {theme.BORDER}; border: none;')
    return line


def color_icon(color: str, size: int = 14):
    """
    Rounded color swatch as an icon (category colors).

    Args:
        color (str): Hex color.
        size (int): Size in px.

    Returns:
        QIcon: Swatch icon.
    """
    from PyQt6.QtGui import QIcon, QPainter
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 3, 3)
    painter.end()
    return QIcon(pixmap)


def ci_text(metrics: dict) -> str:
    """
    '95 % CI 92.5–99.8 %' for a metrics dict with 'accuracy_ci95', or '' if unavailable.

    Args:
        metrics (dict): Output of evaluate().

    Returns:
        str: Confidence interval text.
    """
    ci = metrics.get('accuracy_ci95') if metrics else None
    if not ci or ci[0] is None or ci[0] != ci[0]:
        return ''
    return f'95 % CI {100 * ci[0]:.1f}–{100 * ci[1]:.1f} %'


def status_item(status: str) -> QTableWidgetItem:
    """
    Table cell showing a pipeline status with its color.

    Args:
        status (str): 'ok', 'no_pattern', 'cannot_analyse' or 'not processed'.

    Returns:
        QTableWidgetItem: Cell.
    """
    item = QTableWidgetItem(theme.STATUS_TEXT.get(status, status))
    item.setForeground(QColor(theme.STATUS_COLORS.get(status, theme.TEXT)))
    item.setData(Qt.ItemDataRole.UserRole, status)
    return item


def read_only(text: str, align_right: bool = False) -> QTableWidgetItem:
    """
    Non-editable table cell.

    Args:
        text (str): Text.
        align_right (bool): Right-align (numbers).

    Returns:
        QTableWidgetItem: Cell.
    """
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if align_right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


## Segmented bar (like OpenDEP View's 'Curve plots | Scatter plots') ##


class SegmentedBar(QFrame):
    """
    Row of mutually exclusive toggle buttons inside a card.
    """
    changed = pyqtSignal(int)

    def __init__(self, items: list[str], parent: QWidget | None = None):
        """
        Args:
            items (list[str]): Captions.
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        self.setProperty('card', True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for i, text in enumerate(items):
            b = QPushButton(text)
            b.setProperty('segment', True)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
            self.buttons.append(b)
        self.buttons[0].setChecked(True)
        self.group.idClicked.connect(self.changed.emit)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_index(self, index: int) -> None:
        self.buttons[index].setChecked(True)

    def index(self) -> int:
        return self.group.checkedId()


## Stat tile ##


class StatTile(QFrame):
    """
    Small card with a big number and a caption.
    """

    def __init__(self, caption: str, value: str = '-', parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty('card', True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(0)
        self.value_label = label(value, 'tile-value')
        self.caption_label = label(caption, 'tile-label', wrap=True)    # wraps so many tiles still fit a row
        self.caption_label.setMinimumWidth(90)
        lay.addWidget(self.value_label)
        lay.addWidget(self.caption_label)

    def set_caption(self, caption: str) -> None:
        """
        Update the caption (e.g. to add a confidence interval).

        Args:
            caption (str): Caption text.
        """
        self.caption_label.setText(caption)
        self.setToolTip(caption)                    # the full text when the tile is too narrow

    def set_value(self, value: str, color: str | None = None) -> None:
        """
        Update the number.

        Args:
            value (str): Text to show.
            color (str | None): Optional text color.
        """
        self.value_label.setText(value)
        self.value_label.setStyleSheet(f'color: {color};' if color else '')


## Matplotlib canvas ##


class PlotCanvas(FigureCanvasQTAgg):
    """
    Matplotlib figure styled to match the app.
    """

    RESIZE_DELAY_MS = 120                            # redraw once the size has settled

    def __init__(self, width: float = 5, height: float = 3.5, parent: QWidget | None = None):
        self.figure = Figure(figsize=(width, height), facecolor='white', layout='constrained')
        super().__init__(self.figure)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # A full redraw (constrained layout included) takes ~140 ms: done at every step of a window or splitter
        # drag it made the page sluggish. While resizing, the last picture stays and one redraw follows the end.
        self._resizing = False
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(self.RESIZE_DELAY_MS)
        self._resize_timer.timeout.connect(self._resize_done)

    def resizeEvent(self, event) -> None:
        self._resizing = True                        # matplotlib's resizeEvent asks for a redraw: postponed
        try:
            super().resizeEvent(event)
        finally:
            self._resizing = False
        self._resize_timer.start()

    def draw_idle(self) -> None:
        if self._resizing:
            return
        super().draw_idle()

    def _resize_done(self) -> None:
        try:
            self.draw_idle()
        except RuntimeError:                         # widget already deleted
            pass

    def clear(self):
        """
        Remove all axes.
        """
        self.figure.clear()

    def draw(self):
        """Draw, unless the widget was closed while a redraw was still queued."""
        try:
            super().draw()
        except RuntimeError:                         # C++ widget already deleted (window closed)
            pass

    @staticmethod
    def style(ax) -> None:
        """
        Light axes style (slate grid, no top/right spines).

        Args:
            ax: Matplotlib axes.
        """
        ax.spines[['top', 'right']].set_visible(False)
        for side in ('left', 'bottom'):
            ax.spines[side].set_color('#94A3B8')
        ax.tick_params(colors='#334155', labelsize=9)
        ax.grid(color='#E2E8F0', linewidth=0.8)
        ax.set_axisbelow(True)


## Image view ##


def array_to_pixmap(array: np.ndarray, vmin: float | None = None, vmax: float | None = None) -> QPixmap:
    """
    Grayscale array (NaN = transparent-ish white) to a pixmap.

    Args:
        array (np.ndarray): 2D array.
        vmin (float | None): Black level (default: 1st percentile).
        vmax (float | None): White level (default: 99th percentile).

    Returns:
        QPixmap: Image.
    """
    valid = np.isfinite(array)
    lo = np.nanpercentile(array, 1) if vmin is None else vmin
    hi = np.nanpercentile(array, 99) if vmax is None else vmax
    scaled = np.clip((np.nan_to_num(array, nan=hi) - lo) / max(hi - lo, 1e-9), 0, 1)
    gray = (scaled * 255).astype(np.uint8)
    gray[~valid] = 245
    gray = np.ascontiguousarray(gray)
    h, w = gray.shape
    image = QImage(gray.data, w, h, w, QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(image.copy())


class ImageView(QLabel):
    """
    Label that shows an image scaled to fit, keeping its aspect ratio.
    """

    def __init__(self, parent: QWidget | None = None, placeholder: str = 'No image selected'):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._placeholder = placeholder
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setText(placeholder)
        self.setProperty('role', 'muted')

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        if pixmap is None or pixmap.isNull():
            self.clear()
            self.setText(self._placeholder)
        self._refresh()

    def set_file(self, path: str | Path) -> None:
        self.set_pixmap(QPixmap(str(path)))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return                                   # keep the placeholder text
        super().setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation))
