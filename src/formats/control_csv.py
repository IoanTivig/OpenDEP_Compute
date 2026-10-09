"""
OpenDEP Control parameter files (experiment_parameters.csv) of Frequency Spectrum runs.

The file has "Parameter,Value" rows, mode sections ("--- ... ---"), a point table ("Point,Frequency (Hz),...")
and a "Results Summary (sorted, for copy-paste)" block with the main values per frequency. Every value
column of the summary with its error column (SE or Std) becomes one spectrum: DEP rate, grayness factor (ref),
grayness factor in Population mode, displacement in Single Cell mode. Raw (not normalised) values are used;
the normalisation factor is kept. Per-point data of the point table (phase, exposure, stop reason, class)
follows the spectra.

Amplitude and Time Course files are not spectra and are refused.
"""
from pathlib import Path
import csv

from src.data.spectrum import SCALE_RELATIVE, ImportResult, Spectrum

SUMMARY_MARK = 'Results Summary'
POINT_COLUMNS = {'Phase': 'phase', 'Exposure (s)': 'exposure_s', 'Stop Reason': 'stop_reason', 'Class': 'class'}
QUANTITIES = {'DEP Rate (1/s)': ('dep_rate', 'DEP rate', '1/s'),
              'Grayness Factor (ref)': ('grayness_factor_ref', 'Grayness factor (ref)', ''),
              'Grayness Factor': ('grayness_factor', 'Grayness factor', ''),
              'Displacement (um)': ('displacement', 'Displacement', 'µm'),
              'Relative CM (m/N)': ('relative_cm', 'Relative CM', 'm/N')}
COLORS = {'dep_rate': '#D97706', 'grayness_factor_ref': '#2563EB', 'grayness_factor': '#7C3AED',
          'displacement': '#059669', 'relative_cm': '#DC2626'}


def _float(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def read_experiment_parameters(path: str | Path) -> ImportResult:
    """
    Read the spectra of an OpenDEP Control Frequency Spectrum run.

    Args:
        path (str | Path): experiment_parameters.csv.

    Returns:
        ImportResult: One spectrum per measured quantity.

    Raises:
        ValueError: Not a Frequency Spectrum parameter file.
    """
    path = Path(path)
    rows = list(csv.reader(path.read_text(encoding='utf-8-sig').splitlines()))
    result = ImportResult(str(path), 'OpenDEP Control experiment_parameters.csv')

    # 1. Parameters and normalisation factors
    params, factors = {}, {}
    for r in rows:
        if len(r) >= 2 and r[0] and not r[0].startswith('---'):
            params.setdefault(r[0], r[1])
            if r[0].endswith(' Factor') and _float(r[1]) is not None:
                factors[r[0][:-len(' Factor')]] = _float(r[1])

    # 2. Summary block
    start = next((i for i, r in enumerate(rows) if r and SUMMARY_MARK in r[0]), None)
    if start is None or start + 1 >= len(rows) or not rows[start + 1] or not rows[start + 1][0].startswith('Frequency'):
        if path.name.lower() == 'experiment_parameters.csv':
            raise ValueError(f'⚠️ {path.name}: no frequency summary (Amplitude / Time Course files are not spectra)')
        raise ValueError(f'⚠️ {path.name}: not a spectrum. From OpenDEP Control import the run\'s '
                         f'experiment_parameters.csv or its spectrum_*.odspec; 3DEP exports are recognised by their '
                         f'header')
    header = rows[start + 1]
    table = []
    for r in rows[start + 2:]:
        if not r or _float(r[0]) is None:
            break
        table.append(r)
    freqs = [_float(r[0]) for r in table]

    # 3. Per-point data from the point table, matched by frequency
    points: dict[str, list] = {}
    point_start = next((i for i, r in enumerate(rows) if r and r[0] == 'Point'), None)
    if point_start is not None:
        ph = rows[point_start]
        by_freq = {}
        for r in rows[point_start + 1:]:
            if not r or _float(r[0]) is None:
                break
            row = dict(zip(ph, r))
            f = _float(row.get('Frequency (Hz)'))
            if f is not None:
                by_freq[round(f, 6)] = row
        for column, key in POINT_COLUMNS.items():
            if column in ph:
                points[key] = [by_freq.get(round(f, 6), {}).get(column, '') for f in freqs]

    # 4. One spectrum per quantity (raw values; normalised columns are skipped)
    run = path.parent.name
    source = {'file': str(path), 'format': result.format, 'software': 'OpenDEP Control',
              'measurement': 'Frequency Spectrum', 'date': params.get('Date', ''),
              'amplitude_vpp': _float(params.get('Amplitude (Vpp)')), 'exposure_s': _float(params.get('Exposure Time (s)'))}
    for i, column in enumerate(header):
        if column not in QUANTITIES or '(norm)' in column:
            continue
        quantity, label, unit = QUANTITIES[column]
        error_col = header[i + 1] if i + 1 < len(header) and (' SE' in header[i + 1] or ' Std' in header[i + 1]) \
            and '(norm)' not in header[i + 1] else None
        values = [_float(r[i]) if i < len(r) else None for r in table]
        if all(v is None for v in values):
            continue
        errors = [(_float(r[i + 1]) or 0.0) if error_col and i + 1 < len(r) else 0.0 for r in table]
        factor_key = column.replace(' (1/s)', '').replace(' (um)', '').replace(' (m/N)', '')
        raw = {'unit': unit, 'normalisation': {'method': 'cm_range', 'factor': factors[factor_key]}} \
            if factor_key in factors else {'unit': unit}
        result.spectra.append(Spectrum(
            name=f'{run} - {label}', frequencies=freqs, values=[v if v is not None else float('nan') for v in values],
            errors=errors, quantity=quantity, label=label, unit=unit, scale=SCALE_RELATIVE,
            enabled=[v is not None for v in values], points={k: list(v) for k, v in points.items()}, raw=raw,
            source={**source, 'column': column}, color=COLORS.get(quantity, '#2563EB')))
    if not result.spectra:
        raise ValueError(f'⚠️ {path.name}: the summary has no known value columns')
    return result
