# Quick start

From an OpenDEP Control Frequency Spectrum run to membrane and cytoplasm values.

1. **Create a project**: on the start page, **Create new project** and give the project file a name and place (for example `DEP analysis 2026-10.odcproject`).
2. **Import**: on the **Data** page, **Import…** and open the run's `experiment_parameters.csv`. Three spectra appear: DEP rate, Grayness factor (ref) and Grayness factor. Give replicates the same **Sample…** name.
3. **Look at the points**: select a spectrum. Untick **Use** for a point you do not trust, or try **Suggest outliers**. The zero line separates pDEP (above) from nDEP (below).
4. **Fit**: on the **Fit** page, tick the spectrum (or its replicates). Keep the **Single-shell** model. In the parameter table enter what you know: under **Buffer** the **Conductivity** (S/m), under **Other** the cell **Radius** (µm). The membrane permittivity and the cytoplasm conductivity are ticked for fitting. Press **Fit**.
5. **Read the result**: the tiles show the **first and second crossovers** and **R²**; the **Results** card below the plot each value with its standard error, grouped like the parameters. "Not determined" means the spectrum does not fix that parameter: untick it and enter a literature value ([Fitting](concepts/fitting.md)).
6. **Keep it**: **Export fit…** (an `.odfit` file), **Report…** for a PDF, **Figure…** for a publication figure; **Add to Saved fits…** to open it again or export many fits together later.
7. **Save** the project (Ctrl+S).

Control's spectra are relative (the grayness factor and the DEP rate are proportional to Re[K]), so each gets a free scale factor: the crossovers and the shape determine the fit, not the height.
