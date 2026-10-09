"""
OpenDEP Fit files (.odfit): spectra, a model curve and the link between them, in one JSON file (ADR-010).

Shared by OpenDEP Compute and OpenDEP View:
    "format": "OpenDEP Fit", "format_version": 1, "name", "created", "program"
    "spectra":  complete OpenDEP Spectrum documents (.odspec v2) with their ORIGINAL values
    "curve":    a complete OpenDEP Curve document (.odcurve), with Compute's exact model block
    "links":    one per spectrum: {"spectrum": index, "scale": s, "scale_error": se, "sample": name,
                "biological": label (optional, from OpenDEP View replicate groups: spectra with the same label are
                technical replicates of one suspension)}
                a spectrum is drawn on the curve's Re[K] axis as value / scale (scale 1: as it is)
    "group":    optional, from OpenDEP View: the replicate group's name, look and average (mean ± SD per point)
    "fit":      {"settings": FitSettings fields, "result": fit_summary() (values ± SE, R², crossovers)}
                written by Compute after a fit; absent in files without a fit behind them (View links made
                by hand, or a curve changed in View after the fit)

Spectra are stored unscaled so the data exist once; the scale lives in the link. A file from View may carry
only "spectra", "curve" and "links".
"""
from datetime import datetime
from pathlib import Path
import json

from src import __version__
from src.data.spectrum import ImportResult, ModelCurve, Spectrum
from src.formats.opendep_json import curve_document, read_curve, read_scatter, scatter_document

FIT_FORMAT = 'OpenDEP Fit'
FIT_VERSION = 1
FIT_SUFFIX = '.odfit'

## Writing ##


def fit_document(name: str, spectra: list[Spectrum], curve: ModelCurve, scales: list[float] | None = None,
                 scale_errors: list[float | None] | None = None, samples: list[str] | None = None,
                 settings: dict | None = None, result: dict | None = None) -> dict:
    """
    OpenDEP Fit document.

    Args:
        name (str): Fit name.
        spectra (list[Spectrum]): Spectra, with their original values.
        curve (ModelCurve): Fitted (or linked) model curve.
        scales (list[float] | None): Scale factor of each spectrum (default 1).
        scale_errors (list[float | None] | None): Standard error of each scale factor.
        samples (list[str] | None): Sample / replicate group of each spectrum.
        settings (dict | None): Fit settings (FitSettings fields); None without a fit.
        result (dict | None): fit_summary() of the fit; None without a fit.

    Returns:
        dict: JSON document.
    """
    n = len(spectra)
    scales = list(scales) if scales is not None else [1.0] * n
    scale_errors = list(scale_errors) if scale_errors is not None else [None] * n
    samples = list(samples) if samples is not None else [''] * n
    links = [{'spectrum': i, 'scale': float(scales[i]),
              'scale_error': None if scale_errors[i] is None else float(scale_errors[i]), 'sample': samples[i]}
             for i in range(n)]
    document = {'format': FIT_FORMAT, 'format_version': FIT_VERSION, 'name': name,
                'created': datetime.now().isoformat(timespec='seconds'),
                'program': f'OpenDEP Compute {__version__}',
                'spectra': [scatter_document(s) for s in spectra], 'curve': curve_document(curve), 'links': links}
    if result is not None:
        document['fit'] = {'settings': settings or {}, 'result': result}
    return document


def write_fit(document: dict, path: str | Path) -> Path:
    """
    Write an OpenDEP Fit document.

    Args:
        document (dict): From fit_document().
        path (str | Path): Target file.

    Returns:
        Path: The file written.
    """
    path = Path(path)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False), encoding='utf-8')
    return path


## Reading ##


def is_fit_document(data: object) -> bool:
    """
    True for the content of an OpenDEP Fit file.
    """
    return isinstance(data, dict) and (data.get('format') == FIT_FORMAT
                                       or {'spectra', 'curve', 'links'} <= set(data))


def read_fit(path: str | Path, data: dict | None = None) -> ImportResult:
    """
    Read an OpenDEP Fit file: its spectra, its curve and (when present) the fit, as an import result.

    The fit goes to `ImportResult.fits` as {'name', 'spectra' (indices into `spectra`), 'samples', 'scales',
    'settings', 'result'}; Project.add_import turns it into a saved fit of the new spectra.

    Args:
        path (str | Path): File.
        data (dict | None): Already parsed JSON.

    Returns:
        ImportResult: Spectra, the curve and the fit.

    Raises:
        ValueError: A link points to a spectrum the file does not have.
    """
    path = Path(path)
    data = data if data is not None else json.loads(path.read_text(encoding='utf-8'))
    result = ImportResult(str(path), f'{FIT_FORMAT} v{data.get("format_version", 1)}')
    for document in data.get('spectra', []):
        part = read_scatter(path, document)
        result.spectra += part.spectra
    if data.get('curve'):
        part = read_curve(path, data['curve'])
        result.curves += part.curves
        result.warnings += part.warnings

    links = data.get('links', [])
    if any(not 0 <= int(link['spectrum']) < len(result.spectra) for link in links):
        raise ValueError(f'⚠️ {path.name}: a link points to a spectrum the file does not have')
    # Replicate structure from OpenDEP View: the sample and the biological replicate (suspension) of each spectrum
    for link in links:
        source = result.spectra[int(link['spectrum'])].source
        if link.get('biological') is not None:
            source['biological_replicate'] = str(link['biological'])
        if link.get('sample'):
            source.setdefault('sample', link['sample'])
    fit = data.get('fit')
    if fit and fit.get('result'):
        result.fits.append({'name': data.get('name') or path.stem,
                            'spectra': [int(link['spectrum']) for link in links],
                            'samples': [link.get('sample', '') for link in links],
                            'scales': [float(link.get('scale', 1.0)) for link in links],
                            'settings': fit.get('settings', {}), 'result': fit['result']})
    else:
        result.warnings.append('ℹ️ No fit results in this file (spectra and model only, e.g. linked in OpenDEP View)')
    return result
