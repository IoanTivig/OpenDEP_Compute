"""
Plot helpers shared by the pages: the drawing itself is Qt-free (src/report/plotting.py), shared with the
publication figures and reports; here only the point-style switch.
"""
from src.report.plotting import (ZERO_LINE, dep_labels, draw_fit, draw_residuals, draw_spectrum,  # noqa: F401
                                 frequency_axis)


def point_style_bar(ctx) -> 'SegmentedBar':
    """
    "Error bars | Area" switch bound to the shared point style.
    """
    from ui.widgets import SegmentedBar
    bar = SegmentedBar(['Error bars', 'Area'])
    bar.setToolTip('How the measured points are drawn (as in OpenDEP View)')
    bar.set_index(0 if ctx.point_style == 'errorbars' else 1)
    bar.changed.connect(lambda i: ctx.set_point_style(('errorbars', 'area')[i]))
    ctx.point_style_changed.connect(lambda: bar.set_index(0 if ctx.point_style == 'errorbars' else 1))
    return bar
