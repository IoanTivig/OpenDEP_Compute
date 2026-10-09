"""
Publication figures and fit reports (matplotlib, Qt-free).

A figure is the fitted spectrum at a journal size (one or two columns), with 8 pt Arial-like text, in PNG / TIFF
(600 dpi), SVG or PDF (text kept as text). A report is a two-page A4 PDF: the figure and the main results
(crossovers, R²), then every parameter with its standard error, the fit settings, the data sources, the warnings
and the references of the model, so that a fit can be checked and cited later.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import math

import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from src import __version__
from src.data.spectrum import Spectrum
from src.models.catalog import MODELS, full_label, grouped_parameters
from src.report.plotting import draw_fit, fit_crossovers, frequency_text

MM = 1 / 25.4
# Journal figure sizes (width, height) in mm: Elsevier / ACS / RSC column widths
FIGURE_SIZES = {'single': ('One column (85 mm)', 85, 75), 'one_half': ('One and a half columns (120 mm)', 120, 95),
                'double': ('Two columns (175 mm)', 175, 115)}
FIGURE_FORMATS = {'.png': 'PNG (600 dpi)', '.tif': 'TIFF (600 dpi)', '.svg': 'SVG (vector)', '.pdf': 'PDF (vector)'}
DPI = 600
PUBLICATION_RC = {'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
                  'svg.fonttype': 'none', 'pdf.fonttype': 42, 'axes.linewidth': 0.8}
SOFTWARE_REFERENCE = ('Tivig I, Moisescu MG, Savopol T. OpenDEP: an open-source platform for dielectrophoresis '
                      'spectra acquisition and analysis. ACS Omega 8 (2023) 38715-38722. doi:10.1021/acsomega.3c06052')
_JONES = 'Jones TB. Electromechanics of Particles. Cambridge University Press (1995). doi:10.1017/CBO9780511574498'
_IRIMAJIRI = ('Irimajiri A, Hanai T, Inouye A. A dielectric theory of "multi-stratified shell" model with its '
              'application to a lymphoma cell. J Theor Biol 78 (1979) 251-269. doi:10.1016/0022-5193(79)90268-6')
_PETHIG = ('Pethig R. Dielectrophoresis: Theory, Methodology and Biological Applications. Wiley (2017). '
           'doi:10.1002/9781118671443')
_HUANG = ('Huang Y, Hölzel R, Pethig R, Wang XB. Differences in the AC electrodynamics of viable and non-viable '
          'yeast cells determined through combined dielectrophoresis and electrorotation studies. Phys Med Biol 37 '
          '(1992) 1499-1517. doi:10.1088/0031-9155/37/7/003')
_ERMOLINA = ('Ermolina I, Morgan H. The electrokinetic properties of latex particles: comparison of '
             'electrophoresis and dielectrophoresis. J Colloid Interface Sci 285 (2005) 419-428. '
             'doi:10.1016/j.jcis.2004.11.003')
_COTTET = ('Cottet J et al. MyDEP: a new computational tool for dielectric modeling of particles and cells. '
           'Biophys J 116 (2019) 12-18. doi:10.1016/j.bpj.2018.11.021 (models validated against MyDEP 1.0.1)')
MODEL_REFERENCES = {'homogeneous': [_JONES, _ERMOLINA], 'single_shell': [_IRIMAJIRI, _JONES, _PETHIG],
                    'two_shell': [_IRIMAJIRI, _JONES, _HUANG], 'three_shell': [_IRIMAJIRI, _JONES],
                    'four_shell': [_IRIMAJIRI, _JONES]}
SCALE_TEXT = {'auto': 'automatic', 'free': 'free', 'fixed': 'fixed at 1'}
WEIGHT_TEXT = {'errors': 'by the error bars', 'none': 'none'}


## Figures ##


def fit_figure(spectra: list[Spectrum], model: str, values: dict[str, float], scales: list[float],
               size: str = 'single', style: str = 'errorbars', residuals: bool = True, legend: bool = True) -> Figure:
    """
    A fitted spectrum at a journal size.

    Args:
        spectra (list[Spectrum]): The fitted spectra.
        model (str): Catalog model key.
        values (dict[str, float]): Fitted and fixed values (display units).
        scales (list[float]): Scale factor per spectrum.
        size (str): Key of FIGURE_SIZES.
        style (str): 'errorbars' or 'area'.
        residuals (bool): Residual panel below.
        legend (bool): Legend.
    """
    _, width, height = FIGURE_SIZES[size]
    with matplotlib.rc_context(PUBLICATION_RC):
        figure = Figure(figsize=(width * MM, height * MM), facecolor='white', layout='constrained')
        small = size == 'single'
        draw_fit(figure, spectra, model, values, scales, style, residuals, legend=legend,
                 fontsize=8 if small else 9, markersize=3.5 if small else 4.5)
    return figure


def save_figure(figure: Figure, path: str | Path) -> Path:
    """
    Save a figure: raster formats at 600 dpi, vector formats with their text as text.

    Raises:
        ValueError: Unknown file type.
    """
    path = Path(path)
    if path.suffix.lower() not in FIGURE_FORMATS and path.suffix.lower() != '.tiff':
        raise ValueError(f'⚠️ {path.suffix} is not a figure format ({", ".join(FIGURE_FORMATS)})')
    with matplotlib.rc_context(PUBLICATION_RC):
        figure.savefig(path, dpi=DPI, facecolor='white')
    return path


## Reports ##


@dataclass
class FitReport:
    """
    Everything a report shows: a saved fit (FitRecord) or the fit on the Fit page.
    """
    name: str
    spectra: list[Spectrum]
    settings: dict                                     # FitSettings fields
    summary: dict                                      # fit_summary() output
    project: str = ''
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec='seconds'))


def value_text(value: float, error: float | None = None) -> str:
    """'12.3 ± 0.4' with the value rounded to the error's second significant digit."""
    if value is None or not math.isfinite(value):
        return '-'
    if error is None or not math.isfinite(error) or error <= 0:
        return f'{value:.4g}'
    digits = max(0, 1 - int(math.floor(math.log10(error))))
    if abs(value) >= 1e5 or abs(value) < 1e-3:
        return f'{value:.3g} ± {error:.2g}'
    return f'{value:.{digits}f} ± {error:.2g}'


def parameter_rows(summary: dict) -> list[tuple[str, str, str, str, str]]:
    """(group, parameter, value ± SE, unit, note) for every parameter, grouped like the Fit page."""
    rows = []
    for group, params in grouped_parameters(summary['model']):
        for d in params:
            p = summary['parameters'].get(d.key)
            if p is None:
                continue
            note = 'fixed' if not p['free'] else ('not determined' if not p['determined'] else
                                                  ('at bound' if p['at_bound'] else 'fitted'))
            rows.append((group, f'{d.label} ({d.symbol})', value_text(p['value'], p['stderr'] if p['free'] else None),
                         d.unit, note))
    return rows


def _text_block(figure: Figure, y: float, lines: list[tuple[str, str]], size: float = 9) -> float:
    """Lines of (style, text) from height y down; returns the next free height. Styles: h, b, t (text), s (small)."""
    for style, text in lines:
        fs = {'h': 12, 'b': size, 't': size, 's': size - 1.5}[style]
        weight = 'bold' if style in ('h', 'b') else 'normal'
        figure.text(0.08, y, text, fontsize=fs, weight=weight, va='top', wrap=True)
        y -= (fs + 5) / 72 / figure.get_figheight() * (1 + text.count('\n'))
    return y


def _wrap(text: str, width: int = 105) -> str:
    import textwrap
    return '\n'.join(textwrap.wrap(text, width, subsequent_indent='    '))


def write_fit_report(report: FitReport, path: str | Path, style: str = 'errorbars') -> Path:
    """
    Two-page A4 PDF of a fit.

    Args:
        report (FitReport): The fit.
        path (str | Path): Target .pdf.
        style (str): Point style of the figure.
    """
    path = Path(path)
    s, st = report.summary, report.summary['statistics']
    model = MODELS[s['model']]
    first, second = fit_crossovers(s['model'], s['values'])
    a4 = (210 * MM, 297 * MM)
    with matplotlib.rc_context(PUBLICATION_RC), PdfPages(path) as pdf:
        # Page 1: what was fitted, the figure, the main results
        page = Figure(figsize=a4, facecolor='white')
        y = _text_block(page, 0.95, [
            ('h', report.name),
            ('s', f'OpenDEP Compute {__version__}  ·  {report.created.replace("T", " ")}'
                  + (f'  ·  project {report.project}' if report.project else '')),
        ])
        fig_area = page.add_subfigure(page.add_gridspec(100, 1)[9:60, 0])
        fig_area.set_facecolor('white')
        draw_fit(fig_area, report.spectra, s['model'], s['values'], s['scales'], style, True, fontsize=9,
                 markersize=4.5)
        fig_area.subplots_adjust(left=0.1, right=0.95, top=0.97, bottom=0.1)
        n_params = sum(1 for p in s['parameters'].values() if p['free'])
        n_scales = st['n_free'] - n_params
        results = [('b', 'Results'),
                   ('t', f'First crossover (nDEP → pDEP): {frequency_text(first)}'),
                   ('t', f'Second crossover (pDEP → nDEP): {frequency_text(second)}'),
                   ('t', f'R²: {st["r_squared"]:.4f}   ({st["n_points"]} points; {n_params} fitted parameters'
                         f'{f" and {n_scales} scale factor" + ("s" if n_scales > 1 else "") if n_scales else ""})'),
                   ('b', 'Model'),
                   ('t', _wrap(f'{model.name}: {model.description}'))]
        free = [k for k, p in s['parameters'].items() if p['free']]
        results.append(('t', _wrap('Fitted: ' + ', '.join(
            full_label(d) for _, ps in grouped_parameters(s['model']) for d in ps if d.key in free))))
        _text_block(page, 0.37, results)
        pdf.savefig(page)

        # Page 2: parameters, settings, data, warnings, references
        page = Figure(figsize=a4, facecolor='white')
        y = _text_block(page, 0.95, [('h', 'Parameters')])
        rows = parameter_rows(s)
        table_h = 0.0175 * (len(rows) + 1)
        ax = page.add_axes([0.08, y - table_h - 0.01, 0.84, table_h])
        ax.axis('off')
        table = ax.table(cellText=[list(r) for r in rows], colLabels=['Group', 'Parameter', 'Value ± SE', 'Unit', 'Note'],
                         colWidths=[0.14, 0.38, 0.22, 0.1, 0.16], loc='upper left', cellLoc='left')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        for (r, _), cell in table.get_celld().items():
            cell.set_edgecolor('#CBD5E1')
            cell.set_linewidth(0.4)
            if r == 0:
                cell.set_text_props(weight='bold')
                cell.set_facecolor('#F1F5F9')
        y = y - table_h - 0.035
        scales = ', '.join(value_text(v, e) for v, e in zip(s['scales'], s['scale_errors']))
        lines = [('b', 'Fit settings'),
                 ('t', f'Scale factor: {SCALE_TEXT.get(report.settings.get("scale"), report.settings.get("scale"))}'
                       f' ({scales});  weighting: '
                       f'{WEIGHT_TEXT.get(report.settings.get("weighting"), report.settings.get("weighting"))}'
                       f'{" (applied)" if st["weighted"] else " (not applied)"}'),
                 ('t', f'Variable projection least squares, {report.settings.get("starts", 12)} extra starts '
                       f'(Latin hypercube); standard errors from the Jacobian.'),
                 ('b', 'Data')]
        for sp in report.spectra:
            src = sp.source.get('file', '')
            lines.append(('t', _wrap(f'{sp.name}: {int(sp.usable.sum())} of {len(sp)} points used'
                                     + (f'; {Path(src).name}' if src else ''))))
        if s.get('warnings'):
            lines.append(('b', 'Warnings'))
            lines += [('t', _wrap(w.replace('⚠️', '').strip())) for w in s['warnings']]
        lines.append(('b', 'References'))
        lines += [('s', _wrap(ref, 120)) for ref in MODEL_REFERENCES.get(s['model'], []) + [_COTTET, SOFTWARE_REFERENCE]]
        _text_block(page, y, lines)
        pdf.savefig(page)
    return path


def report_for_fit(project, record) -> FitReport:
    """
    The report of a saved fit (FitRecord) of a project.

    Raises:
        ValueError: None of the fit's spectra is still in the project.
    """
    spectra = [project.spectra[s].spectrum for s in record.spectra if s in project.spectra]
    if len(spectra) != len(record.spectra):
        raise ValueError(f'⚠️ Fit "{record.name}": some of its spectra were removed from the project')
    return FitReport(record.name, spectra, record.settings, record.result, project.name,
                     record.created)
