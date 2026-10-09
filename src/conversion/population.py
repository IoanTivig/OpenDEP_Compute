"""
Population image sets -> DEP spectra (Qt-free).

An image set is a folder with one image per frequency in `_DATA` (the end of the exposure) and, optionally, one
in `_BKG` (just before the field goes on), named `..._<frequency>Hz.<ext>` (OpenDEP Control, OpenDEP Compute 1.x).
The grayness factor is computed with exactly OpenDEP Control's arithmetic (src/conversion/control_grid.py, a
generated copy of Control's population_grid.py):

    profile          mean intensity along the electrode edges, on a 0-1 scale
    grayness factor  mean over the grid lines of (profile at the line - background), sign inverted for bright-field
                     (cells darker than the medium), with the spread over the lines as its error
    background       mean of small windows at the middle of the regions between the lines

With a `_BKG` image, a second spectrum uses the profile change (image - background image) instead of the
image itself, so the static electrode pattern cancels. It is not Control's "Grayness Factor (ref)": Control
averages the frames of the last second, of which only the final one is saved.

The grid (lines on consecutive electrode edges and a marker inside each electrode) comes from Control's
experiment_parameters.csv when the folder has one. Otherwise it is detected on an `Edges.*` image without cells
(OpenDEP Compute 1.x: the profile minus a polynomial trend changes sign at each edge), or suggested from the
profile averaged over all images (cells move between images, the edges stay). A detected grid is a suggestion to
check on the image, where lines are added or removed. Regions between consecutive lines alternate electrode /
gap; the darker set is taken as electrodes.
"""
from dataclasses import dataclass, field, replace
from pathlib import Path
import csv
import re

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

from src.conversion import control_grid as cg
from src.data.spectrum import SCALE_RELATIVE, ImportResult, Spectrum

IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')
FREQUENCY_RE = re.compile(r'_(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*Hz', re.IGNORECASE)
BKG_REGIONS = ('Gap & Electrode', 'Gap Only', 'Electrode Only')
ALIGNMENTS = ('Vertical', 'Horizontal')
GRID_CONTROL = 'OpenDEP Control experiment_parameters.csv'
GRID_DETECTED = 'detected'


## Images ##


def read_image(path: str | Path) -> np.ndarray:
    """
    Read an image (any path, also non-ASCII on Windows).

    Raises:
        ValueError: The file is not a readable image.
    """
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED) if data.size else None
    if image is None:
        raise ValueError(f'⚠️ {Path(path).name} is not a readable image')
    if image.dtype != np.uint8:                         # 16-bit TIFF -> 8-bit, the scale Control works on
        image = (image.astype(np.float64) / np.iinfo(image.dtype).max * 255).round().astype(np.uint8)
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    return image


def image_frequency(path: Path) -> float | None:
    """Frequency in a file name ('OpenDEP_123900Hz.jpg' -> 123900.0), or None."""
    m = FREQUENCY_RE.search(path.name)
    return float(m.group(1)) if m else None


def _images_by_frequency(folder: Path) -> dict[float, Path]:
    out = {}
    if folder.is_dir():
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() in IMAGE_SUFFIXES and (f := image_frequency(p)) is not None:
                out[f] = p
    return out


## Image sets ##


@dataclass
class ImageSet:
    """
    One experiment's images.
    """
    folder: Path
    data: dict[float, Path]                             # frequency in the file name -> image
    background: dict[float, Path] = field(default_factory=dict)
    edges_image: Path | None = None                     # 'Edges.*' (OpenDEP Compute 1.x)
    control_parameters: Path | None = None              # experiment_parameters.csv next to the images

    @property
    def name(self) -> str:
        return f'{self.folder.parent.name} - {self.folder.name}' if self.folder.parent.name else self.folder.name

    def preview_image(self) -> Path:
        """The image to show the grid on: Edges image, else the first background image, else the first image."""
        if self.edges_image is not None:
            return self.edges_image
        if self.background:
            return self.background[min(self.background)]
        return self.data[min(self.data)]


def open_image_set(folder: str | Path) -> ImageSet:
    """
    Read an experiment folder (with a `_DATA` subfolder).

    Raises:
        ValueError: No `_DATA` folder with frequency-named images.
    """
    folder = Path(folder)
    data = _images_by_frequency(folder / '_DATA')
    if not data:
        raise ValueError(f'⚠️ {folder.name}: no _DATA folder with images named ..._<frequency>Hz')
    edges = next((p for p in sorted(folder.iterdir()) if p.is_file() and p.stem.lower() == 'edges'
                  and p.suffix.lower() in IMAGE_SUFFIXES), None)
    params = folder / 'experiment_parameters.csv'
    return ImageSet(folder, data, _images_by_frequency(folder / '_BKG'), edges, params if params.is_file() else None)


def find_image_sets(folder: str | Path, depth: int = 3) -> list[ImageSet]:
    """
    The folder itself when it is an image set, otherwise every image set below it (up to `depth` levels).
    """
    folder = Path(folder)
    if (folder / '_DATA').is_dir():
        try:
            return [open_image_set(folder)]
        except ValueError:
            return []
    if depth == 0 or not folder.is_dir():
        return []
    found = []
    for sub in sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith(('_', '.'))):
        found += find_image_sets(sub, depth - 1)
    return found


## Grid ##


@dataclass
class GridSettings:
    """
    The population grid in OpenDEP Control's convention: positions normalised 0-1 along the axis perpendicular to
    the lines, as on Control's mirrored live preview (vertical lines: raw x = 1 - position). Detected grids are
    stored the same way, so that one calculation serves both.
    """
    grid_positions: list[float]
    electrode_positions: list[float]
    alignment: str = 'Vertical'
    edge_width: int = 1                                 # half-width (px) sampled around each line
    bkg_width: int = 5                                  # width (px) of each background window
    bkg_region: str = 'Gap & Electrode'
    invert_sign: bool = True                            # bright-field: dark cells give positive values
    source: str = GRID_DETECTED

    def edge_px(self, axis_len: int) -> list[int]:
        return cg.raw_axis_pixels(self.grid_positions, self.alignment, axis_len)

    def electrode_px(self, axis_len: int) -> list[int]:
        return cg.raw_axis_pixels(self.electrode_positions, self.alignment, axis_len)


def _to_positions(pixels: list[float], alignment: str, axis_len: int) -> list[float]:
    """Raw pixels -> Control's normalised preview positions (inverse of raw_axis_pixels)."""
    norm = [p / (axis_len - 1) for p in pixels]
    return sorted(1.0 - p for p in norm) if alignment == 'Vertical' else sorted(norm)


def control_parameters(path: str | Path) -> dict[str, str]:
    """Parameter / value pairs of a Control experiment_parameters.csv (first occurrence of each)."""
    params = {}
    for r in csv.reader(Path(path).read_text(encoding='utf-8-sig').splitlines()):
        if len(r) >= 2 and r[0] and not r[0].startswith('---'):
            params.setdefault(r[0], r[1])
    return params


def grid_from_control(path: str | Path) -> GridSettings:
    """
    The grid of a Control run.

    Raises:
        ValueError: The run has no population grid.
    """
    p = control_parameters(path)
    lines = [float(p[k]) for k in sorted((k for k in p if re.fullmatch(r'Grid Line \d+ Position \(norm\)', k)),
                                         key=lambda k: int(k.split()[2]))]
    electrodes = [float(p[k]) for k in sorted((k for k in p if re.fullmatch(r'Electrode \d+ Position \(norm\)', k)),
                                              key=lambda k: int(k.split()[1]))]
    if len(lines) < 2:
        raise ValueError(f'⚠️ {Path(path).parent.name}: the Control run has no population grid')
    return GridSettings(lines, electrodes, p.get('Grid Alignment', 'Vertical'), int(p.get('Edge Width (px)', 1)),
                        int(p.get('Background Width (px)', 5)), p.get('Background Region', 'Gap & Electrode'),
                        p.get('Invert Sign', 'True') == 'True', GRID_CONTROL)


def lines_to_grid(lines_px: list[float], axis_len: int, alignment: str = 'Vertical', first_is_electrode: bool = True,
                  source: str = GRID_DETECTED) -> GridSettings:
    """
    A grid from line positions on consecutive electrode edges: regions alternate electrode / gap, so a marker goes
    in the middle of every other region.

    Args:
        lines_px (list[float]): Line positions (raw-frame px).
        axis_len (int): Profile length (px).
        alignment (str): 'Vertical' or 'Horizontal'.
        first_is_electrode (bool): The region between the first two lines is an electrode.
        source (str): Where the lines come from.
    """
    lines = sorted(float(x) for x in lines_px)
    regions = list(zip(lines[:-1], lines[1:]))
    electrodes = [(a + b) / 2 for i, (a, b) in enumerate(regions) if (i % 2 == 0) == first_is_electrode]
    return GridSettings(_to_positions(lines, alignment, axis_len), _to_positions(electrodes, alignment, axis_len),
                        alignment, source=source)


def darker_first(profile: np.ndarray, lines_px: list[float]) -> bool:
    """True when the regions starting with the first one (1st, 3rd, ...) are darker on average: electrodes."""
    lines = sorted(int(x) for x in lines_px)
    means = [float(profile[a:b].mean()) for a, b in zip(lines[:-1], lines[1:]) if b > a]
    if len(means) < 2:
        return True
    return float(np.mean(means[0::2])) <= float(np.mean(means[1::2]))


def edges_image_lines(image: np.ndarray, alignment: str = 'Vertical', min_spacing: int = 25,
                      poly_degree: int = 7, trim: int = 0) -> list[int]:
    """
    Edges on a frame without cells ('Edges' image), as OpenDEP Compute 1.x found them: the profile minus a
    polynomial trend changes sign at each edge; a change closer than `min_spacing` px to the previous one, or to
    an end of the profile (where the trend wanders), is dropped. Each line then snaps to the strongest step nearby
    (Control's snap).

    Raises:
        ValueError: Fewer than two edges.
    """
    profile = cg.frame_profile(image, alignment)
    n = len(profile)
    x = np.arange(trim, n - trim, dtype=float)
    detrended = profile[trim:n - trim] - np.polyval(np.polyfit(x / n, profile[trim:n - trim], poly_degree), x / n)
    signs = np.sign(detrended)
    edges = []
    for i in range(len(signs) - 1):
        at = trim + i
        if (signs[i] != signs[i + 1] and signs[i + 1] != 0 and min_spacing <= at < n - min_spacing
                and (not edges or at - edges[-1] >= min_spacing)):
            edges.append(at)
    if len(edges) < 2:
        raise ValueError('⚠️ fewer than two electrode edges found in the Edges image')
    radius = int(np.clip(np.diff(edges).min() // 3, 3, 50))
    return sorted(cg.snap_edge_pixels(profile, edges, radius))


def average_profile(image_set: ImageSet, alignment: str = 'Vertical', max_images: int = 40) -> np.ndarray:
    """
    Mean profile over the images of a set. Cells sit elsewhere in every image and average out; the electrode edges
    stay. Background and data images are both used (up to `max_images`, spread over the set).
    """
    paths = list(image_set.background.values()) + list(image_set.data.values())
    if len(paths) > max_images:
        paths = [paths[int(i)] for i in np.linspace(0, len(paths) - 1, max_images)]
    profiles = [cg.frame_profile(read_image(p), alignment) for p in paths]
    n = min(len(p) for p in profiles)
    return np.mean([p[:n] for p in profiles], axis=0)


def suggest_lines(profile: np.ndarray, min_spacing: int = 25, sensitivity: float = 8.0) -> list[int]:
    """
    Suggested edge positions on an averaged profile: where the (lightly smoothed) profile changes fastest, which
    catches both a brightness step and the sharp bright / dark pair of a thin edge line. A suggestion to check on
    the image: cells stuck at the edges and uneven light also make steps.

    Args:
        profile (np.ndarray): Averaged profile (see average_profile).
        min_spacing (int): Smallest distance between lines (px).
        sensitivity (float): Peaks must stand this many median deviations above the typical slope.
    """
    n = len(profile)
    slope = np.abs(np.gradient(gaussian_filter1d(profile, 1.5)))
    mad = float(np.median(np.abs(slope - np.median(slope)))) or 1e-12
    peaks, _ = find_peaks(slope, distance=max(1, min_spacing), prominence=sensitivity * mad)
    return [int(p) for p in peaks if 10 < p < n - 10]


def snap_line(profile: np.ndarray, px: float, radius: int = 12) -> int:
    """A clicked position moved to the steepest step of the (averaged) profile within +/- radius px."""
    return cg.snap_edge_pixels(profile, [int(round(px))], radius, smooth_px=1.5, min_contrast=1.0)[0]


def detect_grid(image_set: ImageSet, alignment: str = 'Vertical', min_spacing: int = 25) -> GridSettings:
    """
    A grid for an image set without Control's: from its Edges image (Compute 1.x) when there is one, otherwise
    suggested from the averaged profile. Always check it on the image.

    Raises:
        ValueError: Fewer than two lines found.
    """
    if image_set.edges_image is not None:
        image = read_image(image_set.edges_image)
        lines = edges_image_lines(image, alignment, min_spacing)
        profile = cg.frame_profile(image, alignment)
        source = 'detected (Edges image)'
    else:
        profile = average_profile(image_set, alignment)
        lines = suggest_lines(profile, min_spacing)
        source = 'suggested (averaged images)'
    if len(lines) < 2:
        raise ValueError('⚠️ fewer than two electrode edges found: place the lines on the image')
    return lines_to_grid(lines, len(profile), alignment, darker_first(profile, lines), source)


def grid_for(image_set: ImageSet, alignment: str = 'Vertical') -> GridSettings:
    """Control's grid when the folder has one, otherwise a detected grid."""
    if image_set.control_parameters is not None:
        try:
            return grid_from_control(image_set.control_parameters)
        except (ValueError, KeyError):
            pass
    return detect_grid(image_set, alignment)


## Conversion ##


@dataclass
class ImageResult:
    """
    The numbers of one image.
    """
    frequency: float
    file: str
    raw: float                                          # grayness at the lines
    background: float                                   # grayness of the background windows
    factor: float
    factor_std: float
    factor_bkg: float | None = None                     # factor of (image - background image)
    factor_bkg_std: float | None = None


def measure(image: np.ndarray, grid: GridSettings, background: np.ndarray | None = None) -> dict:
    """
    Grayness factor of one image (Control's measure_grayness) and, with a background image, the factor of the
    profile change.
    """
    profile = cg.frame_profile(image, grid.alignment)
    n = len(profile)
    edge_px, elec_px = grid.edge_px(n), grid.electrode_px(n)
    raw, bkg, factor, std = cg.grayness_factor(profile, edge_px, elec_px, grid.edge_width, grid.bkg_width,
                                               grid.bkg_region, grid.invert_sign)
    out = {'raw': raw, 'background': bkg, 'factor': factor, 'factor_std': std}
    if background is not None:
        reference = cg.frame_profile(background, grid.alignment)
        if len(reference) == n:
            edge_win = cg.edge_windows(edge_px, grid.edge_width, n)
            bkg_win = cg.background_windows(edge_px, elec_px, grid.bkg_width, grid.bkg_region, n)
            out['factor_bkg'], out['factor_bkg_std'] = cg.line_factor(profile - reference, edge_win, bkg_win,
                                                                      grid.invert_sign)
    return out


def _exact_frequencies(image_set: ImageSet) -> list[float]:
    """Point frequencies of a Control run (file names carry them rounded)."""
    if image_set.control_parameters is None:
        return []
    rows = list(csv.reader(image_set.control_parameters.read_text(encoding='utf-8-sig').splitlines()))
    start = next((i for i, r in enumerate(rows) if r[:2] == ['Point', 'Frequency (Hz)']), None)
    out = []
    if start is not None:
        for r in rows[start + 1:]:
            if len(r) < 2 or not r[0].isdigit():
                break
            out.append(float(r[1]))
    return out


def convert(image_set: ImageSet, grid: GridSettings, progress=None) -> tuple[ImportResult, list[ImageResult]]:
    """
    Convert an image set into spectra.

    Args:
        image_set (ImageSet): The images.
        grid (GridSettings): Grid and sampling settings.
        progress (callable | None): Called with (done, total) after each image.

    Returns:
        tuple[ImportResult, list[ImageResult]]: The spectra (grayness factor; image - background when there are
        background images) and the numbers per image.
    """
    exact = _exact_frequencies(image_set)
    results, warnings = [], []
    freqs = sorted(image_set.data)
    for k, f in enumerate(freqs):
        path = image_set.data[f]
        try:
            image = read_image(path)
            bkg_path = image_set.background.get(f)
            m = measure(image, grid, read_image(bkg_path) if bkg_path is not None else None)
        except ValueError as e:
            warnings.append(str(e))
            continue
        # The file name carries the frequency rounded: use Control's exact value when one is within 1 %
        near = min(exact, key=lambda e: abs(np.log(e / f)), default=None)
        frequency = near if near is not None and abs(near / f - 1) < 0.01 else f
        results.append(ImageResult(frequency, path.name, m['raw'], m['background'], m['factor'], m['factor_std'],
                                   m.get('factor_bkg'), m.get('factor_bkg_std')))
        if progress is not None:
            progress(k + 1, len(freqs))

    result = ImportResult(str(image_set.folder), 'image set', warnings=warnings)
    if not results:
        return result, results
    source = {'software': 'OpenDEP Compute (image conversion)', 'format': 'image set',
              'file': str(image_set.folder), 'grid': grid.source,
              'settings': {'alignment': grid.alignment, 'edge_width': grid.edge_width, 'bkg_width': grid.bkg_width,
                           'bkg_region': grid.bkg_region, 'invert_sign': grid.invert_sign,
                           'grid_positions': grid.grid_positions, 'electrode_positions': grid.electrode_positions}}
    f = [r.frequency for r in results]
    points = {'file': [r.file for r in results], 'raw_grayness': [r.raw for r in results],
              'background_grayness': [r.background for r in results]}
    result.spectra.append(Spectrum(f'{image_set.name} - Grayness factor', f, [r.factor for r in results],
                                   [r.factor_std for r in results], 'grayness_factor', 'Grayness Factor', '',
                                   SCALE_RELATIVE, points=points, source=dict(source)))
    if all(r.factor_bkg is not None for r in results):
        result.spectra.append(Spectrum(f'{image_set.name} - Grayness factor (image - background)', f,
                                       [r.factor_bkg for r in results], [r.factor_bkg_std for r in results],
                                       'grayness_factor_bkg', 'Grayness Factor (image − background)', '',
                                       SCALE_RELATIVE, points=dict(points), source=dict(source)))
    elif image_set.background:
        warnings.append(f'⚠️ {image_set.name}: background images missing for some frequencies, '
                        f'image - background spectrum left out')
    return result, results


def with_settings(grid: GridSettings, **changes) -> GridSettings:
    """A copy of the grid with other sampling settings."""
    return replace(grid, **changes)
