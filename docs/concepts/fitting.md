# Fitting

A fit finds the model parameters that make the model spectrum match the measured one.

## What is compared

The measured values y are compared with

    y(f) = s · Re[K(f; p)]

with p the model parameters and s a **scale factor**. Most measured spectra (grayness factor, DEP rate, 3DEP intensity, OpenDEP Control spectra scaled to the CM range) are only **proportional** to Re[K]: for them s is free and fitted, and must be positive. For spectra that are Re[K] itself, s = 1. Replicates fitted together share p and each gets its own s, because each measurement has its own unknown factor.

## Choosing what to fit

Each parameter is **free** (fitted) or **fixed** (kept at its value). Fix what you know: the cell radius (measured), the medium conductivity and permittivity (measured), and values the spectrum cannot reach. A DEP spectrum between about 1 kHz and 10 MHz mainly determines:

- the **membrane permittivity** (with the thickness fixed), through the first crossover,
- the **cytoplasm conductivity** σ_cyto, through the high-frequency plateau and the second crossover.

Membrane permittivity and thickness cannot be fitted together: only their ratio ε0 εmem / d affects the spectrum, so keep the thickness fixed. The membrane conductivity is usually poorly determined unless the buffer conductivity is low.

## How the fit works

1. Conductivities and other parameters spanning decades are searched in log space, inside their ranges.
2. For given model parameters the best scale factor is exact (a linear problem), so the search only runs over the model parameters (variable projection; Golub and Pereyra 1973).
3. The search starts from the values in the table and from 12 more points spread over the ranges (Latin hypercube), and keeps the best result, so it does not stop in a local minimum.
4. A last fit over all free parameters and scales gives the **standard errors** and **correlations** (from the Jacobian, Press et al. 2007).

Points switched off or marked as outliers are left out. With error bars on every point the residuals are weighted by 1/error; the standard errors are then never smaller than the error bars imply, and they grow when the scatter is larger (reduced chi-square above 1).

## Reading the result

| Item | Meaning |
|---|---|
| value ± standard error | fitted value; the standard error assumes the model is right |
| not determined | the standard error exceeds the value, or the parameter correlates above 0.95 with another: fix one of them |
| at bound | the value hit the end of its range: widen the range or fix the parameter |
| first / second crossover | where the fitted Re[K] changes sign: nDEP → pDEP (first) and pDEP → nDEP (second), searched between 100 Hz and 1 GHz |
| R² | fit quality: share of the variation the model explains |

**Outliers** are only suggested, never removed: a point whose residual has a robust z-score above 3.5 (Iglewicz and Hoaglin 1993) is marked as a suggestion; you decide.

## Checked against other programs

- Simulated spectra with known parameters and noise: the parameters are recovered within their standard errors.
- **3DEP** example file: with the same fixed values and points, the membrane capacitance ε0 εmem / d agrees with 3DEP's within its error, and the first crossover within 2 % (71 against 70.6 kHz).
- **OpenDEP Compute 1.x** example file: at the parameters Compute 1.x reported, the model reproduces its fitted curve to 0.03 %; refitting the same parameters gives a better fit (R² 0.96 against 0.90) with similar values.

## References

- Golub G, Pereyra V. The differentiation of pseudo-inverses and nonlinear least squares problems whose variables separate. *SIAM J Numer Anal* 10 (1973) 413–432. [doi:10.1137/0710036](https://doi.org/10.1137/0710036)
- Iglewicz B, Hoaglin DC. *How to Detect and Handle Outliers*. ASQC Quality Press (1993).
- Press WH, Teukolsky SA, Vetterling WT, Flannery BP. *Numerical Recipes*, 3rd ed., ch. 15. Cambridge University Press (2007).
