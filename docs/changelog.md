# Changes

## 2.1.0 (2026-10-12)

- **Report bug → Send to OpenDEP**: reports go to the OpenDEP team through the OpenDEP website (opendep.org), from a tester account (sign in once; the program keeps a token, not the password). Saving the report as a file still works; saved reports are sent later from the Reports tab (**Send selected**, **Send all unsent**), and the website never stores the same report twice.

## 2.0.0 (2026-10-10)

A rebuild of OpenDEP Compute from the ground up (PyQt6, Python 3.12).

- Imports spectra from OpenDEP Control (`experiment_parameters.csv`, `.odspec` / `.ods` v2), OpenDEP View (`.odspec` / `.ods`, Excel), OpenDEP Compute 1.x (Excel) and 3DEP (`.csv`), with point flags kept.
- New file names shared by Control, View and Compute: spectra `.odspec` (OpenDEP Spectrum), model curves `.odcurve`; the older `.ods` and `.odc` files still open.
- OpenDEP Fit files (`.odfit`): a fit's spectra, fitted curve, scale factors and results in one file. "Export fit…" writes it (and Saved fits → Export, for many fits); OpenDEP View opens the spectra linked to the curve; importing it here restores the saved fit.
- **Send to View** (Data and Fit pages): the selected spectra, the current fit or saved fits open in OpenDEP View at once; View is started when it is not running.
- Homogeneous, single-, two-, three- and four-shell models, validated against MyDEP 1.0.1 to 1e-10; published parameter sets from the MyDEP database (MIT licence).
- Fitting with a free scale factor per spectrum, replicates, error weighting, multi-start, standard errors and flags for undetermined parameters; first and second crossovers; R².
- Outlier suggestions judged from neighbouring points (no model).
- Image-set conversion with OpenDEP Control's grayness-factor algorithm; bright-field and fluorescence. Grid lines can be dragged, with or without snapping to the edges.
- Publication figures (journal sizes; PNG, TIFF, SVG, PDF) and two-page PDF fit reports.
- Projects as one file (`.odcproject`, to copy and send between users; double-click opens it), keeping copies of the data and the saved fits; a damaged part is reported and the rest opens; project folders of earlier versions open and are saved as a file. **Add to Saved fits** keeps a fit in the project's list: it opens again (no refit), and the saved fits are exported at once (the selected ones, or all): `.odfit` files, PDF reports, one table of all fits.
- CSV tables for other software or work by hand: spectra (Data page) and fits (data with scale, fitted value and residual per point, plus the fitted curve), also for all saved fits.
- Fit page: parameter table as Fit tick, name, Value, Min, Max, Unit; parameters grouped as in OpenDEP View (Buffer, Cytoplasm, Other, Shell dimensions, Membrane, …), in the table, the Results card (a grid of group cards with value ± SE and status) and the PDF report.
- Two pages, Data and Fit: each exports what it shows (no separate Export page), to a folder or file you choose; the dialogs start in the last folder used in the project.
- Fixed: the program could crash on closing (access violation, about 1 in 4 runs); figure legends could hide data points.
- User guide in the program (F1).
- **Report bug** (as in OpenDEP Control and View): a form saved as a Markdown report with the error, the recent output, a screenshot and where the program was; unexpected errors open it by themselves.

## 1.3.5

The previous version (PyQt5): image conversion, homogeneous and single-shell fits. It stays available as the tag `v1.3.5` and the branch `v1` of this repository.
