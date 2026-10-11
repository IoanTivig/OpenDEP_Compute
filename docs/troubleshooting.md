# Troubleshooting

## Importing

**"no frequency summary"**: the `experiment_parameters.csv` is from an Amplitude or Time Course run, which are not spectra.

**A model curve file (.odcurve or .odc) is not imported**: curves belong to OpenDEP View. Compute imports measured spectra.

**Excel file not recognised**: Compute reads View's 3-column scatter (frequency, value, error) and Compute 1.x's data + fit workbooks. Other layouts: save the columns as a View scatter, or as CSV in the 3DEP layout.

## Converting images

**"no _DATA folder with images"**: the folder must contain `_DATA` with images named `..._<frequency>Hz.jpg` (or .png, .tif). Choose the experiment folder, or the folder above it.

**Lines in the wrong places**: without Control's `experiment_parameters.csv` the lines are only a suggestion. Remove wrong ones with a right click and add missing ones with a left click on the edge. Check **Edges** (vertical or horizontal) and **Electrodes** (which regions are shaded).

**Signs inverted**: choose the right **Light**: bright-field when cells look darker than the medium, fluorescence when brighter.

## Fitting

**"not determined"**: the spectrum does not fix that parameter (its error is larger than its value, or it is strongly correlated with another). Untick it and enter a literature value; typical candidates: the membrane conductivity, the cytoplasm permittivity, the thickness together with the permittivity of the membrane.

**"at bound"**: the best value lies at Min or Max. Widen the range if the range is not physical, or check the fixed values (buffer conductivity, radius).

**R² low**: look at the residuals. A systematic wave means the model or a fixed value is wrong (two-shell for walled cells, the buffer conductivity); scattered residuals mean noisy data (more replicates, outliers).

**No second crossover**: the fitted curve stays positive up to 1 GHz, usually because the high-frequency points do not reach it; it is shown as "-".

## Reports and figures

**"some of its spectra were removed"**: a saved fit's report needs its spectra in the project. Import them again and fit again.

**Fonts in SVG look different elsewhere**: SVG keeps the text as text in Arial; a computer without Arial substitutes a similar font. Use PDF to keep the exact look.

## Reporting a bug

**Report bug** (top right) opens a form, as in OpenDEP Control and View: a short **title**, **what you did** (files imported, model, settings, the clicks that led to the problem), **what you expected** and **what happened instead**. When the program meets an unexpected error, the form opens by itself with the error filled in. Leave **Attach the console and log** ticked (the last 200 lines of the program's output) and tick **Attach a screenshot** when the problem is visible on screen: the screenshot is taken when the form opens, before it covers the window.

**Send to OpenDEP** sends the report to the OpenDEP team through the OpenDEP website. It needs a tester account (ask the team for one): the first time, sign in with your user name and password; the program then keeps a sign-in token for this computer, never your password (**Sign out** at the top of the form forgets it). The report arrives with the program version, the commit, where the program was and, if ticked, the output and the screenshot; you get its number back. If the website cannot be reached, nothing is lost: send it later or save it as a file.

**Save report** writes one Markdown file (and the screenshot as `.png`) with the program version, the commit and where the program was (page, project, model, the fit on screen), on this computer only. Run from the source folder, the reports go to `bug_reports/` in the repository: commit and push them with the code when you finish testing. The installed program writes them to `Documents/OpenDEP Compute/bug_reports`: send them to the developers. The **Reports** tab lists the saved reports with their status (open, fixed, wont-fix) and, in **Sent**, their number on the OpenDEP website. Saved several reports without a connection, or before you had an account? **Send selected** (Ctrl or Shift for several) or **Send all unsent** sends them now, with their screenshots and output. The website never stores a report twice: one it already has (the same file, or the same text sent from the form) is only confirmed with its number. After a fix, the developer sets `status: fixed` and `fixed_in: <commit>` in the report's header.
