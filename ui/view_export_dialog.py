"""
Export a fit as files: the fit (.odfit: spectra, fitted curve and scale factors in one file; the default), and
optionally the separate files: the fitted curve (.odcurve), the fitted spectra on the Re[K] scale (.odspec, one per
spectrum), the fitted curve as points (.odspec), and plain CSV tables of the data and the curve.
"""
from pathlib import Path
from typing import Callable

from PyQt6.QtWidgets import QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from src.formats.opendep_fit import FIT_SUFFIX, write_fit
from src.formats.opendep_json import CURVE_SUFFIX, SPECTRUM_SUFFIX, write_curve, write_scatter
from ui.widgets import button, label, safe_name


class ViewExportDialog(QDialog):
    """
    What to write, and where.
    """

    def __init__(self, folder: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Export fit')
        lay = QVBoxLayout(self)
        lay.addWidget(label('The fit as files, written to the folder below. OpenDEP View and Compute open the .odfit file.', 'muted', wrap=True))
        self.fit_check = QCheckBox(f'Fit ({FIT_SUFFIX}): the spectra, the fitted curve and the scale factors in one '
                                   'file; View opens them linked, each spectrum on the curve')
        self.fit_check.setChecked(True)
        lay.addWidget(self.fit_check)
        lay.addWidget(label('Separate files', 'muted'))
        self.curve_check = QCheckBox(f'Fitted curve ({CURVE_SUFFIX}): the model with its fitted values')
        self.points_check = QCheckBox(f'Fitted spectra on the Re[K] scale ({SPECTRUM_SUFFIX}): each spectrum divided '
                                      'by its scale factor, one file per spectrum')
        self.curve_points_check = QCheckBox(f'Fitted curve as points ({SPECTRUM_SUFFIX}): 200 points, for programs '
                                            'that read only spectrum files')
        self.tables_check = QCheckBox('Data tables (CSV): every point with its scale factor, Re[K], the fitted value '
                                      'and the residual; the fitted curve as a second table')
        for c in (self.curve_check, self.points_check, self.curve_points_check, self.tables_check):
            lay.addWidget(c)
        row = QHBoxLayout()
        self.folder_edit = QLineEdit(str(folder))
        browse = button('Browse…')
        browse.clicked.connect(self._browse)
        row.addWidget(label('Folder'))
        row.addWidget(self.folder_edit, 1)
        row.addWidget(browse)
        lay.addLayout(row)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = button('Export', 'primary')
        cancel = button('Cancel')
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        lay.addLayout(buttons)
        self.resize(620, 260)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Folder', self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def write(self, name: str, fit: dict, curve, scaled: list, curve_points,
              tables: Callable[[Path], list[Path]] | None = None) -> list[Path]:
        """
        Write the ticked files.

        Args:
            name (str): Fit name (file names).
            fit (dict): OpenDEP Fit document (opendep_fit.fit_document).
            curve (ModelCurve): Fitted curve.
            scaled (list[Spectrum]): Fitted spectra on the Re[K] scale.
            curve_points (Spectrum): Fitted curve as points.
            tables (Callable | None): Writes the CSV tables into a folder and returns their paths.

        Returns:
            list[Path]: Files written.
        """
        folder = Path(self.folder_edit.text())
        folder.mkdir(parents=True, exist_ok=True)
        written = []
        if self.fit_check.isChecked():
            written.append(write_fit(fit, folder / f'{safe_name(name)}{FIT_SUFFIX}'))
        if self.curve_check.isChecked():
            written.append(write_curve(curve, folder / f'{safe_name(name)} - curve{CURVE_SUFFIX}'))
        if self.points_check.isChecked():
            written += [write_scatter(s, folder / f'{safe_name(s.name)}{SPECTRUM_SUFFIX}') for s in scaled]
        if self.curve_points_check.isChecked():
            written.append(write_scatter(curve_points, folder / f'{safe_name(name)} - curve points{SPECTRUM_SUFFIX}'))
        if self.tables_check.isChecked() and tables is not None:
            written += tables(folder)
        return written
