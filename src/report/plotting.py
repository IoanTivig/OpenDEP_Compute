"""
Spectrum and fit plots (matplotlib, Qt-free): used by the pages, the publication figures and the reports.

Points are drawn as in OpenDEP View, with error bars or as a band (value ± error); a fitted spectrum is divided
by its scale factor so that data and model share the Re[K] axis. The zero line separates pDEP (above) from nDEP.
"""
import math

import numpy as np
from matplotlib.figure import Figure

from src.data.spectrum import Spectrum
from src.fitting.engine import model_crossovers
from src.models.catalog import MODELS, cm_factor

POINT_STYLES = ('errorbars', 'area')
ZERO_LINE = {'color': '#475569', 'linewidth': 1.1, 'zorder': 1.5}
CROSSOVER_RANGE = (1e2, 1e9)                 # Hz, where crossovers of the fitted curve are looked for
FIT_COLOR = '#0F172A'


def style_axes(ax) -> None:
    """Light axes style (slate grid, no top/right spines), as the application draws."""
    ax.spines[['top', 'right']].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color('#94A3B8')
    ax.tick_params(colors='#334155', labelsize=9)
    ax.grid(color='#E2E8F0', linewidth=0.8)
    ax.set_axisbelow(True)


def frequency_axis(ax) -> None:
    """Logarithmic frequency axis with a clearly visible zero line (above it pDEP, below it nDEP)."""
    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)')
    style_axes(ax)
    ax.axhline(0, **ZERO_LINE)


def dep_labels(ax, fontsize: float = 8) -> None:
    """"pDEP" above and "nDEP" below the zero line, at the left edge of a Re[K] axis."""
    style = {'transform': ax.get_yaxis_transform(), 'fontsize': fontsize, 'color': '#475569', 'ha': 'left'}
    ax.text(0.005, 0.0, '  pDEP ↑', va='bottom', **style)
    ax.text(0.005, 0.0, '  nDEP ↓', va='top', **style)


def draw_spectrum(ax, spectrum: Spectrum, scale: float = 1.0, color: str | None = None, label: str | None = None,
                  connect: bool = False, style: str = 'errorbars', markersize: float = 5) -> None:
    """
    Points of a spectrum divided by a scale factor: 'errorbars' (points with grey error bars) or 'area' (a band
    of value ± error). Switched-off points are hollow, outliers a red x.

    Args:
        ax: Matplotlib axes.
        spectrum (Spectrum): Spectrum.
        scale (float): The values are divided by it (fit scale factor: puts them on the Re[K] axis).
        color (str | None): Colour (default: the spectrum's).
        label (str | None): Legend label (default: the name).
        connect (bool): Join the used points with a thin line.
        style (str): 'errorbars' or 'area'.
        markersize (float): Marker size (pt).
    """
    color = color or spectrum.color
    s = spectrum.sorted()
    f, y, e = s.frequencies, s.values / scale, s.errors / scale
    used = s.usable
    off = ~s.enabled & ~s.outlier
    name = label if label is not None else spectrum.name
    if style == 'area' and used.sum() > 1:
        ax.fill_between(f[used], y[used] - e[used], y[used] + e[used], color=color, alpha=0.3, linewidth=0,
                        label=name)
        ax.plot(f[used], y[used], color=color, linewidth=1.0)
    else:
        if connect and used.sum() > 1:
            ax.plot(f[used], y[used], color=color, linewidth=0.8, alpha=0.6)
        ax.errorbar(f[used], y[used], yerr=np.where(e[used] > 0, e[used], np.nan), fmt='none', ecolor='grey',
                    elinewidth=0.6, capsize=2, zorder=1)
        ax.plot(f[used], y[used], 'o', color=color, markersize=markersize, label=name, zorder=2)
    if off.any():
        ax.plot(f[off], y[off], 'o', markerfacecolor='none', markeredgecolor=color, markersize=markersize,
                alpha=0.6)
    if s.outlier.any():
        ax.plot(f[s.outlier], y[s.outlier], 'x', color='#DC2626', markersize=markersize + 2)


def draw_residuals(ax, frequencies: np.ndarray, residuals: np.ndarray, errors: np.ndarray, color: str,
                   style: str = 'errorbars', markersize: float = 4) -> None:
    """
    Residuals with the data's errors, in the same point style as the data.

    Args:
        ax: Matplotlib axes.
        frequencies (np.ndarray): Frequencies of the used points (Hz).
        residuals (np.ndarray): Data / scale - model.
        errors (np.ndarray): Errors of the data / scale (0 = none).
        color (str): Colour.
        style (str): 'errorbars' or 'area'.
        markersize (float): Marker size (pt).
    """
    order = np.argsort(frequencies)
    f, r, e = frequencies[order], residuals[order], errors[order]
    if style == 'area' and len(f) > 1:
        ax.fill_between(f, r - e, r + e, color=color, alpha=0.3, linewidth=0)
        ax.plot(f, r, color=color, linewidth=1.0)
    else:
        ax.errorbar(f, r, yerr=np.where(e > 0, e, np.nan), fmt='none', ecolor='grey', elinewidth=0.6, capsize=2,
                    zorder=1)
        ax.plot(f, r, 'o', color=color, markersize=markersize, zorder=2)


def first_and_second(crossovers: list[tuple[float, str]]) -> tuple[float | None, float | None]:
    """First crossover (nDEP -> pDEP, rising) and second crossover (pDEP -> nDEP above it, falling)."""
    first = next((f for f, d in crossovers if d == 'rising'), None)
    second = next((f for f, d in crossovers if d == 'falling' and (first is None or f > first)), None)
    return first, second


def fit_crossovers(model: str, values: dict[str, float]) -> tuple[float | None, float | None]:
    """First and second crossover of a fitted curve (Hz), or None."""
    return first_and_second(model_crossovers(model, values, *CROSSOVER_RANGE))


def frequency_text(f: float | None) -> str:
    """'52.3 kHz' style."""
    if f is None:
        return '-'
    for unit, scale in (('MHz', 1e6), ('kHz', 1e3)):
        if f >= scale:
            return f'{f / scale:.3g} {unit}'
    return f'{f:.3g} Hz'


LEGEND_GAP = 0.04                                       # axes fraction between the legend and the highest point


def place_legend(ax, points: np.ndarray, fontsize: float) -> None:
    """
    Legend that never hides a data point.

    matplotlib's 'best' place only minimises the overlap: with a wide legend (long spectrum names) and data near
    the top, it covered points (a 3.1 MHz point of a HeLa spectrum vanished behind it). When it still covers a
    point or an error bar, the y axis is extended above the data and the legend goes into that free band.
    Long labels are wrapped to the figure's width (in an 85 mm figure a long name made the legend wider than the
    figure and the axes collapsed). Call it last, when the axes' layout is final: 'best' is re-evaluated at every
    draw, so the checked place is pinned.

    Args:
        ax: Re[K] axes.
        points (np.ndarray): (n, 2) data coordinates to keep clear (values and error-bar tops).
        fontsize (float): Legend text size (pt).
    """
    import textwrap
    figure = ax.get_figure(root=True)
    width = max(20, int(figure.get_figwidth() * 72 / (0.55 * fontsize)) - 12)   # characters per line
    handles, labels = ax.get_legend_handles_labels()
    labels = [textwrap.fill(label, width) for label in labels]
    style = dict(fontsize=fontsize, frameon=True, framealpha=0.85, edgecolor='none')
    leg = ax.legend(handles, labels, loc='best', **style)
    points = points[np.all(np.isfinite(points), axis=1)]
    if not len(points):
        return

    def covered(legend) -> tuple:
        """(legend box in axes fraction, whether it covers a point) after a full layout."""
        figure.draw_without_rendering()
        to_axes = ax.transAxes.inverted()
        box = legend.get_window_extent(figure._get_renderer()).transformed(to_axes)
        xy = to_axes.transform(ax.transData.transform(points))
        return box, bool(((xy[:, 0] >= box.x0) & (xy[:, 0] <= box.x1) &
                          (xy[:, 1] >= box.y0) & (xy[:, 1] <= box.y1)).any())

    # Each change (y range, legend place) can change the layout, so every step is checked again
    floating = True                                     # 'best' (re-evaluated at every draw) until pinned
    for _ in range(5):
        box, hit = covered(leg)
        if not hit:
            if not floating:
                return                                  # a fixed place, checked clear
            # 'best' found a clear place: pin it, so a later layout change does not move it onto the data
            leg = ax.legend(handles, labels, loc='lower left', bbox_to_anchor=(box.x0, box.y0),
                            borderaxespad=0, **style)
            floating = False
            continue
        y0, y1 = ax.get_ylim()
        room = 1 - box.height - LEGEND_GAP              # axes fraction left below the legend
        if room <= 0.3:
            return                                      # a legend taller than the plot: nothing better to do
        ax.set_ylim(y0, max(y1, y0 + (points[:, 1].max() - y0) / room))
        leg = ax.legend(handles, labels, loc='upper left', **style)
        floating = False


def draw_fit(figure: Figure, spectra: list[Spectrum], model: str, values: dict[str, float], scales: list[float],
             style: str = 'errorbars', residuals: bool = True, crossovers: bool = True, legend: bool = True,
             fontsize: float = 9, markersize: float = 5) -> tuple:
    """
    A fitted spectrum on a figure: data divided by their scale factors, the fitted Re[K], the crossovers (dashed)
    and, below, the residuals with the data's errors.

    Args:
        figure (Figure): Empty figure.
        spectra (list[Spectrum]): The fitted spectra (replicates), in fit order.
        model (str): Catalog model key.
        values (dict[str, float]): Fitted and fixed values (display units).
        scales (list[float]): Scale factor per spectrum.
        style (str): 'errorbars' or 'area'.
        residuals (bool): Residual panel below.
        crossovers (bool): Mark the first and second crossover.
        legend (bool): Legend.
        fontsize (float): Label size (pt).
        markersize (float): Marker size (pt).

    Returns:
        tuple: (Re[K] axes, residual axes or None).
    """
    if residuals:
        gs = figure.add_gridspec(2, 1, height_ratios=[3, 1])
        ax = figure.add_subplot(gs[0])
        res_ax = figure.add_subplot(gs[1], sharex=ax)
    else:
        ax, res_ax = figure.add_subplot(111), None
    for a in (ax, res_ax):
        if a is not None:
            frequency_axis(a)
            a.tick_params(labelsize=fontsize - 1)
            a.xaxis.label.set_size(fontsize)

    used_f = [s.frequencies[s.usable & (s.frequencies > 0)] for s in spectra]
    f_all = np.concatenate(used_f) if any(len(u) for u in used_f) else np.array([1e3, 1e8])
    f = np.logspace(math.log10(f_all.min() / 3), math.log10(f_all.max() * 3), 400)
    cat = MODELS[model]
    ax.plot(f, cm_factor(cat, f, values).real, color=FIT_COLOR, linewidth=1.6, label=f'{cat.name} fit', zorder=3)
    if crossovers:
        for x in fit_crossovers(model, values):
            if x is not None and f.min() <= x <= f.max():
                ax.axvline(x, color='#94A3B8', linestyle='--', linewidth=0.8)
    points = []                                         # (f, value) and (f, value + error) on the Re[K] scale
    for s, scale in zip(spectra, scales):
        label = f'{s.name} (÷ {scale:.3g})' if scale != 1 else s.name
        draw_spectrum(ax, s, scale, label=label, style=style, markersize=markersize)
        used = s.usable & (s.frequencies > 0)
        v, e = s.values[used] / scale, np.nan_to_num(s.errors[used] / scale)
        points += list(zip(s.frequencies[used], v)) + list(zip(s.frequencies[used], v + e))
        if res_ax is not None:
            used = s.usable
            res = s.values[used] / scale - cm_factor(cat, s.frequencies[used], values).real
            draw_residuals(res_ax, s.frequencies[used], res, s.errors[used] / scale, s.color, style,
                           markersize * 0.8)
    ax.set_ylabel('Re[K]', fontsize=fontsize)
    dep_labels(ax, fontsize - 1)
    if res_ax is not None:
        res_ax.set_ylabel('Residual', fontsize=fontsize)
        ax.tick_params(labelbottom=False)
        ax.set_xlabel('')
    if legend:                                          # last: needs the final layout
        place_legend(ax, np.array(points, dtype=float).reshape(-1, 2), fontsize - 1)
    return ax, res_ax
