# Figures and reports

## Publication figure

**Figure…** (Fit page: the fit on screen, or one memorized fit: **Memorized fits → Export → Figure…**) draws the fitted spectrum for a paper: the data divided by their scale factor on the Re[K] axis, the fitted curve, the first and second crossovers (dashed), and optionally the residual panel and the legend. Points are drawn as on screen, with **error bars** or as an **area**.

| Size | Width × height | Use |
|---|---|---|
| One column | 85 × 75 mm | single-column figure (Elsevier, ACS, RSC) |
| One and a half columns | 120 × 95 mm | |
| Two columns | 175 × 115 mm | full-width figure |

Save as **PNG** or **TIFF** (600 dpi, for submission systems) or **SVG** / **PDF** (vector; the text stays text, so it can be edited in Inkscape or Illustrator). Text is 8-9 pt Arial (Helvetica or DejaVu Sans when Arial is missing).

## Fit report

**Report…** on the Fit page, or **Memorized fits → Export → PDF reports** for the selected memorized fits (or all), writes a two-page A4 PDF:

1. The fit's name, date and software version; the figure; the **first and second crossovers**, **R²** with the number of points and fitted parameters; the model and what was fitted.
2. Every parameter with its value ± standard error, unit and status (fitted, fixed, not determined, at bound); the fit settings (scale factor, weighting, method); the spectra used, with their points in use and source file; the fit's warnings; and the references of the model and of OpenDEP, to cite.

A report of a memorized fit needs its spectra: removing a spectrum from the project also makes its fits unreportable.

## Table of all fits

**Table of all fits (CSV)** (Memorized fits → Export) writes every memorized fit in one table, whatever is selected (one row per fit): model, spectra, samples, R², points, free parameters, crossovers, and for every parameter its value, standard error and status. It opens in Excel, Origin or Python for comparing samples.
