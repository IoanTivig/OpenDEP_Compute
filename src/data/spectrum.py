"""
Internal representation of measured spectra and model curves (Qt-free).

A Spectrum is one measured DEP spectrum: frequencies, values, errors and per-point flags. Whatever file it
came from (OpenDEP Control, OpenDEP View, Compute 1.x, 3DEP), it is held the same way, and nothing imported
is ever dropped: points are switched off or marked as outliers, never deleted.

`scale` says how the values relate to Re[K]:
    SCALE_ABSOLUTE   the values are Re[K] itself (e.g. a curve from View, a CM-factor file)
    SCALE_RELATIVE   the values are proportional to Re[K] with an unknown positive factor (grayness factor,
                     DEP rate, 3DEP intensity, Control's spectra normalised to the CM range): a fit needs a
                     free scale factor

A ModelCurve is a set of model parameters (from a View curve file, a Compute 1.x fit, a 3DEP fit, or the
parameter library), in catalog display units.
"""
from dataclasses import dataclass, field
from typing import Any

import numpy as np

SCALE_ABSOLUTE = 'absolute'
SCALE_RELATIVE = 'relative'

## Spectrum ##


@dataclass
class Spectrum:
    """
    One measured spectrum.
    """
    name: str
    frequencies: np.ndarray                       # Hz, as imported (not sorted)
    values: np.ndarray
    errors: np.ndarray                            # standard errors or deviations; 0 = unknown
    quantity: str = 're_k'                        # e.g. 're_k', 'dep_rate', 'grayness_factor', '3dep_intensity'
    label: str = 'Re[K]'
    unit: str = ''
    scale: str = SCALE_RELATIVE
    enabled: np.ndarray | None = None             # per point; False = left out of fits
    outlier: np.ndarray | None = None             # per point; marked as outlier (and normally disabled)
    points: dict[str, list] = field(default_factory=dict)          # extra per-point data (phase, class, ...)
    raw: dict[str, Any] = field(default_factory=dict)              # unscaled values / factor, when known
    known_parameters: dict[str, float] = field(default_factory=dict)   # catalog display units (radius, medium_sigma)
    source: dict[str, Any] = field(default_factory=dict)           # file, format, software, measurement, ...
    color: str = '#2563EB'

    def __post_init__(self) -> None:
        self.frequencies = np.asarray(self.frequencies, dtype=float)
        self.values = np.asarray(self.values, dtype=float)
        n = len(self.frequencies)
        self.errors = np.zeros(n) if self.errors is None else np.asarray(self.errors, dtype=float)
        self.enabled = np.ones(n, bool) if self.enabled is None else np.asarray(self.enabled, bool)
        self.outlier = np.zeros(n, bool) if self.outlier is None else np.asarray(self.outlier, bool)
        for name, arr in (('values', self.values), ('errors', self.errors), ('enabled', self.enabled),
                          ('outlier', self.outlier)):
            if len(arr) != n:
                raise ValueError(f'⚠️ "{self.name}": {name} has {len(arr)} entries for {n} frequencies')
        for key, values in self.points.items():
            if len(values) != n:
                raise ValueError(f'⚠️ "{self.name}": point data "{key}" has {len(values)} entries for {n} frequencies')

    def __len__(self) -> int:
        return len(self.frequencies)

    @property
    def usable(self) -> np.ndarray:
        """
        Points that enter a fit: enabled, not outliers, finite, positive frequency.

        Returns:
            np.ndarray: Boolean mask.
        """
        return (self.enabled & ~self.outlier & np.isfinite(self.values) & np.isfinite(self.frequencies)
                & (self.frequencies > 0))

    def sorted(self) -> 'Spectrum':
        """
        A copy sorted by frequency (point data follows).

        Returns:
            Spectrum: Sorted copy.
        """
        order = np.argsort(self.frequencies, kind='stable')
        return Spectrum(self.name, self.frequencies[order], self.values[order], self.errors[order], self.quantity,
                        self.label, self.unit, self.scale, self.enabled[order], self.outlier[order],
                        {k: [v[i] for i in order] for k, v in self.points.items()}, dict(self.raw),
                        dict(self.known_parameters), dict(self.source), self.color)


## Model curves ##


@dataclass
class ModelCurve:
    """
    A particle model with parameter values (not fitted here, or fitted elsewhere).
    """
    name: str
    model: str                                    # catalog key
    values: dict[str, float]                      # display units, particle and medium parameters
    source: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    color: str = '#DC2626'


## Import result ##


@dataclass
class ImportResult:
    """
    Everything read from one file.
    """
    path: str
    format: str                                   # e.g. 'OpenDEP Spectrum v2', '3DEP csv'
    spectra: list[Spectrum] = field(default_factory=list)
    curves: list[ModelCurve] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fits: list[dict] = field(default_factory=list)        # saved fits in the file (.odfit), see opendep_fit
