"""
A fit's data and curve as spectra on the Re[K] scale (Qt-free), for OpenDEP Spectrum (.odspec) files that OpenDEP
View opens next to the model curve (.odcurve).

A relative spectrum (grayness factor, DEP rate) is put on the Re[K] axis by dividing values and errors by the scale
factor the fit found for it, exactly as the Fit page plots it. Nothing is lost: the original values and errors and
the factor are kept in the file ("raw", "normalisation"), with the fit's model and R² in "source".

Also the saved fits of a project: one CSV table of all, and the OpenDEP Fit document (.odfit) of one.
"""
import csv
from pathlib import Path

import numpy as np

from src.data.spectrum import SCALE_ABSOLUTE, ModelCurve, Spectrum
from src.formats.opendep_fit import fit_document
from src.models.catalog import MEDIUM_PARAMETERS, MODELS, cm_factor


def scaled_spectrum(spectrum: Spectrum, scale: float, model: str, r_squared: float) -> Spectrum:
    """
    A fitted spectrum divided by its scale factor (Re[K] axis), points and flags kept.

    Args:
        spectrum (Spectrum): The measured spectrum.
        scale (float): Its scale factor in the fit.
        model (str): Catalog model key of the fit.
        r_squared (float): R² of the fit.
    """
    raw = {'unit': spectrum.unit, 'label': spectrum.label, 'values': [float(v) for v in spectrum.values],
           'errors': [float(e) for e in spectrum.errors],
           'normalisation': {'method': 'fit_scale_factor', 'factor': float(scale)}}
    source = {**spectrum.source, 'fit_model': MODELS[model].name, 'fit_r_squared': float(r_squared),
              'fit_scale_factor': float(scale), 'software': 'OpenDEP Compute'}
    name = f'{spectrum.name} (Re[K], ÷ {scale:.3g})' if scale != 1 else f'{spectrum.name} (Re[K])'
    return Spectrum(name, spectrum.frequencies.copy(), spectrum.values / scale, spectrum.errors / scale, 're_k',
                    'Re[K]', '', SCALE_ABSOLUTE, spectrum.enabled.copy(), spectrum.outlier.copy(),
                    {k: list(v) for k, v in spectrum.points.items()}, raw, dict(spectrum.known_parameters), source,
                    spectrum.color)


def curve_spectrum(name: str, model: str, values: dict[str, float], f_min: float, f_max: float,
                   n: int = 200) -> Spectrum:
    """
    The fitted Re[K] sampled at `n` log-spaced frequencies, as points (no errors).

    Args:
        name (str): Name.
        model (str): Catalog model key.
        values (dict[str, float]): Fitted and fixed values (display units).
        f_min / f_max (float): Frequency range (Hz).
        n (int): Number of points.
    """
    f = np.logspace(np.log10(f_min), np.log10(f_max), n)
    k = cm_factor(MODELS[model], f, values).real
    return Spectrum(name, f, k, np.zeros(n), 're_k', 'Re[K]', '', SCALE_ABSOLUTE,
                    source={'software': 'OpenDEP Compute', 'fit_model': MODELS[model].name,
                            'model_values': dict(values), 'kind': 'fitted curve'},
                    color='#0F172A')


## Plain tables (CSV) ##
# For other software or for working by hand: one header row, one row per point, '.' as decimal separator.
# UTF-8 with a byte-order mark, so Excel shows µ, ² and Greek letters correctly; other programs ignore it.

CSV_ENCODING = 'utf-8-sig'


def _quantity_text(spectrum: Spectrum) -> str:
    return f'{spectrum.label} ({spectrum.unit})' if spectrum.unit else spectrum.label


def write_spectrum_csv(spectrum: Spectrum, path: str | Path) -> Path:
    """
    A spectrum as a CSV table: every point (sorted by frequency) with its error and flags.

    Columns: Frequency (Hz), value, error (empty when unknown), Use (1/0), Outlier (1/0).
    """
    s = spectrum.sorted()
    path = Path(path)
    with open(path, 'w', newline='', encoding=CSV_ENCODING) as fh:
        w = csv.writer(fh)
        w.writerow(['Frequency (Hz)', _quantity_text(s), 'Error', 'Use', 'Outlier'])
        for f, v, e, use, out in zip(s.frequencies, s.values, s.errors, s.enabled, s.outlier):
            w.writerow([f'{f:.10g}', f'{v:.10g}', f'{e:.6g}' if e > 0 else '', int(use), int(out)])
    return path


def write_fit_tables(folder: str | Path, name: str, spectra: list[Spectrum], samples: list[str], model: str,
                     values: dict[str, float], scales: list[float], n_curve: int = 200) -> list[Path]:
    """
    A fit's data as two CSV tables: "<name> - data.csv" and "<name> - curve.csv".

    Data: one row per measured point of every spectrum (sorted by frequency): Spectrum, Sample, Frequency (Hz),
    Value, Error (as measured), Scale factor, Re[K] data = value / scale, Re[K] error = error / scale, Re[K] fit
    (the fitted curve at that frequency), Residual = data - fit, Used (1 = in the fit; 0 = left out or outlier).
    Curve: the fitted Re[K] and Im[K] at n_curve log-spaced frequencies over the data range (÷3 / ×3, as plotted).

    Returns:
        list[Path]: [data table, curve table].
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cat = MODELS[model]
    data_path = folder / f'{name} - data.csv'
    with open(data_path, 'w', newline='', encoding=CSV_ENCODING) as fh:
        w = csv.writer(fh)
        w.writerow(['Spectrum', 'Sample', 'Frequency (Hz)', 'Value', 'Error', 'Scale factor', 'Re[K] data',
                    'Re[K] error', 'Re[K] fit', 'Residual', 'Used'])
        for spectrum, sample, scale in zip(spectra, samples, scales):
            s = spectrum.sorted()
            fit = cm_factor(cat, s.frequencies, values).real
            for f, v, e, k, used in zip(s.frequencies, s.values, s.errors, fit, s.usable):
                err = f'{e:.6g}' if e > 0 else ''
                w.writerow([s.name, sample, f'{f:.10g}', f'{v:.10g}', err, f'{scale:.10g}', f'{v / scale:.10g}',
                            f'{e / scale:.6g}' if e > 0 else '', f'{k:.10g}', f'{v / scale - k:.6g}', int(used)])
    used_f = np.concatenate([s.frequencies[s.frequencies > 0] for s in spectra])
    f = np.logspace(np.log10(used_f.min() / 3), np.log10(used_f.max() * 3), n_curve)
    k = cm_factor(cat, f, values)
    curve_path = folder / f'{name} - curve.csv'
    with open(curve_path, 'w', newline='', encoding=CSV_ENCODING) as fh:
        w = csv.writer(fh)
        w.writerow(['Frequency (Hz)', 'Re[K] fit', 'Im[K] fit'])
        for fi, ki in zip(f, k):
            w.writerow([f'{fi:.10g}', f'{ki.real:.10g}', f'{ki.imag:.10g}'])
    return [data_path, curve_path]


## Saved fits ##


def write_fit_table(project, path: str | Path) -> Path:
    """
    All saved fits in one CSV: one row per fit, value and standard error of every parameter.

    Args:
        project (Project): Project.
        path (str | Path): Target file.

    Returns:
        Path: The file written.
    """
    keys = []
    for f in project.fits.values():
        for k in f.result['parameters']:
            if k not in keys:
                keys.append(k)
    defs = {p.key: p for m in MODELS.values() for p in m.parameters + MEDIUM_PARAMETERS}
    header = ['Fit', 'Model', 'Spectra', 'Samples', 'R2', 'Points', 'Free', 'Crossovers (Hz)']
    for k in keys:
        unit = f' ({defs[k].unit})' if defs[k].unit else ''
        header += [f'{k}{unit}', f'{k} SE', f'{k} status']
    path = Path(path)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for f in project.fits.values():
            st = f.result['statistics']
            spectra = [project.spectra[s] for s in f.spectra if s in project.spectra]
            row = [f.name, MODELS[f.result['model']].name, '; '.join(e.spectrum.name for e in spectra),
                   '; '.join(sorted({e.sample for e in spectra if e.sample})), st['r_squared'],
                   st['n_points'], st['n_free'],
                   '; '.join(f'{c[0]:.6g} {c[1]}' for c in f.result['crossovers'])]
            for k in keys:
                p = f.result['parameters'].get(k)
                if p is None:
                    row += ['', '', '']
                else:
                    status = 'fixed' if not p['free'] else ('not determined' if not p['determined'] else 'fitted')
                    row += [p['value'], p['stderr'] if p['stderr'] is not None else '', status]
            w.writerow(row)
    return path


def saved_fit_document(project, record) -> dict:
    """
    OpenDEP Fit document of a saved fit: its spectra (original values), the fitted curve, scale factors, results.

    Args:
        project (Project): Project.
        record (FitRecord): Saved fit.

    Returns:
        dict: JSON document.

    Raises:
        ValueError: Some of the fit's spectra were removed from the project.
    """
    entries = [project.spectra[s] for s in record.spectra if s in project.spectra]
    if len(entries) != len(record.spectra):
        raise ValueError(f'⚠️ Fit "{record.name}": some of its spectra were removed from the project')
    result = record.result
    spectra = [e.spectrum for e in entries]
    curve = ModelCurve(f'Fit: {record.name}', result['model'], dict(result['values']),
                       {'software': 'OpenDEP Compute', 'fit_r_squared': result['statistics']['r_squared']},
                       color=spectra[0].color if len(spectra) == 1 else '#DC2626')
    return fit_document(record.name, spectra, curve, result['scales'], result.get('scale_errors'),
                        [e.sample for e in entries], record.settings, result)
