"""
Publication figure dialog: a fitted spectrum at a journal size, previewed at its real proportions, saved as
PNG / TIFF (600 dpi), SVG or PDF.
"""
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QMessageBox,
                             QVBoxLayout, QWidget)

from src.data.spectrum import Spectrum
from src.report.report import FIGURE_FORMATS, FIGURE_SIZES, fit_figure, save_figure
from ui.widgets import button, label

FILTER = ';;'.join(f'{text} (*{ext})' for ext, text in FIGURE_FORMATS.items())


class FigureDialog(QDialog):
    """
    Figure of one fit.
    """

    def __init__(self, spectra: list[Spectrum], model: str, values: dict, scales: list[float], style: str,
                 default_path: Path, parent: QWidget | None = None, remember=None) -> None:
        """remember (callable | None): called with the folder a figure was saved in (the next export starts there)."""
        super().__init__(parent)
        self.setWindowTitle('Publication figure')
        self.resize(900, 640)
        self.args = (spectra, model, values, scales)
        self.style = style
        self.default_path = default_path
        self.remember = remember
        self.saved: Path | None = None
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        form = QFormLayout()
        self.size_combo = QComboBox()
        for key, (text, w, h) in FIGURE_SIZES.items():
            self.size_combo.addItem(f'{text}, {w} x {h} mm', key)
        form.addRow('Size', self.size_combo)
        self.residuals_check = QCheckBox('Residual panel')
        self.residuals_check.setChecked(True)
        self.legend_check = QCheckBox('Legend')
        self.legend_check.setChecked(True)
        form.addRow('', self.residuals_check)
        form.addRow('', self.legend_check)
        left.addLayout(form)
        left.addWidget(label('Points are drawn as on the Fit page (error bars or area). Text is 8-9 pt Arial; '
                             'PNG and TIFF at 600 dpi, SVG and PDF keep text as text.', 'muted', wrap=True))
        left.addStretch(1)
        save = button('Save…', 'primary', 'save_icon')
        save.clicked.connect(self.save)
        close = button('Close')
        close.clicked.connect(self.reject)
        left.addWidget(save)
        left.addWidget(close)
        lay.addLayout(left)
        self.preview = QVBoxLayout()
        lay.addLayout(self.preview, 1)
        self.canvas: FigureCanvasQTAgg | None = None
        for w in (self.size_combo,):
            w.currentIndexChanged.connect(self.redraw)
        for w in (self.residuals_check, self.legend_check):
            w.toggled.connect(self.redraw)
        self.redraw()

    def figure(self):
        return fit_figure(*self.args, size=self.size_combo.currentData(), style=self.style,
                          residuals=self.residuals_check.isChecked(), legend=self.legend_check.isChecked())

    def redraw(self) -> None:
        if self.canvas is not None:
            self.preview.removeWidget(self.canvas)
            self.canvas.deleteLater()
        self.canvas = FigureCanvasQTAgg(self.figure())
        self.preview.addWidget(self.canvas)

    def save_to(self, path: str | Path) -> Path:
        """Save the figure (any FIGURE_FORMATS suffix)."""
        self.saved = save_figure(self.figure(), path)
        return self.saved

    def save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Save figure', str(self.default_path), FILTER)
        if not path:
            return
        try:
            self.save_to(path)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, 'Figure', str(e))
            return
        self.default_path = Path(path)                   # a second save in this dialog starts there
        if self.remember is not None:
            self.remember(Path(path).parent)
        QMessageBox.information(self, 'Figure', f'Saved: {path}')
