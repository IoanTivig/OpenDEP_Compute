"""
OpenDEP JSON files: "OpenDEP Spectrum" (.odspec, a measured spectrum) and "OpenDEP Curve" (.odcurve, a model
curve).

Extensions: .odspec and .odcurve since 2026-10 (ADR-009). The older .ods ("OpenDEP Scatter") and .odc are the same
JSON content and are still read; they clashed with the OpenDocument spreadsheet (.ods) and Office data connection
(.odc) files that Windows opens with LibreOffice / Excel. Files are recognised by their content, not the extension.

Spectrum, version 1 (OpenDEP View 1.x): name, color, point_size, point_style, visibility, widget, and
    "scatter": {"frequencies", "recm_values", "recm_errors"}.
Spectrum, version 2 (OpenDEP Control, OpenDEP Compute): the same keys, plus "format" ("OpenDEP Spectrum"; "OpenDEP
    Scatter" in .ods files), "format_version", "quantity", "label", "normalisation" {method, factor}, "raw" {unit,
    values, errors}, "points" (per-point lists), "known_parameters" (curve names, e.g. core_radius in µm), "source",
    "created". View reads only the version-1 keys, so both versions open in View.

Curve (OpenDEP View): "format" ("OpenDEP Curve", absent in .odc files), "format_version" (2: outer radius),
    name, color, line_style, line_width, visibility, widget, "model" (0 homogeneous,
    1 single-shell, 2 two-shell, 3 three-shell, 4 four-shell), "parameters" (buffer_perm, buffer_cond, core_perm,
    core_cond, core_radius µm, 1st_shell_perm / _cond / _thick nm, 2nd_shell_*, electric_field, crossovers;
    core_surface_cond nS; nucleus_radius µm, envelope_thick nm, envelope_perm / _cond, nucleoplasm_perm / _cond),
    "curves" (sampled curves) and "radius_convention". Layers: core = cytoplasm (homogeneous: the particle),
    1st shell = membrane, 2nd shell = cell wall. OpenDEP Compute adds an "opendep_compute" block with its own model
    key and values; when present it is used instead of the View fields.

"radius_convention": "outer" (OpenDEP View 2, PyQt6): core_radius is the outer radius for every model, and the
two-shell formula is the correct one. Older View files have no such key: their two-shell core_radius is the core
radius (both shells outside it) and their two-shell formula combined the outer shell with the raw inner-shell
permittivity instead of the equivalent one; such curves are converted to the outer radius, recomputed with the
correct model, and a warning says so.
"""
from datetime import datetime
from pathlib import Path
import json

import numpy as np

from src import __version__
from src.data.spectrum import SCALE_RELATIVE, ImportResult, ModelCurve, Spectrum
from src.models.catalog import MODELS, cm_factor

SCATTER_FORMAT = 'OpenDEP Spectrum'
SCATTER_FORMATS = (SCATTER_FORMAT, 'OpenDEP Scatter')     # current name, name in .ods files
SCATTER_VERSION = 2
CURVE_FORMAT = 'OpenDEP Curve'
CURVE_VERSION = 2                                          # 2: outer radius for every model (OpenDEP View 2)
CURVE_BLOCK = 'opendep_compute'

# File extensions: written, and still read (older files)
SPECTRUM_SUFFIX = '.odspec'
CURVE_SUFFIX = '.odcurve'
LEGACY_SPECTRUM_SUFFIX = '.ods'
LEGACY_CURVE_SUFFIX = '.odc'

# Curve-file / known_parameters names -> catalog keys (display units match: µm, nm, S/m)
KNOWN_PARAMETER_KEYS = {'core_radius': 'radius', 'buffer_cond': 'medium_sigma', 'buffer_perm': 'medium_eps_r'}
VIEW_MODELS = {0: 'homogeneous', 1: 'single_shell', 2: 'two_shell', 3: 'three_shell', 4: 'four_shell'}
# Key of each model in View's "curves" (recm_<key>) and cross-overs
VIEW_CURVE_KEYS = {'homogeneous': 'homogenous_particle', 'single_shell': 'single_shell', 'two_shell': 'two_shell',
                   'three_shell': 'three_shell', 'four_shell': 'four_shell'}
VIEW_CROSSOVER_KEYS = ('homogenous', 'single_shell', 'two_shell', 'three_shell', 'four_shell')
RADIUS_OUTER = 'outer'

## Scatter ##


def read_scatter(path: str | Path, data: dict | None = None) -> ImportResult:
    """
    Read an OpenDEP Spectrum file (.odspec, or .ods; version 1 or 2).

    Args:
        path (str | Path): File.
        data (dict | None): Already parsed JSON (skips reading the file).

    Returns:
        ImportResult: One spectrum.
    """
    path = Path(path)
    data = data if data is not None else json.loads(path.read_text(encoding='utf-8'))
    scatter = data['scatter']
    version = int(data.get('format_version', 1)) if data.get('format') in SCATTER_FORMATS else 1
    result = ImportResult(str(path), f'{SCATTER_FORMAT} v{version}')
    n = len(scatter['frequencies'])
    errors = scatter.get('recm_errors') or [0.0] * n
    points = {k: list(v) for k, v in (data.get('points') or {}).items() if isinstance(v, list) and len(v) == n}
    enabled = points.pop('enabled', None)
    outlier = points.pop('outlier', None)
    known = {}
    for key, value in (data.get('known_parameters') or {}).items():
        target = KNOWN_PARAMETER_KEYS.get(key, key)
        if isinstance(value, (int, float)):
            known[target] = float(value)
    normalisation = data.get('normalisation') or {}
    raw = dict(data.get('raw') or {})
    if normalisation:
        raw['normalisation'] = normalisation
    source = dict(data.get('source') or {})
    source.update({'file': str(path), 'format': result.format})
    label = data.get('label') or 'Re[K] (relative)'
    if normalisation.get('method') == 'cm_range':
        label = f'{label} (scaled to the CM range)'
    spectrum = Spectrum(
        name=data.get('name') or path.stem, frequencies=scatter['frequencies'], values=scatter['recm_values'],
        errors=errors, quantity=data.get('quantity', 're_k'), label=label, unit='',
        # Measured spectra are proportional to Re[K] with an unknown factor; View scatters carry no
        # information either way, so they are treated the same (a free scale factor of 1 costs nothing)
        scale=data.get('scale', SCALE_RELATIVE), enabled=enabled, outlier=outlier, points=points, raw=raw,
        known_parameters=known, source=source, color=data.get('color') or '#2563EB')
    if version == 1:
        result.warnings.append('ℹ️ View scatter (version 1): treated as proportional to Re[K] (free scale factor)')
    result.spectra.append(spectrum)
    return result


def scatter_document(spectrum: Spectrum) -> dict:
    """
    OpenDEP Spectrum version-2 document of a spectrum (readable by OpenDEP View).

    Args:
        spectrum (Spectrum): Spectrum.

    Returns:
        dict: JSON document.
    """
    def floats(a) -> list[float]:
        return [float(x) for x in a]

    points = {k: list(v) for k, v in spectrum.points.items()}
    points['enabled'] = [bool(x) for x in spectrum.enabled]
    points['outlier'] = [bool(x) for x in spectrum.outlier]
    known = {('core_radius' if k == 'radius' else k): v for k, v in spectrum.known_parameters.items()}
    source = {k: v for k, v in spectrum.source.items() if k not in ('file', 'format')}
    source.setdefault('software', 'OpenDEP Compute')
    raw = {k: v for k, v in spectrum.raw.items() if k != 'normalisation'}
    return {
        'format': SCATTER_FORMAT, 'format_version': SCATTER_VERSION,
        'name': spectrum.name, 'color': spectrum.color, 'point_size': 50.0, 'point_style': 'o', 'visibility': True,
        'scatter': {'frequencies': floats(spectrum.frequencies), 'recm_values': floats(spectrum.values),
                    'recm_errors': floats(spectrum.errors)},
        'quantity': spectrum.quantity, 'label': spectrum.label, 'scale': spectrum.scale,
        'normalisation': spectrum.raw.get('normalisation', {'method': 'none', 'factor': None}),
        'raw': raw, 'points': points, 'known_parameters': known, 'source': source,
        'created': datetime.now().isoformat(timespec='seconds'), 'exported_by': f'OpenDEP Compute {__version__}',
        'widget': None,
    }


def write_scatter(spectrum: Spectrum, path: str | Path) -> Path:
    """
    Write a spectrum as an OpenDEP Spectrum (.odspec) file.

    Args:
        spectrum (Spectrum): Spectrum.
        path (str | Path): Target file.

    Returns:
        Path: The file written.
    """
    path = Path(path)
    path.write_text(json.dumps(scatter_document(spectrum), indent=1, ensure_ascii=False), encoding='utf-8')
    return path


## Curve ##


def _view_values(model_key: str, p: dict, radius_convention: str | None = None) -> tuple[dict, list[str]]:
    """
    Catalog values of a View curve's parameters.

    Args:
        model_key (str): Catalog key of View's model.
        p (dict): View parameters.
        radius_convention (str | None): The file's "radius_convention" ("outer" from OpenDEP View 2; None before).

    Returns:
        tuple[dict, list[str]]: (values in display units, warnings).
    """
    medium = {'medium_eps_r': float(p['buffer_perm']), 'medium_sigma': float(p['buffer_cond'])}
    if model_key == 'homogeneous':
        return {**medium, 'radius': float(p['core_radius']), 'eps_p': float(p['core_perm']),
                'sigma_p': float(p['core_cond']), 'k_s': float(p.get('core_surface_cond', 0.0))}, []
    values = {**medium, 'radius': float(p['core_radius']),
              'eps_cyto': float(p['core_perm']), 'sigma_cyto': float(p['core_cond']),
              'd_mem': float(p['1st_shell_thick']), 'eps_mem': float(p['1st_shell_perm']),
              'sigma_mem': float(p['1st_shell_cond'])}
    warnings = []
    if model_key in ('two_shell', 'four_shell'):
        values.update(d_wall=float(p['2nd_shell_thick']), eps_wall=float(p['2nd_shell_perm']),
                      sigma_wall=float(p['2nd_shell_cond']))
    if model_key in ('three_shell', 'four_shell'):
        values.update(r_nuc=float(p['nucleus_radius']), d_env=float(p['envelope_thick']),
                      eps_env=float(p['envelope_perm']), sigma_env=float(p['envelope_cond']),
                      eps_np=float(p['nucleoplasm_perm']), sigma_np=float(p['nucleoplasm_cond']))
    if model_key == 'two_shell' and radius_convention != RADIUS_OUTER:
        # View 1.x two-shell: core radius, then the inner and the outer shell outside it
        values['radius'] += (values['d_mem'] + values['d_wall']) / 1000.0
        warnings = ['⚠️ View two-shell curve: OpenDEP View 1.x computes this model with an incorrect formula '
                    '(see the user guide, Dielectric models); it is recomputed here with the correct one, so the '
                    'curve differs from the one shown in View 1.x',
                    'ℹ️ View 1.x two-shell radius is the core radius; converted to the outer radius '
                    f'{values["radius"]:.4g} µm (both shells included)']
    return values, warnings


def read_curve(path: str | Path, data: dict | None = None) -> ImportResult:
    """
    Read an OpenDEP Curve (.odcurve, or .odc) file from OpenDEP View or OpenDEP Compute.

    Args:
        path (str | Path): File.
        data (dict | None): Already parsed JSON.

    Returns:
        ImportResult: One model curve.
    """
    path = Path(path)
    data = data if data is not None else json.loads(path.read_text(encoding='utf-8'))
    name = data.get('name') or path.stem
    own = data.get(CURVE_BLOCK)
    if own:
        result = ImportResult(str(path), 'OpenDEP Curve (OpenDEP Compute)')
        model = MODELS[own['model']]
        values = {**model.defaults(), **{k: float(v) for k, v in own['values'].items()}}
        result.curves.append(ModelCurve(name, model.key, values, {'file': str(path), **own.get('source', {})},
                                        color=data.get('color') or '#DC2626'))
        return result
    result = ImportResult(str(path), 'OpenDEP Curve (OpenDEP View)')
    model_key = VIEW_MODELS.get(int(data.get('model', 1)))
    if model_key is None:
        raise ValueError(f'⚠️ {path.name}: unknown View model {data.get("model")}')
    values, warnings = _view_values(model_key, data['parameters'], data.get('radius_convention'))
    result.curves.append(ModelCurve(name, model_key, values, {'file': str(path), 'software': 'OpenDEP View'},
                                    warnings, data.get('color') or '#DC2626'))
    result.warnings.extend(warnings)
    return result


def curve_document(curve: ModelCurve, frequencies: np.ndarray | None = None) -> dict:
    """
    OpenDEP Curve document of a model curve.

    The View fields are filled (all five catalog models, outer radius, "radius_convention": "outer") so OpenDEP
    View 2 shows the curve; the "opendep_compute" block keeps the exact model and values for OpenDEP Compute.

    Args:
        curve (ModelCurve): Model curve.
        frequencies (np.ndarray | None): Sample frequencies for "curves" (default 1 kHz - 100 MHz, 200 points).

    Returns:
        dict: JSON document.

    Raises:
        ValueError: OpenDEP View cannot show the model.
    """
    model = MODELS[curve.model]
    v = {**model.defaults(), **curve.values}
    view_index = {key: index for index, key in VIEW_MODELS.items()}.get(curve.model)
    if view_index is None:
        raise ValueError(f'⚠️ OpenDEP View cannot show the model "{model.name}": save the curve as an '
                         'OpenDEP Compute project instead')
    f = np.logspace(3, 8, 200) if frequencies is None else np.asarray(frequencies, float)
    k = cm_factor(model, f, v)

    # 1. View parameters: the model's own values, View's defaults for the layers it does not have
    parameters = {'buffer_perm': v.get('medium_eps_r', 78.0), 'buffer_cond': v.get('medium_sigma', 0.01),
                  'core_radius': v['radius'], 'electric_field': 1.0,
                  '1st_shell_perm': 40.0, '1st_shell_cond': 1e-5, '1st_shell_thick': 6.0,
                  '2nd_shell_perm': 10.0, '2nd_shell_cond': 1e-5, '2nd_shell_thick': 6.0,
                  'core_surface_cond': 0.0, 'nucleus_radius': 3.0, 'envelope_thick': 40.0, 'envelope_perm': 30.0,
                  'envelope_cond': 1e-3, 'nucleoplasm_perm': 50.0, 'nucleoplasm_cond': 1.0,
                  '1st_cross_over': {key: 0.0 for key in VIEW_CROSSOVER_KEYS},
                  '2nd_cross_over': {key: 0.0 for key in VIEW_CROSSOVER_KEYS}}
    if curve.model == 'homogeneous':
        parameters.update(core_perm=v['eps_p'], core_cond=v['sigma_p'], core_surface_cond=v['k_s'])
    else:
        parameters.update(core_perm=v['eps_cyto'], core_cond=v['sigma_cyto'], **{
            '1st_shell_perm': v['eps_mem'], '1st_shell_cond': v['sigma_mem'], '1st_shell_thick': v['d_mem']})
    if curve.model in ('two_shell', 'four_shell'):
        parameters.update({'2nd_shell_perm': v['eps_wall'], '2nd_shell_cond': v['sigma_wall'],
                           '2nd_shell_thick': v['d_wall']})
    if curve.model in ('three_shell', 'four_shell'):
        parameters.update(nucleus_radius=v['r_nuc'], envelope_thick=v['d_env'], envelope_perm=v['eps_env'],
                          envelope_cond=v['sigma_env'], nucleoplasm_perm=v['eps_np'], nucleoplasm_cond=v['sigma_np'])

    # 2. Sampled curve of the model (View recomputes all of them when it opens the file)
    curves = {'frequencies': [float(x) for x in f]}
    for model_key, name in VIEW_CURVE_KEYS.items():
        own_model = model_key == curve.model
        curves[f'recm_{name}'] = [float(x) for x in k.real] if own_model else [0.0] * len(f)
        curves[f'imcm_{name}'] = [float(x) for x in k.imag] if own_model else [0.0] * len(f)
        curves[f'depforce_{name}'] = [0.0] * len(f)
    return {'format': CURVE_FORMAT, 'format_version': CURVE_VERSION,
            'name': curve.name, 'color': curve.color, 'line_style': '-', 'line_width': 1.5, 'visibility': True,
            'model': view_index, 'parameters': parameters, 'curves': curves, 'widget': None,
            'radius_convention': RADIUS_OUTER,
            CURVE_BLOCK: {'model': curve.model, 'values': {k: float(x) for k, x in v.items()},
                          'source': curve.source, 'exported_by': f'OpenDEP Compute {__version__}'}}


def write_curve(curve: ModelCurve, path: str | Path, frequencies: np.ndarray | None = None) -> Path:
    """
    Write a model curve as an OpenDEP Curve (.odcurve) file.

    Args:
        curve (ModelCurve): Curve.
        path (str | Path): Target file.
        frequencies (np.ndarray | None): Sample frequencies.

    Returns:
        Path: The file written.
    """
    path = Path(path)
    path.write_text(json.dumps(curve_document(curve, frequencies), indent=1, ensure_ascii=False), encoding='utf-8')
    return path
