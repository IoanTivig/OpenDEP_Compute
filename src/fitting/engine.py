"""
Fitting DEP spectra with the particle models of the catalog (Qt-free).

The data y_i of a spectrum are compared with

    y(f) = s * Re[K(f; p)]

where p are the model parameters (some free, some fixed) and s a scale factor: s = 1 for absolute spectra
(the values are Re[K]); for relative spectra (grayness factor, DEP rate, 3DEP intensity, spectra scaled to the
CM range) s > 0 is free, because the measurement is proportional to Re[K] with an unknown factor. Several
spectra (replicates) can be fitted together: they share p and each has its own s.

Method
    1. Free parameters are searched inside their bounds, in log space for those spanning decades
       (conductivities). For fixed p the best s of each spectrum is linear and solved exactly (variable
       projection, Golub & Pereyra 1973), so the search runs over p only.
    2. Multi-start: the search is repeated from several starting points (the start values plus a Latin
       hypercube over the bounds) and the best result is kept, to avoid local minima.
    3. Polish: a final least-squares fit over p and s together gives the covariance matrix (J^T J)^-1, scaled
       by the reduced chi-square, hence standard errors and correlations. Parameters whose standard error
       exceeds their value, or that correlate above 0.95 with another, are reported as not determined.

Residuals are weighted by 1/error when every used point has a positive error (weighting "errors"),
otherwise unweighted. Points switched off or marked as outliers are left out.

References
    Golub G, Pereyra V. The differentiation of pseudo-inverses and nonlinear least squares problems whose
        variables separate. SIAM J Numer Anal 10 (1973) 413-432. doi:10.1137/0710036
    Press WH, Teukolsky SA, Vetterling WT, Flannery BP. Numerical Recipes, 3rd ed., ch. 15. Cambridge
        University Press (2007).
"""
from dataclasses import dataclass, field
import math

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import qmc

from src.data.spectrum import SCALE_ABSOLUTE, Spectrum
from src.models.catalog import MEDIUM_PARAMETERS, MODELS, Parameter, cm_factor

SCALE_AUTO = 'auto'               # free for relative spectra, 1 for absolute ones
SCALE_FREE = 'free'
SCALE_FIXED = 'fixed'
WEIGHT_ERRORS = 'errors'
WEIGHT_NONE = 'none'
UNDETERMINED_CORRELATION = 0.95

## Settings and results ##


@dataclass
class FitSettings:
    """
    What to fit.
    """
    model: str                                        # catalog key
    values: dict[str, float]                          # start / fixed values, display units (particle + medium)
    free: list[str]                                   # keys of the free parameters
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)   # overrides of the catalog ranges
    scale: str = SCALE_AUTO
    weighting: str = WEIGHT_ERRORS
    starts: int = 12                                  # multi-start points besides the start values
    seed: int = 1


@dataclass
class ParameterResult:
    key: str
    value: float                                      # display units
    stderr: float | None                              # display units; None = not available
    free: bool
    at_bound: bool = False
    determined: bool = True


@dataclass
class FitResult:
    """
    Outcome of a fit.
    """
    model: str
    parameters: dict[str, ParameterResult]
    values: dict[str, float]                          # all values (fitted and fixed), display units
    scales: list[float]                               # one per spectrum
    scale_errors: list[float | None]
    chi_square: float
    reduced_chi_square: float
    r_squared: float
    rmse: float
    aic: float
    bic: float
    n_points: int
    n_free: int
    weighted: bool
    correlation: dict[tuple[str, str], float]
    success: bool
    message: str
    warnings: list[str] = field(default_factory=list)
    starts_tried: int = 0


## Helpers ##


def all_parameters(model_key: str) -> dict[str, Parameter]:
    """
    Particle and medium parameters of a model.

    Args:
        model_key (str): Catalog key.

    Returns:
        dict[str, Parameter]: Key -> definition.
    """
    return {p.key: p for p in MODELS[model_key].parameters + MEDIUM_PARAMETERS}


def _data(spectra: list[Spectrum], weighting: str) -> tuple[list[tuple], bool]:
    """
    Used points of each spectrum and whether the fit is weighted.

    Returns:
        tuple: ([(frequencies, values, weights)], weighted).
    """
    used = [(s.frequencies[s.usable], s.values[s.usable], s.errors[s.usable]) for s in spectra]
    weighted = weighting == WEIGHT_ERRORS and all(len(e) and np.all(e > 0) for _, _, e in used)
    return [(f, y, 1.0 / e if weighted else np.ones_like(y)) for f, y, e in used], weighted


class _Problem:
    """
    Residual function over the free parameters (internal coordinates: log10 where log_scale).
    """

    def __init__(self, spectra: list[Spectrum], settings: FitSettings) -> None:
        self.model = MODELS[settings.model]
        self.defs = all_parameters(settings.model)
        unknown = [k for k in settings.free if k not in self.defs]
        if unknown:
            raise ValueError(f'⚠️ Unknown parameters for {self.model.name}: {unknown}')
        self.base = {**{k: p.default for k, p in self.defs.items()}, **settings.values}
        self.free = list(settings.free)
        self.log = [self.defs[k].log_scale and self._bound(k, settings)[0] > 0 for k in self.free]
        lo, hi = zip(*(self._bound(k, settings) for k in self.free)) if self.free else ((), ())
        self.lower = np.array([math.log10(a) if g else a for a, g in zip(lo, self.log)])
        self.upper = np.array([math.log10(b) if g else b for b, g in zip(hi, self.log)])
        self.data, self.weighted = _data(spectra, settings.weighting)
        self.scaled = [settings.scale == SCALE_FREE or
                       (settings.scale == SCALE_AUTO and s.scale != SCALE_ABSOLUTE) for s in spectra]

    def _bound(self, key: str, settings: FitSettings) -> tuple[float, float]:
        p = self.defs[key]
        return settings.bounds.get(key, (p.minimum, p.maximum))

    def to_internal(self, values: dict) -> np.ndarray:
        x = [math.log10(max(values[k], 1e-300)) if g else values[k] for k, g in zip(self.free, self.log)]
        return np.clip(np.array(x, float), self.lower, self.upper)

    def to_values(self, x: np.ndarray) -> dict[str, float]:
        out = dict(self.base)
        for k, g, v in zip(self.free, self.log, x):
            out[k] = 10.0 ** v if g else float(v)
        return out

    def model_curves(self, x: np.ndarray) -> list[np.ndarray]:
        values = self.to_values(x)
        return [cm_factor(self.model, f, values).real for f, _, _ in self.data]

    def best_scales(self, curves: list[np.ndarray]) -> list[float]:
        """Linear least-squares scale of each spectrum (positive), or 1 where the scale is fixed."""
        out = []
        for (f, y, w), k, scaled in zip(self.data, curves, self.scaled):
            if not scaled:
                out.append(1.0)
                continue
            den = float(np.sum((w * k) ** 2))
            out.append(max(float(np.sum(w * w * k * y)) / den, 1e-12) if den > 0 else 1.0)
        return out

    def residuals_projected(self, x: np.ndarray) -> np.ndarray:
        curves = self.model_curves(x)
        scales = self.best_scales(curves)
        return np.concatenate([w * (s * k - y) for (f, y, w), k, s in zip(self.data, curves, scales)])

    def residuals_full(self, z: np.ndarray) -> np.ndarray:
        n = len(self.free)
        curves = self.model_curves(z[:n])
        scales, i = [], n
        for scaled in self.scaled:
            if scaled:
                scales.append(z[i])
                i += 1
            else:
                scales.append(1.0)
        return np.concatenate([w * (s * k - y) for (f, y, w), k, s in zip(self.data, curves, scales)])


## Fitting ##


def fit_spectra(spectra: Spectrum | list[Spectrum], settings: FitSettings) -> FitResult:
    """
    Fit one spectrum, or several replicates together.

    Args:
        spectra (Spectrum | list[Spectrum]): Spectrum or replicates (shared model parameters, own scale each).
        settings (FitSettings): Model, start / fixed values, free parameters, options.

    Returns:
        FitResult: Values with standard errors, scales, fit statistics, warnings.

    Raises:
        ValueError: Unknown parameters, or fewer points than free parameters.
    """
    spectra = [spectra] if isinstance(spectra, Spectrum) else list(spectra)
    problem = _Problem(spectra, settings)
    n_points = sum(len(y) for _, y, _ in problem.data)
    n_scales = sum(problem.scaled)
    n_free = len(problem.free) + n_scales
    if n_points <= n_free:
        raise ValueError(f'⚠️ {n_points} points for {n_free} free parameters: switch some parameters to fixed')

    # 1. Multi-start search over the model parameters (scales solved exactly)
    starts = [problem.to_internal(problem.base)]
    if problem.free and settings.starts > 0:
        sample = qmc.LatinHypercube(d=len(problem.free), seed=settings.seed).random(settings.starts)
        starts += list(qmc.scale(sample, problem.lower, problem.upper))
    best = None
    for x0 in starts:
        if not problem.free:
            break
        try:
            r = least_squares(problem.residuals_projected, x0, bounds=(problem.lower, problem.upper),
                              x_scale='jac', max_nfev=400 * len(problem.free))
        except (ValueError, FloatingPointError):
            continue
        if best is None or r.cost < best.cost:
            best = r
    x = best.x if best is not None else np.array([])

    # 2. Polish over parameters and scales together (covariance)
    scales0 = [s for s, scaled in zip(problem.best_scales(problem.model_curves(x)), problem.scaled) if scaled]
    z0 = np.concatenate([x, scales0])
    lower = np.concatenate([problem.lower, np.full(n_scales, 1e-12)])
    upper = np.concatenate([problem.upper, np.full(n_scales, np.inf)])
    if n_free:
        final = least_squares(problem.residuals_full, np.clip(z0, lower, upper), bounds=(lower, upper),
                              x_scale='jac', max_nfev=2000)
        z, jac, residuals, success, message = final.x, final.jac, final.fun, final.success, final.message
    else:
        z, jac, residuals, success, message = z0, np.zeros((n_points, 0)), problem.residuals_full(z0), True, 'nothing free'
    return _result(problem, settings, z, jac, residuals, n_points, n_free, success, message, len(starts))


def _result(problem: _Problem, settings: FitSettings, z: np.ndarray, jac: np.ndarray, residuals: np.ndarray,
            n_points: int, n_free: int, success: bool, message: str, n_starts: int) -> FitResult:
    """
    Statistics, standard errors and warnings of a finished fit.
    """
    n_par = len(problem.free)
    values = problem.to_values(z[:n_par])
    chi2 = float(np.sum(residuals ** 2))
    dof = max(n_points - n_free, 1)
    red = chi2 / dof
    warnings = []

    # 1. Covariance (internal coordinates). Unweighted: scaled by the reduced chi-square (the scatter is the
    #    only error estimate). Weighted: scaled only when the scatter exceeds the error bars, never below them
    cov = None
    if n_free:
        try:
            cov = np.linalg.pinv(jac.T @ jac) * (max(red, 1.0) if problem.weighted else red)
        except np.linalg.LinAlgError:
            warnings.append('⚠️ Covariance not available (singular Jacobian)')
    errors_internal = np.sqrt(np.clip(np.diag(cov), 0, None)) if cov is not None else np.full(n_free, np.nan)

    # 2. Parameters in display units
    params = {}
    for i, (key, is_log) in enumerate(zip(problem.free, problem.log)):
        v = values[key]
        e = errors_internal[i]
        stderr = float(v * math.log(10) * e) if is_log else float(e)
        at_bound = bool(np.isclose(z[i], problem.lower[i], rtol=1e-6, atol=1e-9) or
                        np.isclose(z[i], problem.upper[i], rtol=1e-6, atol=1e-9))
        params[key] = ParameterResult(key, float(v), stderr if np.isfinite(stderr) else None, True, at_bound)
    for key, v in values.items():
        params.setdefault(key, ParameterResult(key, float(v), None, False))

    # 3. Correlations and determinability
    correlation = {}
    if cov is not None and n_par > 1:
        d = np.sqrt(np.clip(np.diag(cov)[:n_par], 1e-300, None))
        corr = cov[:n_par, :n_par] / np.outer(d, d)
        for i in range(n_par):
            for j in range(i + 1, n_par):
                correlation[(problem.free[i], problem.free[j])] = float(corr[i, j])
    for key, p in params.items():
        if not p.free:
            continue
        reasons = []
        if p.stderr is None or (p.value != 0 and p.stderr > abs(p.value)):
            reasons.append('standard error larger than the value')
        partners = [b if a == key else a for (a, b), c in correlation.items() if key in (a, b)
                    and abs(c) > UNDETERMINED_CORRELATION]
        if partners:
            reasons.append(f'correlated with {", ".join(partners)}')
        if reasons:
            p.determined = False
            warnings.append(f'⚠️ {key} is not determined by the data ({"; ".join(reasons)}): fix it, or fix a '
                            f'correlated parameter')
        if p.at_bound:
            warnings.append(f'⚠️ {key} ended at its bound: widen the range or fix it')

    # 4. Scales
    scales, scale_errors, i = [], [], n_par
    for scaled in problem.scaled:
        if scaled:
            scales.append(float(z[i]))
            scale_errors.append(float(errors_internal[i]) if np.isfinite(errors_internal[i]) else None)
            i += 1
        else:
            scales.append(1.0)
            scale_errors.append(None)

    # 5. Goodness of fit (on the weighted residuals; R² on the data scale)
    ys = np.concatenate([y for _, y, _ in problem.data])
    ws = np.concatenate([w for _, _, w in problem.data])
    ss_res = float(np.sum((residuals / ws) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    aic = n_points * math.log(max(chi2, 1e-300) / n_points) + 2 * n_free
    bic = n_points * math.log(max(chi2, 1e-300) / n_points) + n_free * math.log(n_points)
    if problem.weighted and red > 4:
        warnings.append(f'ℹ️ Reduced chi-square {red:.2g}: the scatter is larger than the error bars '
                        '(standard errors are scaled up accordingly)')
    return FitResult(settings.model, params, values, scales, scale_errors, chi2, red, r2,
                     math.sqrt(ss_res / n_points), aic, bic, n_points, n_free, problem.weighted, correlation,
                     bool(success), str(message), warnings, n_starts)


## Crossovers ##


def model_crossovers(model_key: str, values: dict[str, float], f_min: float = 1e2, f_max: float = 1e9,
                     points: int = 2000) -> list[tuple[float, str]]:
    """
    Frequencies where Re[K] of a model changes sign.

    Args:
        model_key (str): Catalog key.
        values (dict[str, float]): Parameter values (display units).
        f_min / f_max (float): Search range (Hz).
        points (int): Sampling density (log-spaced) before refinement.

    Returns:
        list[tuple[float, str]]: (frequency, 'rising' (nDEP -> pDEP) or 'falling'), ascending.
    """
    from scipy.optimize import brentq
    model = MODELS[model_key]
    f = np.logspace(math.log10(f_min), math.log10(f_max), points)
    k = cm_factor(model, f, values).real
    out = []
    for i in np.nonzero(np.sign(k[:-1]) * np.sign(k[1:]) < 0)[0]:
        g = lambda lf: float(cm_factor(model, np.array([10 ** lf]), values).real[0])
        root = brentq(g, math.log10(f[i]), math.log10(f[i + 1]), xtol=1e-10)
        out.append((10 ** root, 'rising' if k[i + 1] > k[i] else 'falling'))
    return out


def data_crossovers(spectrum: Spectrum) -> list[tuple[float, float, float, str]]:
    """
    Sign changes between neighbouring used points of a spectrum (straight line in log f between them).

    Args:
        spectrum (Spectrum): Spectrum.

    Returns:
        list[tuple[float, float, float, str]]: (estimate, lower point, upper point, 'rising' / 'falling').
    """
    s = spectrum.sorted()
    f, y = s.frequencies[s.usable], s.values[s.usable]
    out = []
    for i in range(len(f) - 1):
        if y[i] == 0 or y[i] * y[i + 1] < 0:
            frac = y[i] / (y[i] - y[i + 1]) if y[i] != y[i + 1] else 0.0
            est = 10 ** (math.log10(f[i]) + frac * (math.log10(f[i + 1]) - math.log10(f[i])))
            out.append((est, f[i], f[i + 1], 'rising' if y[i + 1] > y[i] else 'falling'))
    return out


## Saving ##


def fit_summary(result: FitResult, f_min: float = 1e2, f_max: float = 1e9) -> dict:
    """
    Plain-data summary of a fit (for projects, reports and exports).

    Args:
        result (FitResult): Fit.
        f_min / f_max (float): Crossover search range (Hz).

    Returns:
        dict: JSON-ready summary.
    """
    return {
        'model': result.model,
        'values': {k: float(v) for k, v in result.values.items()},
        'parameters': {k: {'value': p.value, 'stderr': p.stderr, 'free': p.free, 'at_bound': p.at_bound,
                           'determined': p.determined} for k, p in result.parameters.items()},
        'scales': result.scales, 'scale_errors': result.scale_errors,
        'statistics': {'chi_square': result.chi_square, 'reduced_chi_square': result.reduced_chi_square,
                       'r_squared': result.r_squared, 'rmse': result.rmse, 'aic': result.aic, 'bic': result.bic,
                       'n_points': result.n_points, 'n_free': result.n_free, 'weighted': result.weighted},
        'correlation': [[a, b, c] for (a, b), c in result.correlation.items()],
        'crossovers': [[f, d] for f, d in model_crossovers(result.model, result.values, f_min, f_max)],
        'warnings': result.warnings, 'success': result.success, 'message': result.message,
    }


def result_from_summary(summary: dict) -> FitResult:
    """
    The FitResult of a saved fit (inverse of fit_summary), to show it again without refitting.

    Args:
        summary (dict): fit_summary() output (a saved fit's result).

    Returns:
        FitResult: Same values, errors, scales and statistics (starts_tried is not kept: 0).
    """
    st = summary['statistics']
    parameters = {k: ParameterResult(k, p['value'], p['stderr'], p['free'], p.get('at_bound', False),
                                     p.get('determined', True)) for k, p in summary['parameters'].items()}
    scales = list(summary['scales'])
    return FitResult(
        model=summary['model'], parameters=parameters, values=dict(summary['values']), scales=scales,
        scale_errors=list(summary.get('scale_errors') or [None] * len(scales)),
        chi_square=st['chi_square'], reduced_chi_square=st['reduced_chi_square'], r_squared=st['r_squared'],
        rmse=st['rmse'], aic=st['aic'], bic=st['bic'], n_points=st['n_points'], n_free=st['n_free'],
        weighted=st['weighted'], correlation={(a, b): c for a, b, c in summary.get('correlation', [])},
        success=summary.get('success', True), message=summary.get('message', ''),
        warnings=list(summary.get('warnings', [])))
