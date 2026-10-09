# Working with OpenDEP Compute

## Projects

Start by creating a project or opening one. A project is **one file**, `<name>.odcproject`: copy it, back it up or send it to a colleague like any document, and double-click it to open it (installed program). It keeps **copies** of the imported spectra and the saved fits; the files you import are never modified. **Save** (Ctrl+S) writes the project; closing with unsaved changes asks first. Each save keeps the previous version as `<name>.odcproject.bak`.

If part of a project cannot be read (for example a damaged copy), the rest opens and a message lists what was left out. **Project folders** made by earlier versions open as before; **Save** then writes them as one `.odcproject` file next to the folder, which is left untouched (delete it yourself once the file is saved).

## Data

- **Import…** opens spectra from OpenDEP Control, OpenDEP View, OpenDEP Compute 1.x and 3DEP ([File formats](file-formats.md)). Several files at once are fine. Warnings appear in the orange box. Model curve files (.odcurve, formerly .odc) belong to OpenDEP View and are not imported.
- **Convert images…** computes spectra from image sets ([Converting images](conversion.md)).
- **Sample…** gives the selected spectra a sample name: replicates of one sample share it.
- Select one spectrum to see its points. Untick **Use** to leave a point out of fits; tick **Outlier** to mark it (shown as a red ×, also left out). Nothing is deleted.
- **Suggest outliers** proposes points of the selected spectra that deviate strongly from their neighbours (judged without any model, so the choice does not favour the model you fit later); you confirm. The first and last points are not judged.
- **Error bars | Area** switches how measured points are drawn, as in OpenDEP View: points with error bars, or a band of value ± error.
- **Export** writes the selected spectra to a folder you choose: as OpenDEP Spectrum (.odspec, every point with its flags) as View Excel (.xlsx, the points in use) or as a **CSV table** (every point with its error and flags, for other software or work by hand). **Send to View** opens them in OpenDEP View at once (below).

## Fit

1. Tick the spectra to fit: one spectrum, or several replicates of **one sample**. Ticked spectra are fitted together: all their points determine one set of cell parameters, and each spectrum gets its own scale factor (so replicates with different signal strength, or a DEP rate and a grayness factor of the same cells, can be combined). Do not tick spectra of different samples together: fit each sample on its own.
2. Choose the **model**. Its parameters appear grouped as in OpenDEP View: **Buffer**, **Cytoplasm** (or **Particle** for the homogeneous model), **Other** (the radii), **Shell dimensions** (every thickness), then the layers **Membrane**, **Cell wall**, **Nuclear envelope**, **Nucleoplasm**, with literature-based default values.
3. The table lists, per parameter: **Fit** (ticked: fitted; unticked: fixed at its value), the name, **Value**, **Min** / **Max** (the search range of a fitted parameter) and the unit. Enter the values you know (buffer conductivity and permittivity, cell radius) and leave them unticked.
4. Options: the **scale factor** (automatic: free for relative spectra) and **weighting** by error bars.
5. **Fit**. At the top: the **first and second crossovers** of the fitted curve and **R²**. The plot shows the data divided by their scale factor on the Re[K] axis, the fitted curve with the crossovers marked, and the residuals below with their error bars (or band). A solid zero line on both panels separates pDEP (above) from nDEP (below). Below the plot, the **Results** card shows the values in one card per group (the same groups), on a grid as in OpenDEP View: equal columns, as many as the width allows, and the rows of every card aligned like one table (the plot gets the rest of the height): each row gives the value with its standard error (fitted values in bold) and its status: **fitted**, **fixed** (grey, as entered), or in orange **not determined** / **at bound**, which tell you what to fix or widen ([Fitting](../concepts/fitting.md)).

Below the results: **Export fit…** writes the fit as one `.odfit` file: the spectra with their original values, the fitted curve, each spectrum's scale factor and the fit results. View opens it with every spectrum linked to the curve and drawn on it (divided by its scale factor, as plotted here). Separate files can be ticked as well: the fitted curve (.odcurve), the fitted spectra on the Re[K] scale (.odspec, already divided by the scale factor; the original values and the factor stay in the file), the fitted curve as 200 points (.odspec), and **Data tables (CSV)**: every point with its scale factor, Re[K], fitted value and residual, and the fitted curve as a second table ([File formats](file-formats.md)). An `.odfit` file can also be imported here (Data page): its spectra come in with the fit, under Saved fits and ready for a report. **Figure…** makes a publication figure and **Report…** a PDF report of the fit ([Figures and reports](reports.md)). **Send to View** opens it in OpenDEP View. **Add to Saved fits…** keeps the fit in the project's list (below).

### Saved fits

The fits added with **Add to Saved fits…** are listed below the model settings, with their R². They are kept in the project, so the list is still there when the project is opened again.

- **Open** (or a double-click) shows a saved fit again, without fitting anew: its spectra are ticked, its model, parameter values, Fit ticks, ranges, scale factor and weighting are set, and its curve, crossovers, R² and values appear. **Fit** then fits again from these settings (for example after changing a value); add it to the Saved fits under a new name to keep both.
- **Export** writes saved fits to a folder you choose: the selected ones (Ctrl or Shift selects several; **Select all**), or every fit when none is selected. **Fit files** (one `.odfit` per fit), **Data tables** (CSV: data and curve per fit), **PDF reports** (one per fit), **Figure…** (one selected fit), and the **Table of all fits** (CSV, always every saved fit: one row per fit, every parameter with its standard error; for comparing samples in a spreadsheet).
- **Send to View** opens the selected fits (or all) in OpenDEP View; **Remove** deletes the selected fits from the project (exported files stay).

## Exported files

Every export asks where to write: a folder for several files (spectra, saved fits), a file for one report or the table of all fits; **Figure…** and **Export fit…** have the folder in their dialog. The dialogs start in the last folder you used in this project (the first time, the project folder), so a series of exports goes to the same place with one click each. Comparing spectra and curves is done in OpenDEP View.

## Send to View

**Send to View** opens results in OpenDEP View straight away, without saving and opening files by hand:

| Page | Sends |
|---|---|
| Data | the selected spectra, as measured (`.odspec`) |
| Fit | the current fit (`.odfit`): the spectra linked to the fitted curve, each on the curve |
| Fit, Saved fits | the selected saved fits, or all (one `.odfit` each) |

View adds them to its open project (and asks for a project when none is open). If View is not running, Compute starts it with the files. The files are written to a temporary folder first (nothing is added to your folders); View copies them into its own project.

Compute finds View next to itself (installed side by side, or the source folders of the suite) or in the usual program folders. If it is elsewhere, Compute asks for View's folder once and remembers it. The two programs talk over a local channel of the computer (a named pipe on Windows, a socket file on Linux); nothing goes over the network.
