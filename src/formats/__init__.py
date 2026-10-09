"""
Importers and exporters for every OpenDEP file format (Qt-free).

    read_file(path)      any supported file -> ImportResult (spectra, model curves and / or saved fits)

Readers: OpenDEP Spectrum .odspec / .ods (View v1, Control / Compute v2), OpenDEP Fit .odfit (Compute, View),
OpenDEP Curve .odcurve / .odc (View, Compute), Excel (View scatter, Compute 1.x data + fit), OpenDEP Control
experiment_parameters.csv, 3DEP .csv.
Writers: write_scatter (.odspec v2), write_fit (.odfit), write_curve (.odcurve), write_view_scatter (.xlsx).
"""
from pathlib import Path
import json

from src.data.spectrum import ImportResult
from src.formats.control_csv import read_experiment_parameters
from src.formats.dep3 import is_3dep, read_3dep
from src.formats.excel import read_excel, write_view_scatter
from src.formats.opendep_fit import FIT_SUFFIX, fit_document, is_fit_document, read_fit, write_fit
from src.formats.opendep_json import (CURVE_SUFFIX, LEGACY_CURVE_SUFFIX, LEGACY_SPECTRUM_SUFFIX, SPECTRUM_SUFFIX,
                                      read_curve, read_scatter, write_curve, write_scatter)

OPEN_FILTER = ('All supported (*.odspec *.odfit *.odcurve *.ods *.odc *.xlsx *.csv);;'
               'OpenDEP Spectrum (*.odspec *.ods);;OpenDEP Fit (*.odfit);;OpenDEP Curve (*.odcurve *.odc);;'
               'Excel (*.xlsx);;OpenDEP Control / 3DEP (*.csv)')
JSON_SUFFIXES = (SPECTRUM_SUFFIX, FIT_SUFFIX, CURVE_SUFFIX, LEGACY_SPECTRUM_SUFFIX, LEGACY_CURVE_SUFFIX, '.json')


def read_file(path: str | Path) -> ImportResult:
    """
    Read any supported file, recognising the format from its content.

    Args:
        path (str | Path): File.

    Returns:
        ImportResult: Spectra and model curves found in the file, with warnings.

    Raises:
        ValueError: Unsupported or unreadable file.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in JSON_SUFFIXES:
        # 1. A real OpenDocument spreadsheet (.ods) is a zip archive, not an OpenDEP file
        with path.open('rb') as f:
            if f.read(2) == b'PK':
                raise ValueError(f'⚠️ {path.name}: an OpenDocument / LibreOffice spreadsheet, not an OpenDEP '
                                 'spectrum (export it as .xlsx)')
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError(f'⚠️ {path.name}: not an OpenDEP JSON file') from None
        # 2. Fit, spectrum or curve, from the content (the extension may be the old one)
        if is_fit_document(data):
            return read_fit(path, data)
        if isinstance(data, dict) and 'scatter' in data:
            return read_scatter(path, data)
        if isinstance(data, dict) and ('parameters' in data or 'opendep_compute' in data):
            return read_curve(path, data)
        raise ValueError(f'⚠️ {path.name}: JSON without a scatter or a curve')
    if suffix in ('.xlsx', '.xlsm'):
        return read_excel(path)
    if suffix == '.csv':
        if is_3dep(path):
            return read_3dep(path)
        return read_experiment_parameters(path)
    raise ValueError(f'⚠️ {path.name}: unsupported file type "{suffix}"')


__all__ = ['OPEN_FILTER', 'SPECTRUM_SUFFIX', 'CURVE_SUFFIX', 'FIT_SUFFIX', 'ImportResult', 'read_file',
           'read_scatter', 'read_curve', 'read_fit', 'read_excel', 'read_experiment_parameters', 'read_3dep',
           'write_scatter', 'write_curve', 'write_fit', 'fit_document', 'write_view_scatter']
