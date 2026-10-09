# Dielectric models

OpenDEP Compute describes a particle or cell by its **equivalent complex permittivity** and compares it with the suspending medium through the **Clausius-Mossotti factor**. The DEP spectrum is the real part of that factor, Re[K], as a function of frequency.

## The basic equations

Every material (medium, cytoplasm, membrane, ...) has a complex permittivity

    ε* = ε0 εr − j σ / ω,        ω = 2π f

The Clausius-Mossotti factor of a particle in a medium is

    K(ω) = (εp* − εm*) / (εp* + 2 εm*)

and the time-averaged DEP force on a sphere of radius r is

    F = 2π εm r³ Re[K] ∇|E_rms|²

Re[K] lies between −0.5 (strongest nDEP) and 1 (strongest pDEP). Sources: Pohl (1978); Jones (1995), ch. 2.

## Shelled particles

A cell is a set of concentric layers. Each layer is folded into the one inside it, from the centre outwards: a sphere of permittivity εin* and radius r_in, covered by a shell εs* with outer radius r_out, behaves like a homogeneous sphere of radius r_out with

    ε_eq* = εs* [ (r_out/r_in)³ + 2k ] / [ (r_out/r_in)³ − k ],    k = (εin* − εs*) / (εin* + 2 εs*)

This is the "multi-stratified shell" model of Irimajiri, Hanai and Inouye (1979), also derived in Jones (1995), ch. 3, and used for DEP by Huang et al. (1992).

## The models

| Model | Layers, inside → out | Typical use |
|---|---|---|
| Homogeneous sphere | one material, optional surface conductance | latex beads, droplets |
| Single-shell | cytoplasm, membrane | mammalian cells |
| Two-shell (cell wall) | cytoplasm, membrane, wall | yeast, bacteria, plant cells |
| Three-shell (nucleus) | nucleoplasm, nuclear envelope, cytoplasm, membrane | nucleated cells, lymphocytes |
| Four-shell (nucleus + wall) | as three-shell, plus a wall | walled nucleated cells |

**Geometry.** The radius is the **outer** radius of the whole particle, cell wall included; layer thicknesses are taken inwards from it. The nucleus radius includes the nuclear envelope. This is the convention of MyDEP (Cottet et al. 2019).

### Membrane permittivity and thickness

A membrane a few nanometres thick on a cell several micrometres across acts like a capacitor of capacitance ε0 εmem / d per unit area. A DEP spectrum fixes that ratio, not εmem and d separately: keep the thickness fixed (7 nm by default) and fit the permittivity. At low buffer conductivity the first crossover is close to

    f_x1 ≈ √2 σm / (2π r ε0 εmem / d)

(Gascoyne et al. 1997; Pethig 2017, ch. 9).

### Beads: surface conductance

Charged particles conduct along their surface. A homogeneous particle of radius r then has the effective conductivity σp + 2 K_s / r, with K_s the total surface conductance (O'Konski 1960; Ermolina and Morgan 2005).

## Validation

Every model is checked against **MyDEP 1.0.1** (Cottet et al. 2019): the program's own code computed reference permittivities for all five shell models, and OpenDEP Compute agrees to better than 1 part in 10¹⁰. The tests also check analytic limits (low- and high-frequency Re[K] of a homogeneous sphere), the agreement of the shell model with its thin-membrane limit, and the crossover formula above.

MyDEP uses ε0 = 1/(36π·10⁹) F/m; OpenDEP Compute uses the CODATA value 8.8541878128·10⁻¹² F/m (0.14 % higher).

## References

- Cottet J, Fabregue O, Berger C, Buret F, Renaud P, Frénéa-Robin M. MyDEP: a new computational tool for dielectric modeling of particles and cells. *Biophys J* 116 (2019) 12–18. [doi:10.1016/j.bpj.2018.11.021](https://doi.org/10.1016/j.bpj.2018.11.021)
- Ermolina I, Morgan H. The electrokinetic properties of latex particles: comparison of electrophoresis and dielectrophoresis. *J Colloid Interface Sci* 285 (2005) 419–428. [doi:10.1016/j.jcis.2004.11.003](https://doi.org/10.1016/j.jcis.2004.11.003)
- Gascoyne PRC, Wang XB, Huang Y, Becker FF. Dielectrophoretic separation of cancer cells from blood. *IEEE Trans Ind Appl* 33 (1997) 670–678. [doi:10.1109/28.585856](https://doi.org/10.1109/28.585856)
- Huang Y, Hölzel R, Pethig R, Wang XB. Differences in the AC electrodynamics of viable and non-viable yeast cells determined through combined dielectrophoresis and electrorotation studies. *Phys Med Biol* 37 (1992) 1499–1517. [doi:10.1088/0031-9155/37/7/003](https://doi.org/10.1088/0031-9155/37/7/003)
- Irimajiri A, Hanai T, Inouye A. A dielectric theory of "multi-stratified shell" model with its application to a lymphoma cell. *J Theor Biol* 78 (1979) 251–269. [doi:10.1016/0022-5193(79)90268-6](https://doi.org/10.1016/0022-5193(79)90268-6)
- Jones TB. *Electromechanics of Particles*. Cambridge University Press (1995). [doi:10.1017/CBO9780511574498](https://doi.org/10.1017/CBO9780511574498)
- O'Konski CT. Electric properties of macromolecules. V. Theory of ionic polarization in polyelectrolytes. *J Phys Chem* 64 (1960) 605–619. [doi:10.1021/j100834a023](https://doi.org/10.1021/j100834a023)
- Pethig R. *Dielectrophoresis: Theory, Methodology and Biological Applications*. Wiley (2017). [doi:10.1002/9781118671443](https://doi.org/10.1002/9781118671443)
- Pohl HA. *Dielectrophoresis: The Behavior of Neutral Matter in Nonuniform Electric Fields*. Cambridge University Press (1978). ISBN 0-521-21657-5.
- Tivig I, Moisescu MG, Savopol T. OpenDEP: an open-source platform for dielectrophoresis spectra acquisition and analysis. *ACS Omega* 8 (2023) 38715–38722. [doi:10.1021/acsomega.3c06052](https://doi.org/10.1021/acsomega.3c06052)

## Published parameter sets

OpenDEP Compute includes **published particle and cell parameter sets** (beads, red blood cells, lymphocytes, HeLa, MCF7, yeast, ...) as starting values and for comparison. They come from the literature database of **MyDEP 1.0.1** (Cottet et al. 2019), which the MyDEP authors distribute under the MIT licence; their copyright notice and licence travel with the data. Each set also names the publication its values come from, with its DOI. Ten ellipsoidal particles of that database are not included until ellipsoids are supported.

> Parameter sets from the MyDEP 1.0.1 database. Copyright (c) 2018 Université de Lyon – Laboratoire Ampère CNRS UMR 5005 & EPFL – LMIS4, MIT licence. Cottet J et al., *Biophys J* 116 (2019) 12–18.
