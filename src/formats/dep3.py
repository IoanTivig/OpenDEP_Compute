"""
3DEP (DEPtech) result files (.csv): the DEP spectrum and 3DEP's own single-shell fit.

Layout (sections in the first column):
    "DEPWell experiment:, <name>, <date>, <time>"
    "DEP-Spectrum" / "Freqency [Hz], Intesity, Remarks" / one row per frequency
        remarks "Point removed from analysis / Manually removed" (left out) and "... Outlier" (outlier)
    "Auto-Fit Singel-Shell Modelparameters:" (or "Manual-Fit ...") with lines "<name>:  , <value><unit> +-<err>"
        Cytoplasm Conductivity (S/m), Cytoplasm Permitivity, Specific Membrane Conductance (S/m^2),
        Spcific Membrane Capacitance (F/m^2), Cell Radius (um), Medium Coductivity (S/m), Medium Permitivity
    "Model Spectrum", "Streched S-Curve ..." (not needed)

Spelling is 3DEP's own. The intensity is proportional to Re[K] with an unknown factor. 3DEP's own fit
(specific membrane capacitance and conductance, cytoplasm conductivity) is kept with the spectrum as
information (source["3dep_fit"], SI units), not as a model.
"""
from pathlib import Path
import re

from src.data.spectrum import SCALE_RELATIVE, ImportResult, Spectrum

# 3DEP fit lines -> (key, factor to SI except the radius, kept in µm)
FIT_KEYS = {'cytoplasm conductivity': ('sigma_cyto', 1.0), 'cytoplasm permitivity': ('eps_cyto', 1.0),
            'specific membrane conductance': ('g_mem', 1.0), 'spcific membrane capacitance': ('c_mem', 1.0),
            'specific membrane capacitance': ('c_mem', 1.0), 'cell radius': ('radius', 1.0),
            'medium coductivity': ('medium_sigma', 1.0), 'medium conductivity': ('medium_sigma', 1.0),
            'medium permitivity': ('medium_eps_r', 1.0)}
_NUMBER = re.compile(r'[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?')


def _number(text: str) -> float | None:
    m = _NUMBER.search(text or '')
    return float(m.group(0).replace(',', '.')) if m else None


def is_3dep(path: str | Path) -> bool:
    """
    True when the file starts like a 3DEP result file.
    """
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.readline().startswith('DEPWell experiment')


def read_3dep(path: str | Path) -> ImportResult:
    """
    Read a 3DEP result file.

    Args:
        path (str | Path): .csv file.

    Returns:
        ImportResult: The spectrum, with 3DEP's own fit (when present) in its source information.

    Raises:
        ValueError: No DEP-Spectrum section.
    """
    path = Path(path)
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    result = ImportResult(str(path), '3DEP csv')
    head = [x.strip() for x in lines[0].split(',')] if lines else []
    name = head[1] if len(head) > 1 and head[1] else path.stem

    # 1. 3DEP's single-shell fit (specific membrane capacitance / conductance), as information
    fit_info = _fit_info(lines)

    # 2. Spectrum
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == 'DEP-Spectrum') + 2
    except StopIteration:
        raise ValueError(f'⚠️ {path.name}: no DEP-Spectrum section (not a 3DEP result file?)') from None
    freqs, values, enabled, outlier = [], [], [], []
    for line in lines[start:]:
        parts = [p.strip() for p in line.split(' ,')]
        if len(parts) < 2 or _number(parts[0]) is None:
            break
        remark = parts[2].lower() if len(parts) > 2 else ''
        freqs.append(_number(parts[0]))
        values.append(_number(parts[1]))
        enabled.append('removed' not in remark)
        outlier.append('outlier' in remark)
    result.spectra.append(Spectrum(
        name=name, frequencies=freqs, values=values, errors=None, quantity='3dep_intensity',
        label='3DEP intensity', scale=SCALE_RELATIVE, enabled=enabled, outlier=outlier,
        source={'file': str(path), 'format': result.format, 'software': '3DEP',
                'date': ', '.join(head[2:4]) if len(head) > 3 else '', **({'3dep_fit': fit_info} if fit_info else {})},
        color='#0891B2'))
    return result


def _fit_info(lines: list[str]) -> dict | None:
    """
    3DEP's own single-shell fit: values and errors (SI; radius in µm), or None.
    """
    start = next((i for i, line in enumerate(lines) if 'Fit Singel-Shell Modelparameters' in line), None)
    if start is None:
        return None
    values, errors = {}, {}
    for line in lines[start + 1:start + 14]:
        if ':' not in line:
            continue
        label, _, rest = line.partition(':')
        key = FIT_KEYS.get(label.strip().lower())
        number = _number(rest.split('+-')[0])
        if key and number is not None:
            values[key[0]] = number * key[1]
            if '+-' in rest:
                err = _number(rest.split('+-')[1])
                if err is not None:
                    errors[key[0]] = err * key[1]
    if not values:
        return None
    return {'kind': 'auto' if 'Auto-Fit' in lines[start] else 'manual', 'values': values, 'errors': errors}
