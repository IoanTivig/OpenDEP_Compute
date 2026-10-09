"""
Dielectric models of spherical particles and cells (Qt-free).

All quantities are SI: permittivity in F/m, conductivity in S/m, lengths in m, angular frequency
omega = 2 pi f in rad/s. A material is described by its complex permittivity

    eps* = eps0 eps_r - j sigma / omega                                          (1)

The Clausius-Mossotti factor of a particle (eps_p*) in a medium (eps_m*) is

    K(omega) = (eps_p* - eps_m*) / (eps_p* + 2 eps_m*)                          (2)

and the time-averaged dielectrophoretic force on a sphere of radius r is

    F = 2 pi eps_m r^3 Re[K] grad |E_rms|^2                                     (3)

(Pohl 1978; Jones 1995, ch. 2). Re[K] lies between -0.5 and 1.

Shelled particles are reduced to a homogeneous sphere of equivalent permittivity, one shell at a
time from the inside out ("smeared-out" multi-shell model; Irimajiri, Hanai and Inouye 1979;
Jones 1995, ch. 3; Huang et al. 1992). A core of permittivity eps_in* and radius r_in inside a shell
of permittivity eps_s* and outer radius r_out is equivalent to a sphere of radius r_out with

    eps_eq* = eps_s* [ (r_out/r_in)^3 + 2 k ] / [ (r_out/r_in)^3 - k ],
    k = (eps_in* - eps_s*) / (eps_in* + 2 eps_s*)                               (4)

For a thin membrane the single-shell model is often written with the specific membrane
capacitance C_mem = eps0 eps_mem / d and conductance G_mem = sigma_mem / d (per unit area):

    eps_eq* = C_mem* r eps_cyto* / (C_mem* r + eps_cyto*),  C_mem* = C_mem - j G_mem / omega   (5)

(thin-shell limit of (4) for d << r; Pethig 2017, ch. 9; Gascoyne et al. 1997). It is the form to
fit when the data cannot separate eps_mem from d, which is the usual case.

Homogeneous particles with a charged surface (latex beads) get an effective conductivity
sigma_p = sigma_bulk + 2 K_s / r, with K_s the total surface conductance (O'Konski 1960;
Ermolina and Morgan 2005).

Validated against MyDEP 1.0.1 (Cottet et al. 2019) for the homogeneous, single-, two-, three- and
four-shell models (tests/test_models.py); MyDEP uses eps0 = 1 / (36 pi 1e9) F/m, 0.14 % below
the CODATA value used here.

References
    Cottet J et al. MyDEP: a new computational tool for dielectric modeling of particles and cells.
        Biophys J 116 (2019) 12-18. doi:10.1016/j.bpj.2018.11.021
    Ermolina I, Morgan H. The electrokinetic properties of latex particles: comparison of electrophoresis
        and dielectrophoresis. J Colloid Interface Sci 285 (2005) 419-428. doi:10.1016/j.jcis.2004.11.003
    Gascoyne PRC, Wang XB, Huang Y, Becker FF. Dielectrophoretic separation of cancer cells from blood.
        IEEE Trans Ind Appl 33 (1997) 670-678. doi:10.1109/28.585856
    Huang Y, Hölzel R, Pethig R, Wang XB. Differences in the AC electrodynamics of viable and non-viable
        yeast cells determined through combined dielectrophoresis and electrorotation studies.
        Phys Med Biol 37 (1992) 1499-1517. doi:10.1088/0031-9155/37/7/003
    Irimajiri A, Hanai T, Inouye A. A dielectric theory of "multi-stratified shell" model with its
        application to a lymphoma cell. J Theor Biol 78 (1979) 251-269. doi:10.1016/0022-5193(79)90268-6
    Jones TB. Electromechanics of Particles. Cambridge University Press (1995). doi:10.1017/CBO9780511574498
    O'Konski CT. Electric properties of macromolecules. V. Theory of ionic polarization in polyelectrolytes.
        J Phys Chem 64 (1960) 605-619. doi:10.1021/j100834a023
    Pethig R. Dielectrophoresis: Theory, Methodology and Biological Applications. Wiley (2017).
        doi:10.1002/9781118671443
    Pohl HA. Dielectrophoresis: The Behavior of Neutral Matter in Nonuniform Electric Fields.
        Cambridge University Press (1978). ISBN 0-521-21657-5
"""
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.constants import epsilon_0 as EPSILON_0

## Materials ##


@dataclass(frozen=True)
class Material:
    """
    A lossy dielectric.
    """
    eps_r: float                # relative permittivity
    sigma: float                # conductivity (S/m)


@dataclass(frozen=True)
class Shell:
    """
    A concentric shell of a particle.
    """
    material: Material
    thickness: float            # m


def complex_permittivity(material: Material, omega: np.ndarray, eps0: float = EPSILON_0) -> np.ndarray:
    """
    Complex permittivity eps0 eps_r - j sigma / omega, equation (1).

    Args:
        material (Material): Permittivity and conductivity.
        omega (np.ndarray): Angular frequencies (rad/s).
        eps0 (float): Vacuum permittivity (F/m); only changed to compare with other software.

    Returns:
        np.ndarray: Complex permittivity (F/m).
    """
    omega = np.asarray(omega, dtype=float)
    return eps0 * material.eps_r - 1j * material.sigma / omega


## Equivalent permittivity ##


def shell_equivalent(eps_inner: np.ndarray, eps_shell: np.ndarray, r_inner: float, r_outer: float) -> np.ndarray:
    """
    Equivalent permittivity of a sphere covered by one shell, equation (4).

    Args:
        eps_inner (np.ndarray): Complex permittivity of everything inside the shell.
        eps_shell (np.ndarray): Complex permittivity of the shell.
        r_inner (float): Inner radius of the shell (m).
        r_outer (float): Outer radius of the shell (m).

    Returns:
        np.ndarray: Equivalent complex permittivity of the covered sphere.
    """
    if not 0 < r_inner < r_outer:
        raise ValueError(f'⚠️ A shell needs 0 < inner radius < outer radius (got {r_inner:g} m, {r_outer:g} m)')
    gamma = (r_outer / r_inner) ** 3
    k = (eps_inner - eps_shell) / (eps_inner + 2 * eps_shell)
    return eps_shell * (gamma + 2 * k) / (gamma - k)


def multishell_permittivity(omega: np.ndarray, radius: float, core: Material, shells: Sequence[Shell] = (),
                            eps0: float = EPSILON_0) -> np.ndarray:
    """
    Equivalent permittivity of a core with concentric shells, applying equation (4) from the inside out.

    Args:
        omega (np.ndarray): Angular frequencies (rad/s).
        radius (float): Outer radius of the particle, outermost shell included (m).
        core (Material): The innermost region.
        shells (Sequence[Shell]): Shells from the innermost to the outermost.
        eps0 (float): Vacuum permittivity (F/m).

    Returns:
        np.ndarray: Equivalent complex permittivity of the whole particle.

    Raises:
        ValueError: The shells are thicker than the particle radius.
    """
    # 1. Radii from the outside in: every shell's outer radius
    outer = [radius]
    for shell in reversed(shells[1:]):
        outer.insert(0, outer[0] - shell.thickness)
    core_radius = outer[0] - shells[0].thickness if shells else radius
    if core_radius <= 0:
        raise ValueError('⚠️ The shells are thicker than the particle radius')

    # 2. Inside out
    eps = complex_permittivity(core, omega, eps0)
    r_in = core_radius
    for shell, r_out in zip(shells, outer):
        eps = shell_equivalent(eps, complex_permittivity(shell.material, omega, eps0), r_in, r_out)
        r_in = r_out
    return eps


def thin_membrane_permittivity(omega: np.ndarray, radius: float, cytoplasm: Material, c_mem: float, g_mem: float,
                               eps0: float = EPSILON_0) -> np.ndarray:
    """
    Single-shell cell from the specific membrane capacitance and conductance, equation (5).

    Args:
        omega (np.ndarray): Angular frequencies (rad/s).
        radius (float): Cell radius (m).
        cytoplasm (Material): Cell interior.
        c_mem (float): Specific membrane capacitance (F/m²).
        g_mem (float): Specific membrane conductance (S/m²).
        eps0 (float): Vacuum permittivity (F/m).

    Returns:
        np.ndarray: Equivalent complex permittivity of the cell.
    """
    omega = np.asarray(omega, dtype=float)
    c_star = (c_mem - 1j * g_mem / omega) * radius
    eps_cyto = complex_permittivity(cytoplasm, omega, eps0)
    return c_star * eps_cyto / (c_star + eps_cyto)


def surface_conductivity(sigma_bulk: float, surface_conductance: float, radius: float) -> float:
    """
    Effective conductivity of a homogeneous particle with surface conduction (O'Konski 1960).

    Args:
        sigma_bulk (float): Bulk conductivity of the particle material (S/m).
        surface_conductance (float): Total surface conductance K_s (S).
        radius (float): Particle radius (m).

    Returns:
        float: sigma_bulk + 2 K_s / r (S/m).
    """
    return sigma_bulk + 2.0 * surface_conductance / radius


## Clausius-Mossotti factor and force ##


def clausius_mossotti(eps_particle: np.ndarray, eps_medium: np.ndarray) -> np.ndarray:
    """
    Complex Clausius-Mossotti factor, equation (2).

    Args:
        eps_particle (np.ndarray): Complex permittivity of the particle.
        eps_medium (np.ndarray): Complex permittivity of the medium.

    Returns:
        np.ndarray: K(omega); its real part sets the DEP force, the imaginary part electrorotation.
    """
    return (eps_particle - eps_medium) / (eps_particle + 2 * eps_medium)


def dep_force(re_k: np.ndarray, radius: float, medium: Material, grad_e2: float,
              eps0: float = EPSILON_0) -> np.ndarray:
    """
    Time-averaged DEP force on a sphere, equation (3).

    Args:
        re_k (np.ndarray): Re[K].
        radius (float): Particle radius (m).
        medium (Material): Suspending medium (only its permittivity enters).
        grad_e2 (float): grad |E_rms|^2 (V²/m³).
        eps0 (float): Vacuum permittivity (F/m).

    Returns:
        np.ndarray: Force (N); positive = towards high field (pDEP).
    """
    return 2.0 * np.pi * eps0 * medium.eps_r * radius ** 3 * np.asarray(re_k) * grad_e2
