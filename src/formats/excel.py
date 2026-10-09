"""
Excel files of OpenDEP View and OpenDEP Compute 1.x.

View scatter (3 columns): A frequency (Hz), B Re[K] ("Experimental CM factor"), C its error.
Compute 1.x data + fit (also written by its 3DEP converter):
    A frequency, B CM factor, C CM error, D DEP force, E DEP force error,
    F / G point flags ("Normal" / "Outlier" and "Enabled" / "Disabled"; the header names are swapped in
    those files, so the flags are read by their value),
    H-J the fitted curve (frequency, CM factor, DEP force),
    K-N the fit report: name, value, error, unit (model "hopa" or "sish", crossovers, parameters).
View reads the same K / L cells to load a curve from these files.
Compute 1.x image conversion ("Centralization.xlsx"): A frequency, B "Experimental grayness factor", C its error;
read as a grayness-factor spectrum (relative: fitted with a free scale factor).
"""
from pathlib import Path

from openpyxl import Workbook, load_workbook

from src.data.spectrum import SCALE_RELATIVE, ImportResult, ModelCurve, Spectrum
from src.models.catalog import MODELS

# Compute 1.x fit report names -> catalog keys
REPORT_KEYS = {
    'buffer conductivity': 'medium_sigma', 'buffer permitivity': 'medium_eps_r',
    'particle conductivity': 'sigma_p', 'particle permitivity': 'eps_p', 'particle radius': 'radius',
    'membrane thickness': 'd_mem', 'membrane conductivity': 'sigma_mem', 'membrane permitivity': 'eps_mem',
    'cytoplasm conductivity': 'sigma_cyto', 'cytoplasm permitivity': 'eps_cyto',
}

## Reading ##


def _number(value) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        return float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def read_excel(path: str | Path) -> ImportResult:
    """
    Read a View scatter or a Compute 1.x data / fit workbook.

    Args:
        path (str | Path): .xlsx file.

    Returns:
        ImportResult: The spectrum, and the fitted curve when the workbook has a fit report.

    Raises:
        ValueError: Not one of these workbooks.
    """
    path = Path(path)
    ws = load_workbook(path, data_only=True).active
    header = [str(c.value or '').strip().lower() for c in ws[1]]
    grayness = len(header) > 1 and 'grayness factor' in header[1]       # Compute 1.x conversion output
    if not header or not header[0].startswith('frequency') or len(header) < 2 or             not ('cm factor' in header[1] or grayness):
        raise ValueError(f'⚠️ {path.name}: not an OpenDEP View or Compute workbook (A1 "Frequency (Hz)", '
                         'B1 "Experimental CM factor" or "Experimental grayness factor")')
    compute1 = len(header) > 5 and header[5] in ('status', 'type')
    result = ImportResult(str(path), 'OpenDEP Compute 1.x image conversion (grayness factor)' if grayness else
                          'OpenDEP Compute 1.x workbook' if compute1 else 'OpenDEP View Excel scatter')

    # 1. Points
    freqs, values, errors, enabled, outlier, force = [], [], [], [], [], []
    for row in ws.iter_rows(min_row=2, values_only=True):
        f, v = _number(row[0]) if row else None, _number(row[1]) if len(row) > 1 else None
        if f is None or v is None:
            break
        freqs.append(f)
        values.append(v)
        errors.append(_number(row[2]) or 0.0 if len(row) > 2 else 0.0)
        flags = {str(x).strip().lower() for x in row[5:7] if x is not None} if compute1 else set()
        enabled.append('disabled' not in flags)
        outlier.append('outlier' in flags)
        force.append(_number(row[3]) if compute1 and len(row) > 3 else None)
    if not freqs:
        raise ValueError(f'⚠️ {path.name}: no data rows')
    points = {'dep_force': force} if any(x is not None for x in force) else {}
    result.spectra.append(Spectrum(
        name=path.stem, frequencies=freqs, values=values, errors=errors,
        quantity='grayness_factor' if grayness else 're_k',
        label='Grayness Factor' if grayness else 'CM factor (relative)', scale=SCALE_RELATIVE, enabled=enabled, outlier=outlier, points=points,
        source={'file': str(path), 'format': result.format}))

    # 2. Fit report (Compute 1.x)
    if compute1:
        report = {}
        for row in ws.iter_rows(min_row=2, min_col=11, max_col=14, values_only=True):
            if row[0] is None:
                continue
            report[str(row[0]).strip().lower()] = row[1]
        model_key = {'sish': 'single_shell', 'hopa': 'homogeneous'}.get(str(report.get('model', '')).strip())
        if model_key:
            model = MODELS[model_key]
            values_ = model.defaults()
            allowed = set(values_) | {'medium_sigma', 'medium_eps_r'}
            for name, key in REPORT_KEYS.items():
                number = _number(report.get(name))
                if key in allowed and number is not None:
                    values_[key] = number
            warnings = ['ℹ️ Fit from OpenDEP Compute 1.x: its parameters are kept as they were reported']
            result.curves.append(ModelCurve(f'{path.stem} (Compute 1.x fit)', model_key, values_,
                                            {'file': str(path), 'software': 'OpenDEP Compute 1.x',
                                             'r_squared': _number(report.get('rsqare'))}, warnings))
    return result


## Writing ##


def write_view_scatter(spectrum: Spectrum, path: str | Path) -> Path:
    """
    Write a spectrum as an OpenDEP View Excel scatter (3 columns; enabled points only).

    Args:
        spectrum (Spectrum): Spectrum.
        path (str | Path): Target .xlsx.

    Returns:
        Path: The file written.
    """
    wb = Workbook()
    ws = wb.active
    ws.append(['Frequency (Hz)', 'Experimental CM factor', 'Experimental CM Factor errors'])
    s = spectrum.sorted()
    for f, v, e, ok in zip(s.frequencies, s.values, s.errors, s.usable):
        if ok:
            ws.append([float(f), float(v), float(e)])
    path = Path(path)
    wb.save(path)
    return path
