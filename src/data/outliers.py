"""
Model-free outlier suggestions for a spectrum (Qt-free).

A point is compared with what its neighbours predict, not with a fitted model: choosing outliers with the model
being tested would favour that model. A DEP spectrum is smooth in log-frequency, so each point is predicted by a
robust straight line (Theil-Sen: median of the pairwise slopes; Sen 1968) through its nearest used neighbours, the
point itself left out. Deviations are judged on a robust scale, MAD / 0.6745 of all deviations (Iglewicz and
Hoaglin 1993), so the outliers do not inflate the scale they are judged by. The worst point above the threshold is
suggested and left out as a neighbour, and the check is repeated: one strong outlier does not hide or create
another. The first and last points are not judged (their neighbours lie on one side only). Nothing is changed:
the user confirms.

References
    Sen PK. Estimates of the regression coefficient based on Kendall's tau. J Am Stat Assoc 63, 1379-1389 (1968).
    Iglewicz B, Hoaglin DC. How to Detect and Handle Outliers. ASQC Quality Press (1993).
"""
import numpy as np

from src.data.spectrum import Spectrum

NEIGHBOURS = 4                    # used neighbours that predict a point
THRESHOLD = 3.5                   # robust z-score above which a point is suggested (Iglewicz and Hoaglin)


def _deviations(x: np.ndarray, y: np.ndarray, use: np.ndarray, neighbours: int) -> np.ndarray:
    """Deviation of every point from the Theil-Sen line through its nearest used neighbours."""
    pool = np.nonzero(use)[0]
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        others = pool[pool != i]
        if len(others) < 2:
            continue
        near = others[np.argsort(np.abs(x[others] - x[i]), kind='stable')[:neighbours]]
        slopes = [(y[b] - y[a]) / (x[b] - x[a]) for k, a in enumerate(near) for b in near[k + 1:] if x[b] != x[a]]
        slope = float(np.median(slopes)) if slopes else 0.0
        out[i] = y[i] - (np.median(y[near] - slope * x[near]) + slope * x[i])
    return out


def suggest_outliers(spectrum: Spectrum, threshold: float = THRESHOLD,
                     neighbours: int = NEIGHBOURS) -> np.ndarray:
    """
    Points that deviate strongly from their neighbours: a suggestion, never applied automatically.

    Args:
        spectrum (Spectrum): Spectrum (switched-off points and marked outliers are not used as neighbours).
        threshold (float): Robust z-score above which a point is suggested.
        neighbours (int): Neighbours per prediction.

    Returns:
        np.ndarray: Boolean mask over all points.
    """
    mask = np.zeros(len(spectrum), bool)
    use = spectrum.usable.copy()
    if use.sum() < neighbours + 3:
        return mask
    x, y = np.log10(spectrum.frequencies), spectrum.values
    first = _deviations(x, y, use, neighbours)[use]
    scale = float(np.median(np.abs(first - np.median(first)))) / 0.6745
    if scale == 0:
        return mask
    interior = use & (x > x[use].min()) & (x < x[use].max())
    while use.sum() > neighbours + 2:
        d = _deviations(x, y, use, neighbours)
        z = np.where(interior & use, np.abs(d - np.median(d[use])) / scale, 0.0)
        worst = int(np.argmax(z))
        if z[worst] <= threshold:
            break
        mask[worst] = True
        use[worst] = False
    return mask
