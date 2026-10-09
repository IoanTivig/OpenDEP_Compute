"""
Catalog of particle models: parameters with display units, defaults and fitting ranges (Qt-free).

The GUI builds its parameter tables from this catalog, and the fitting engine its free / fixed
parameters. Values are handled in display units (µm, nm, mF/m², ...); `to_si` converts them.

Models (formulas and references in dielectric.py; validated against MyDEP 1.0.1):

    homogeneous          sphere, optional surface conductance (beads)
    single_shell         cytoplasm + membrane (mammalian cells)
    two_shell            cytoplasm + membrane + cell wall (yeast, bacteria, plant cells)
    three_shell          nucleus (nucleoplasm + envelope) + cytoplasm + membrane
    four_shell           three_shell + cell wall

Geometry follows MyDEP: `radius` is the outer radius of the whole particle (wall included) and the
nucleus radius includes the nuclear envelope.
"""
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from src.models.dielectric import (EPSILON_0, Material, Shell, clausius_mossotti, complex_permittivity,
                                   multishell_permittivity, shell_equivalent, surface_conductivity)

## Data classes ##


@dataclass(frozen=True)
class Parameter:
    """
    One model parameter.
    """
    key: str
    label: str
    symbol: str
    unit: str                         # display unit
    to_si: float                      # display value x to_si = SI value
    default: float
    minimum: float                    # fitting range (display units)
    maximum: float
    log_scale: bool = False           # fit in log space (conductivities, ...)
    description: str = ''
    group: str = ''                   # shown together in the GUI: Buffer, Cell, Membrane, ...


@dataclass(frozen=True)
class ParticleModel:
    """
    A particle model of the catalog.
    """
    key: str
    name: str
    description: str
    parameters: tuple[Parameter, ...]
    builder: Callable[[dict[str, float]], Callable[[np.ndarray, float], np.ndarray]] = field(repr=False)

    def defaults(self) -> dict[str, float]:
        """
        Default values in display units.

        Returns:
            dict[str, float]: Parameter key -> value.
        """
        return {p.key: p.default for p in self.parameters}

    def parameter(self, key: str) -> Parameter:
        return next(p for p in self.parameters if p.key == key)

    def permittivity(self, frequency_hz: np.ndarray, values: dict[str, float], eps0: float = EPSILON_0) -> np.ndarray:
        """
        Equivalent complex permittivity of the particle.

        Args:
            frequency_hz (np.ndarray): Frequencies (Hz).
            values (dict[str, float]): Parameter values in display units (missing keys take the default).
            eps0 (float): Vacuum permittivity (F/m).

        Returns:
            np.ndarray: Complex permittivity (F/m).
        """
        si = {p.key: values.get(p.key, p.default) * p.to_si for p in self.parameters}
        omega = 2 * np.pi * np.asarray(frequency_hz, dtype=float)
        return self.builder(si)(omega, eps0)


## Medium (the buffer the particles are suspended in) ##

MEDIUM_PARAMETERS = (
    Parameter('medium_eps_r', 'Buffer permittivity', 'ε_m', '', 1.0, 78.0, 1.0, 200.0,
              description='relative permittivity of the suspending buffer', group='Buffer'),
    Parameter('medium_sigma', 'Buffer conductivity', 'σ_m', 'S/m', 1.0, 0.01, 1e-5, 2.0, True,
              'conductivity of the suspending buffer', 'Buffer'),
)


def medium_material(values: dict[str, float]) -> Material:
    """
    Suspending medium from display values.

    Args:
        values (dict[str, float]): May contain medium_eps_r, medium_sigma.

    Returns:
        Material: Medium.
    """
    eps, sigma = MEDIUM_PARAMETERS
    return Material(values.get(eps.key, eps.default), values.get(sigma.key, sigma.default))


## Parameters shared by several models ##

RADIUS = Parameter('radius', 'Radius', 'r', 'µm', 1e-6, 6.0, 0.5, 50.0,
                   description='outer radius of the particle (cell wall included)', group='Other')
D_MEM = Parameter('d_mem', 'Membrane thickness', 'd_mem', 'nm', 1e-9, 7.0, 2.0, 20.0, group='Shell dimensions')
EPS_MEM = Parameter('eps_mem', 'Permittivity', 'ε_mem', '', 1.0, 10.0, 1.0, 40.0, group='Membrane')
SIGMA_MEM = Parameter('sigma_mem', 'Conductivity', 'σ_mem', 'S/m', 1.0, 1e-7, 1e-10, 1e-4, True, group='Membrane')
EPS_CYTO = Parameter('eps_cyto', 'Permittivity', 'ε_cyto', '', 1.0, 60.0, 20.0, 120.0, group='Cytoplasm')
SIGMA_CYTO = Parameter('sigma_cyto', 'Conductivity', 'σ_cyto', 'S/m', 1.0, 0.5, 0.01, 2.0, True, group='Cytoplasm')
D_WALL = Parameter('d_wall', 'Wall thickness', 'd_wall', 'nm', 1e-9, 100.0, 5.0, 1000.0, group='Shell dimensions')
EPS_WALL = Parameter('eps_wall', 'Permittivity', 'ε_wall', '', 1.0, 60.0, 5.0, 120.0, group='Cell wall')
SIGMA_WALL = Parameter('sigma_wall', 'Conductivity', 'σ_wall', 'S/m', 1.0, 0.01, 1e-5, 2.0, True, group='Cell wall')
R_NUC = Parameter('r_nuc', 'Nucleus radius', 'r_nuc', 'µm', 1e-6, 3.0, 0.3, 40.0,
                  description='outer radius of the nucleus (envelope included)', group='Other')
D_ENV = Parameter('d_env', 'Envelope thickness', 'd_env', 'nm', 1e-9, 40.0, 5.0, 100.0, group='Shell dimensions')
EPS_ENV = Parameter('eps_env', 'Permittivity', 'ε_env', '', 1.0, 30.0, 1.0, 120.0, group='Nuclear envelope')
SIGMA_ENV = Parameter('sigma_env', 'Conductivity', 'σ_env', 'S/m', 1.0, 1e-3, 1e-7, 1.0, True,
                      group='Nuclear envelope')
EPS_NP = Parameter('eps_np', 'Permittivity', 'ε_np', '', 1.0, 50.0, 20.0, 120.0, group='Nucleoplasm')
SIGMA_NP = Parameter('sigma_np', 'Conductivity', 'σ_np', 'S/m', 1.0, 1.0, 0.01, 3.0, True, group='Nucleoplasm')

# Groups and their order in the GUI and reports, as in OpenDEP View's curve panel: the buffer, the core (Particle
# for the homogeneous model, otherwise Cytoplasm), the radii (Other), every thickness (Shell dimensions), then the
# layers from the outside in
GROUPS = ('Buffer', 'Particle', 'Cytoplasm', 'Other', 'Shell dimensions', 'Membrane', 'Cell wall', 'Nuclear envelope',
          'Nucleoplasm')


## Builders: SI values -> eps(omega, eps0) ##


def _membrane(si: dict) -> Shell:
    return Shell(Material(si['eps_mem'], si['sigma_mem']), si['d_mem'])


def _wall(si: dict) -> Shell:
    return Shell(Material(si['eps_wall'], si['sigma_wall']), si['d_wall'])


def _homogeneous(si: dict):
    def eps(omega, eps0):
        sigma = surface_conductivity(si['sigma_p'], si['k_s'], si['radius'])
        return complex_permittivity(Material(si['eps_p'], sigma), omega, eps0)
    return eps


def _single_shell(si: dict):
    return lambda omega, eps0: multishell_permittivity(
        omega, si['radius'], Material(si['eps_cyto'], si['sigma_cyto']), [_membrane(si)], eps0)


def _two_shell(si: dict):
    return lambda omega, eps0: multishell_permittivity(
        omega, si['radius'], Material(si['eps_cyto'], si['sigma_cyto']), [_membrane(si), _wall(si)], eps0)


def _nucleated(si: dict, wall: bool):
    def eps(omega, eps0):
        # 1. Nucleus: nucleoplasm + envelope, as a sphere of radius r_nuc
        nucleus = multishell_permittivity(omega, si['r_nuc'], Material(si['eps_np'], si['sigma_np']),
                                          [Shell(Material(si['eps_env'], si['sigma_env']), si['d_env'])], eps0)
        # 2. Cytoplasm around it, then the membrane (and the wall)
        outer = [_membrane(si)] + ([_wall(si)] if wall else [])
        r_cyto = si['radius'] - sum(s.thickness for s in outer)
        eps_p = shell_equivalent(nucleus, complex_permittivity(Material(si['eps_cyto'], si['sigma_cyto']), omega, eps0),
                                 si['r_nuc'], r_cyto)
        r_in = r_cyto
        for shell in outer:
            eps_p = shell_equivalent(eps_p, complex_permittivity(shell.material, omega, eps0), r_in, r_in + shell.thickness)
            r_in += shell.thickness
        return eps_p
    return eps


## Catalog ##

MODELS: dict[str, ParticleModel] = {m.key: m for m in (
    ParticleModel(
        'homogeneous', 'Homogeneous sphere', 'Uniform sphere, optionally with surface conductance (latex beads).',
        (Parameter('radius', 'Radius', 'r', 'µm', 1e-6, 2.5, 0.05, 50.0, group='Other'),
         Parameter('eps_p', 'Permittivity', 'ε_p', '', 1.0, 2.55, 1.0, 120.0, group='Particle'),
         Parameter('sigma_p', 'Bulk conductivity', 'σ_p', 'S/m', 1.0, 1e-4, 1e-8, 1.0, True, group='Particle'),
         Parameter('k_s', 'Surface conductance', 'K_s', 'nS', 1e-9, 0.0, 0.0, 10.0,
                   description='total surface conductance; σ_p,eff = σ_p + 2 K_s / r', group='Particle')),
        _homogeneous),
    ParticleModel(
        'single_shell', 'Single-shell', 'Cytoplasm surrounded by a membrane (mammalian cells).',
        (RADIUS, D_MEM, EPS_MEM, SIGMA_MEM, EPS_CYTO, SIGMA_CYTO), _single_shell),
    ParticleModel(
        'two_shell', 'Two-shell (cell wall)', 'Cytoplasm, membrane and cell wall (yeast, bacteria, plant cells).',
        (RADIUS, D_WALL, EPS_WALL, SIGMA_WALL, D_MEM, EPS_MEM, SIGMA_MEM, EPS_CYTO, SIGMA_CYTO), _two_shell),
    ParticleModel(
        'three_shell', 'Three-shell (nucleus)', 'Nucleus (nucleoplasm + envelope), cytoplasm and membrane.',
        (RADIUS, D_MEM, EPS_MEM, SIGMA_MEM, EPS_CYTO, SIGMA_CYTO, R_NUC, D_ENV, EPS_ENV, SIGMA_ENV, EPS_NP, SIGMA_NP),
        lambda si: _nucleated(si, wall=False)),
    ParticleModel(
        'four_shell', 'Four-shell (nucleus + wall)', 'Nucleus, cytoplasm, membrane and cell wall.',
        (RADIUS, D_WALL, EPS_WALL, SIGMA_WALL, D_MEM, EPS_MEM, SIGMA_MEM, EPS_CYTO, SIGMA_CYTO,
         R_NUC, D_ENV, EPS_ENV, SIGMA_ENV, EPS_NP, SIGMA_NP),
        lambda si: _nucleated(si, wall=True)),
)}


def full_label(parameter: Parameter) -> str:
    """
    The parameter's name outside its group: 'Membrane permittivity' (in the Membrane group just 'Permittivity').
    Labels that already say what they are (radii, thicknesses, 'Buffer permittivity') stay as they are.
    """
    label, group = parameter.label, parameter.group
    if group in ('Other', 'Shell dimensions') or label.lower().startswith(group.lower()):
        return label
    return f'{group} {label[:1].lower()}{label[1:]}'


def grouped_parameters(model_key: str) -> list[tuple[str, list[Parameter]]]:
    """
    Parameters of a model, buffer included, grouped for display (Buffer, Particle / Cell, Membrane, ...).

    Args:
        model_key (str): Catalog key.

    Returns:
        list[tuple[str, list[Parameter]]]: (group, parameters) in GUI order.
    """
    params = list(MEDIUM_PARAMETERS) + list(MODELS[model_key].parameters)
    return [(g, [p for p in params if p.group == g]) for g in GROUPS if any(p.group == g for p in params)]


## Spectra ##


def cm_factor(model: ParticleModel, frequency_hz: np.ndarray, values: dict[str, float],
              eps0: float = EPSILON_0) -> np.ndarray:
    """
    Complex Clausius-Mossotti factor of a model in its medium.

    Args:
        model (ParticleModel): Particle model.
        frequency_hz (np.ndarray): Frequencies (Hz).
        values (dict[str, float]): Particle and medium parameters in display units.
        eps0 (float): Vacuum permittivity (F/m).

    Returns:
        np.ndarray: K(f); Re[K] is the DEP spectrum.
    """
    omega = 2 * np.pi * np.asarray(frequency_hz, dtype=float)
    eps_m = complex_permittivity(medium_material(values), omega, eps0)
    return clausius_mossotti(model.permittivity(frequency_hz, values, eps0), eps_m)
