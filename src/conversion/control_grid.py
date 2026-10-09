# Vendored from OpenDEP Control (src/utils/population_grid.py) by scripts/sync_control_grid.py - do not edit here.
# ------------------------------------------------------
# ---- OpenDEP Control - Population Grid Geometry ------
# ------------------------------------------------------

"""
Population-mode grid geometry, shared by the live readouts, the capture worker and
the classifier.

The grid handles are dragged over the live preview, which LiveViewWorker mirrors
horizontally (cv2.flip(frame, 1)). Every calculation, however, runs on the raw,
unmirrored camera frame (second_tick, saved images). A vertical line drawn at
preview position x therefore sits at raw position 1 - x. Horizontal lines are not
affected by a horizontal mirror. Single Cell mode applies the same mapping.
"""

from dataclasses import dataclass
from typing import Optional, Sequence

import cv2
import numpy as np

# At least this many grid lines are needed to span one full electrode period
# (edge -> opposite edge -> next edge = one electrode + one gap).
MIN_LINES_FOR_PERIOD: int = 3

# Whole-grid snap: scale range searched (lines placed with a slightly wrong spacing)
GRID_SCALE_RANGE: float = 0.10
# Whole-grid snap: the best rigid placement must beat the current one by this factor
GRID_MOVE_GAIN: float = 1.25
# Whole-grid snap: placements scoring this fraction of the best count as equally good;
# the one moving the lines least wins (a periodic pattern matches at several shifts)
GRID_TIE_FRACTION: float = 0.9


def raw_axis_positions(positions: Sequence[float], alignment: str) -> list[float]:
    """Convert normalized preview positions to normalized raw-frame positions.

    Args:
        positions: Normalized [0, 1] positions along the preview axis.
        alignment: "Vertical" (lines vertical, positions along x) or "Horizontal".

    Returns:
        Normalized positions in the unmirrored raw frame, sorted ascending.
    """
    if alignment == "Vertical":
        return sorted(1.0 - p for p in positions)
    return sorted(positions)


def raw_axis_pixels(positions: Sequence[float], alignment: str, axis_len: int) -> list[int]:
    """Convert normalized preview positions to raw-frame pixel indices.

    Args:
        positions: Normalized [0, 1] positions along the preview axis.
        alignment: "Vertical" or "Horizontal".
        axis_len: Frame width (vertical lines) or height (horizontal lines) in px.

    Returns:
        Pixel indices in the raw frame, sorted ascending.
    """
    return [int(p * (axis_len - 1)) for p in raw_axis_positions(positions, alignment)]


def intensity_profile(gray: np.ndarray, alignment: str) -> np.ndarray:
    """1D mean-intensity profile perpendicular to the grid lines.

    Args:
        gray: 2D grayscale frame (any scale).
        alignment: "Vertical" -> profile over columns; "Horizontal" -> over rows.

    Returns:
        1D float64 profile.
    """
    axis = 0 if alignment == "Vertical" else 1
    return gray.mean(axis=axis, dtype=np.float64)


def frame_profile(frame: np.ndarray, alignment: str) -> np.ndarray:
    """1D profile of a camera frame on a [0, 1] scale, channels weighted equally.

    Same values as intensity_profile(frame.mean(axis=2) / 255, alignment), but
    cv2.reduce avoids building a full-size float image, so it is cheap enough
    for several frames per second at full resolution on the Pi.

    Args:
        frame: Camera frame (HxWxC uint8, or HxW).
        alignment: "Vertical" -> profile over columns; "Horizontal" -> over rows.

    Returns:
        1D float64 profile.
    """
    axis = 0 if alignment == "Vertical" else 1
    reduced = cv2.reduce(np.ascontiguousarray(frame), axis, cv2.REDUCE_AVG, dtype=cv2.CV_64F)
    if frame.ndim == 3:
        reduced = reduced.reshape(-1, frame.shape[2]).mean(axis=1)
    return reduced.ravel() / 255.0


def edge_windows(edge_px: Sequence[int], edge_width: int, axis_len: int) -> list[tuple[int, int]]:
    """Sampling window [lo, hi) around each grid line.

    Args:
        edge_px: Grid-line pixel indices in raw-frame coordinates.
        edge_width: Half-width (px) sampled around each line.
        axis_len: Profile length.

    Returns:
        One (lo, hi) slice per line, clipped to the profile.
    """
    return [(max(0, px - edge_width), min(axis_len, px + edge_width + 1)) for px in edge_px]


def background_windows(edge_px: Sequence[int], electrode_px: Sequence[int], bkg_width: int,
                       bkg_region: str, axis_len: int) -> list[tuple[int, int]]:
    """Background window [lo, hi) at the midpoint of each selected inter-line region.

    A region counts as "electrode" when an electrode handle falls inside it.

    Args:
        edge_px: Grid-line pixel indices in raw-frame coordinates (sorted).
        electrode_px: Electrode-handle pixel indices in raw-frame coordinates.
        bkg_width: Width (px) of each window.
        bkg_region: "Gap & Electrode" | "Gap Only" | "Electrode Only".
        axis_len: Profile length.

    Returns:
        The non-empty windows; empty when no region qualifies.
    """
    windows: list[tuple[int, int]] = []
    for lo_edge, hi_edge in zip(edge_px[:-1], edge_px[1:]):
        has_electrode = any(lo_edge <= ep <= hi_edge for ep in electrode_px)
        include = (
            bkg_region == "Gap & Electrode"
            or (bkg_region == "Electrode Only" and has_electrode)
            or (bkg_region == "Gap Only" and not has_electrode)
        )
        if not include:
            continue
        center = (lo_edge + hi_edge) // 2
        half = bkg_width // 2
        lo, hi = max(0, center - half), min(axis_len, center + half)
        if hi > lo:
            windows.append((lo, hi))
    return windows


def windows_mean(profile: np.ndarray, windows: Sequence[tuple[int, int]]) -> float:
    """Mean of the per-window means (each window weighs the same); whole-profile
    mean when there is no window."""
    if not windows:
        return float(profile.mean())
    return float(np.mean([profile[lo:hi].mean() for lo, hi in windows]))


def edge_centre_signal(delta: np.ndarray, edge_win: Sequence[tuple[int, int]],
                       bkg_win: Sequence[tuple[int, int]], invert_sign: bool) -> tuple[float, float, float]:
    """Edge-versus-centre signal of a profile change.

    `delta` is the profile of a frame minus the profile of a reference frame, so
    the static electrode pattern cancels and only particle movement remains.
    pDEP darkens the edges and clears the centres; nDEP does the opposite.

    Args:
        delta: Profile change (frame - reference), [0, 1] intensity scale.
        edge_win: Windows at the grid lines (see edge_windows).
        bkg_win: Windows at the region centres (see background_windows).
        invert_sign: Negate so that darkening edges (cells darker than the
            medium) give a positive signal, as for the grayness factor.

    Returns:
        (edge_change, centre_change, signal) with signal = edge - centre,
        negated when invert_sign.
    """
    edge = windows_mean(delta, edge_win)
    centre = windows_mean(delta, bkg_win)
    signal = edge - centre
    return edge, centre, (-signal if invert_sign else signal)


def line_factor(delta: np.ndarray, edge_win: Sequence[tuple[int, int]],
                bkg_win: Sequence[tuple[int, int]], invert_sign: bool) -> tuple[float, float]:
    """Grayness factor of a profile change: each line minus the centre windows.

    The same arithmetic as grayness_factor, applied to `delta` (a frame's
    profile minus the reference frame's): (mean, std) across the lines.
    """
    centre = windows_mean(delta, bkg_win)
    per_line = np.array([delta[lo:hi].mean() for lo, hi in edge_win]) - centre
    mean = float(-per_line.mean() if invert_sign else per_line.mean())
    return mean, float(per_line.std())


def snap_edge_pixels(profile: np.ndarray, edge_px: Sequence[int], radius: int,
                     smooth_px: float = 2.0, min_contrast: float = 3.0) -> list[int]:
    """Move each grid line to the strongest intensity step within +/- radius px.

    Works best on the bare chip (electrodes without cells), where the steepest
    gradient is the electrode edge. A line stays where it is when its window
    holds no clear step (peak gradient below min_contrast x the median
    gradient of the profile) or when it would land on, or cross, a neighbour.

    Args:
        profile: 1D intensity profile (raw-frame coordinates).
        edge_px: Current line positions (raw-frame px), in any order.
        radius: Search half-width (px).
        smooth_px: Gaussian smoothing sigma (px) before the gradient.
        min_contrast: Required peak / median gradient ratio.

    Returns:
        New positions, in the same order as edge_px.
    """
    n = len(profile)
    if n < 3 or not edge_px:
        return list(edge_px)
    half = max(1, int(3 * smooth_px))
    x = np.arange(-half, half + 1)
    kernel = np.exp(-0.5 * (x / smooth_px) ** 2)
    smoothed = np.convolve(np.pad(profile, half, mode="edge"), kernel / kernel.sum(), mode="valid")
    grad = np.abs(np.gradient(smoothed))
    floor = min_contrast * float(np.median(grad))

    snapped = []
    for px in edge_px:
        lo, hi = max(0, px - radius), min(n, px + radius + 1)
        window = grad[lo:hi]
        if window.size and window.max() > floor:
            snapped.append(lo + int(np.argmax(window)))
        else:
            snapped.append(int(px))
    # Lines must keep their order and stay distinct; undo the ones that would not
    order = np.argsort(edge_px, kind="stable")
    result = list(snapped)
    for a, b in zip(order[:-1], order[1:]):
        if result[b] <= result[a]:
            result[a], result[b] = int(edge_px[a]), int(edge_px[b])
    return result


def _edge_strength(profile: np.ndarray, smooth_px: float) -> np.ndarray:
    """|gradient| of the profile after Gaussian smoothing."""
    half = max(1, int(3 * smooth_px))
    x = np.arange(-half, half + 1)
    kernel = np.exp(-0.5 * (x / smooth_px) ** 2)
    smoothed = np.convolve(np.pad(profile, half, mode="edge"), kernel / kernel.sum(), mode="valid")
    return np.abs(np.gradient(smoothed))


def align_grid_pixels(profile: np.ndarray, edge_px: Sequence[int], max_shift: int,
                      min_move: float = 0.0, smooth_px: float = 4.0,
                      min_contrast: float = 3.0) -> list[float]:
    """Move the whole grid (shift + uniform scale) onto the strongest edges.

    Lines placed by hand can sit far from their edges, beyond the local snap
    radius. The grid keeps its shape, so the best rigid placement is found by
    scoring the edge strength under all lines for every shift (+/- max_shift px)
    and scale (1 +/- GRID_SCALE_RANGE about the grid centre). The pattern is
    periodic, so several placements score alike: among those within
    GRID_TIE_FRACTION of the best, the one that moves the lines least wins.
    The grid is left as it is unless that placement scores GRID_MOVE_GAIN
    times better than the current one, when the lines would not sit on clear
    edges (mean strength below min_contrast x the median strength of the
    profile), or when it moves no line further than min_move (the local snap
    reaches those on its own).

    Args:
        profile: 1D intensity profile (raw-frame coordinates).
        edge_px: Current line positions (raw-frame px).
        max_shift: Largest shift searched (px).
        min_move: Placements moving every line by at most this are not applied (px).
        smooth_px: Smoothing before the gradient (broad: tolerant of a coarse search).
        min_contrast: Required mean edge strength under the lines / median strength.

    Returns:
        New positions (float px), in the same order as edge_px.
    """
    n = len(profile)
    lines = np.asarray(edge_px, dtype=float)
    if n < 3 or lines.size < 2:
        return [float(p) for p in lines]
    strength = _edge_strength(profile, smooth_px)
    axis = np.arange(n, dtype=float)
    centre = float(lines.mean())
    span = float(lines.max() - lines.min())
    # Scale step that moves the outermost line by ~1 px
    scale_step = 2.0 / span if span > 0 else 1.0
    scales = np.unique(np.concatenate([[1.0], np.arange(1.0 - GRID_SCALE_RANGE,
                                                       1.0 + GRID_SCALE_RANGE + 1e-12, scale_step)]))
    shifts = np.arange(-max_shift, max_shift + 1, dtype=float)
    # placed[scale, shift, line]
    placed = (centre + scales[:, None, None] * (lines - centre)[None, None, :]
              + shifts[None, :, None])
    inside = (placed >= 0) & (placed <= n - 1)
    score = np.where(inside, np.interp(placed, axis, strength), 0.0).sum(axis=2)
    current = float(np.interp(lines, axis, strength).sum())
    best = float(score.max())
    floor = min_contrast * float(np.median(strength)) * lines.size
    if best < GRID_MOVE_GAIN * current or best <= floor:
        return [float(p) for p in lines]
    moved = np.abs(placed - lines[None, None, :]).max(axis=2)
    candidates = score >= GRID_TIE_FRACTION * best
    i, j = np.unravel_index(np.argmin(np.where(candidates, moved, np.inf)), moved.shape)
    if moved[i, j] <= min_move:
        return [float(p) for p in lines]
    return [float(p) for p in placed[i, j]]


def snap_grid_positions(frame: np.ndarray, positions: Sequence[float],
                        alignment: str) -> tuple[list[float], int]:
    """Snap normalized grid positions (mirrored-preview coordinates) to the edges in a frame.

    First the whole grid is moved onto the edges when it sits clearly off them
    (align_grid_pixels: lines far from their edges, even beyond the local
    radius). Then each line snaps to the strongest step within a third of the
    smallest line spacing (3-50 px), so a line never jumps to the neighbouring edge.

    Args:
        frame: Raw (unmirrored) camera frame.
        positions: Normalized preview positions, as the grid bars hold them.
        alignment: "Vertical" or "Horizontal".

    Returns:
        (new positions in the same order, number of lines that moved).
    """
    if not positions:
        return list(positions), 0
    profile = frame_profile(frame, alignment)
    n = len(profile)
    vertical = alignment == "Vertical"
    # Preview -> raw px: vertical lines are mirrored (see module docstring)
    raw = [int(round(((1.0 - p) if vertical else p) * (n - 1))) for p in positions]
    gaps = np.diff(sorted(raw))
    spacing = int(gaps.min()) if gaps.size else n // 10
    radius = int(np.clip(spacing // 3, 3, 50))
    # Search a whole grid move of up to half the typical line spacing: further
    # than that, a different pairing of lines and edges would fit just as well
    max_shift = max(radius, int(np.median(gaps)) // 2) if gaps.size else radius
    aligned = [int(round(p)) for p in align_grid_pixels(profile, raw, max_shift, min_move=radius)]
    aligned = [min(max(p, 0), n - 1) for p in aligned]
    snapped = snap_edge_pixels(profile, aligned, radius)
    moved = sum(1 for a, b in zip(raw, snapped) if a != b)
    new = [((1.0 - px / (n - 1)) if vertical else px / (n - 1)) for px in snapped]
    # Unmoved lines keep their exact position (no rounding drift)
    return [p if a == b else q for p, q, a, b in zip(positions, new, raw, snapped)], moved


def grayness_factor(profile: np.ndarray,
                    edge_px: Sequence[int],
                    electrode_px: Sequence[int],
                    edge_width: int,
                    bkg_width: int,
                    bkg_region: str,
                    invert_sign: bool) -> tuple[float, float, float, float]:
    """Background-corrected grayness sampled at the grid lines.

    Background is the mean of small windows at the midpoints of the selected
    inter-line regions (bkg_separated=False strategy of OpenDEP Compute's
    convert_image_to_CM). A region counts as "electrode" when an electrode handle
    falls inside it.

    Args:
        profile: 1D intensity profile (see intensity_profile), normalized to [0, 1].
        edge_px: Grid-line pixel indices in raw-frame coordinates (sorted).
        electrode_px: Electrode-handle pixel indices in raw-frame coordinates.
        edge_width: Half-width (px) sampled around each grid line.
        bkg_width: Width (px) of each background window.
        bkg_region: "Gap & Electrode" | "Gap Only" | "Electrode Only".
        invert_sign: Negate the factor so dark lines (cells) give a positive value.

    Returns:
        (raw_grayness, bkg_grayness, factor_mean, factor_std).
    """
    axis_len = len(profile)

    # 1. Background: midpoints of the selected inter-line regions (falls back
    #    to the whole-profile mean when no eligible region exists)
    bkg_grayness = windows_mean(
        profile, background_windows(edge_px, electrode_px, bkg_width, bkg_region, axis_len))

    # 2. Raw grayness at each grid line (no subtraction)
    raw_samples = [float(profile[lo:hi].mean())
                   for lo, hi in edge_windows(edge_px, edge_width, axis_len)]
    raw_grayness = float(np.mean(raw_samples))

    # 3. Background-corrected factor across all lines
    norm_samples = np.array(raw_samples) - bkg_grayness
    factor_mean = float(-norm_samples.mean() if invert_sign else norm_samples.mean())
    factor_std = float(norm_samples.std())
    return raw_grayness, bkg_grayness, factor_mean, factor_std


@dataclass(frozen=True)
class ElectrodeGeometry:
    """Electrode period and stripe orientation derived from the grid lines."""

    period_px: Optional[float]   # one electrode + one gap, raw-frame px; None = not derivable
    angle_deg: float             # wave-vector angle as OpenDEP Neuralnet defines it (0 = vertical stripes)
    n_lines: int
    message: str                 # why the period is missing; "" when it is available

    @property
    def valid(self) -> bool:
        """True when a period is available."""
        return self.period_px is not None


def electrode_geometry(positions: Sequence[float], alignment: str,
                       frame_shape: tuple[int, ...]) -> ElectrodeGeometry:
    """Derive the electrode period and orientation from the grid lines.

    The lines are expected on consecutive electrode edges, so regions alternate
    electrode / gap and one period is the distance between line i and line i + 2.
    Real electrodes are never perfectly even (manufacturing), so the mean over all
    such spans is used; the pipeline then searches within +/- 10 % of it and
    refines the period on each frame. The horizontal mirror of the preview does not
    change distances, so it does not affect the period.

    Args:
        positions: Normalized grid-line positions (preview coordinates).
        alignment: "Vertical" or "Horizontal".
        frame_shape: Raw frame shape (height, width[, channels]).

    Returns:
        ElectrodeGeometry (period_px is None when fewer than 3 lines are set).
    """
    vertical = alignment == "Vertical"
    angle = 0.0 if vertical else 90.0
    n = len(positions)
    if n < MIN_LINES_FOR_PERIOD:
        return ElectrodeGeometry(None, angle, n,
                                 f"Place at least {MIN_LINES_FOR_PERIOD} grid lines on consecutive "
                                 f"electrode edges (now {n})")

    axis_len = frame_shape[1] if vertical else frame_shape[0]
    px = sorted(p * (axis_len - 1) for p in positions)
    period = float(np.mean([px[i + 2] - px[i] for i in range(n - 2)]))
    if period < 2.0:
        return ElectrodeGeometry(None, angle, n, "Grid lines overlap")
    return ElectrodeGeometry(period, angle, n, "")
