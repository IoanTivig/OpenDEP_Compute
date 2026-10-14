# File formats

OpenDEP Compute opens the files of every OpenDEP program, and of the 3DEP instrument, and keeps everything it reads: points are switched off or marked as outliers, never deleted.

## What can be opened

| File | Written by | What comes in |
|---|---|---|
| `.odspec` OpenDEP Spectrum, version 1 | OpenDEP View | the spectrum (frequency, value, error) |
| `.odspec` OpenDEP Spectrum, version 2 | OpenDEP Control, OpenDEP Compute | the spectrum, plus the measured quantity, raw values and normalisation factor, per-point data (phase, …), known parameters and where it came from |
| `.odfit` OpenDEP Fit | OpenDEP Compute, OpenDEP View | the spectra (with their sample) and, when the file holds one, the fit: it becomes a memorized fit of the imported spectra |
| `.xlsx` scatter (3 columns) | OpenDEP View | the spectrum |
| `.xlsx` data + fit | OpenDEP Compute 1.x | the spectrum with its point flags |
| `.xlsx` image conversion ("Centralization.xlsx", B1 "Experimental grayness factor") | OpenDEP Compute 1.x | the grayness-factor spectrum (relative: fitted with a free scale factor) |
| `experiment_parameters.csv` | OpenDEP Control (Frequency Spectrum) | one spectrum per quantity: DEP rate, grayness factor (ref), grayness factor (Population) or displacement (Single Cell), with per-point data |
| `.csv` result file | 3DEP (DEPtech) | the spectrum with its removed points and outliers; 3DEP's own fit is kept as information |

**Older file names.** Until October 2026 the OpenDEP programs saved spectra as `.ods` ("OpenDEP Scatter") and model curves as `.odc`. Those names belong to other programs on Windows (`.ods` is the LibreOffice / OpenDocument spreadsheet, `.odc` an Excel data connection), so double-clicking them opened the wrong program. The content is unchanged: `.ods` and `.odc` files open as before, and files are recognised by their content, not their name. A real LibreOffice spreadsheet saved as `.ods` is refused with that explanation: save it as `.xlsx`.

**OpenDEP Fit (`.odfit`)** keeps a fit together: the spectra with their original values, the model curve, the link between them (each spectrum's scale factor: on the curve's Re[K] axis a point is drawn at value ÷ scale) and the fit results (values ± SE, R², crossovers). The data are stored once, unscaled. A file made in OpenDEP View by linking spectra to a curve by hand has no fit results; its spectra are imported as usual. A replicate group exported from OpenDEP View also says which biological replicate (suspension) each spectrum belongs to; Compute keeps that label with the spectrum.

## Relative and absolute spectra

Most measured spectra (grayness factor, DEP rate, 3DEP intensity, and Control's spectra scaled to the CM range) are **proportional** to Re[K] with an unknown factor. They are marked *relative*, and a fit includes a free scale factor. Values that are Re[K] itself are marked *absolute*.

Model curve files (`.odcurve`, formerly `.odc`) belong to OpenDEP View and are not imported. OpenDEP View 2 has the same five models as Compute, with the same formulas and the outer radius for every model (its files say `"radius_convention": "outer"`). Note for files from View 1.x: their **two-shell** curves were computed with an incorrect formula (the outer shell combined with the raw inner-shell permittivity instead of the equivalent one; see [Dielectric models](../concepts/models.md)) and their two-shell radius is the core radius; Compute converts them to the outer radius and recomputes them with the correct model.

## What can be saved

| File | Opens in |
|---|---|
| `.odcproject` OpenDEP Compute project | OpenDEP Compute: the whole project (spectra, curves, memorized fits) in one file, made to be sent between users. A zip archive: any unzip tool shows the OpenDEP Spectrum files inside |
| `.odfit` OpenDEP Fit | OpenDEP View (the spectra linked to the fitted curve, each divided by its scale factor) and Compute (the memorized fit) |
| `.odspec` OpenDEP Spectrum, version 2 | OpenDEP View (and Compute: flags and per-point data are kept) |
| `.odcurve` OpenDEP Curve | OpenDEP View 2, all five models (homogeneous, single-, two-, three- and four-shell); View 1.x shows homogeneous and single-shell curves only (rename the file to `.odc` to open it there) |
| `.xlsx` View scatter | OpenDEP View, Excel (points in use only) |
| `.csv` tables | Any spreadsheet or analysis software (Excel, Origin, LibreOffice, Python, R). A spectrum: every point with its error and the Use / Outlier flags (Data page). A fit: `<fit> - data.csv` with one row per measured point (spectrum, sample, frequency, value and error as measured, scale factor, Re[K] data and error, fitted Re[K], residual, used) and `<fit> - curve.csv` with the fitted Re[K] and Im[K] at 200 frequencies. Point as decimal separator, UTF-8 |
