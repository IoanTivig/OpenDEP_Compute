# OpenDEP Compute

**Turns dielectrophoresis (DEP) measurements into cell properties.** OpenDEP Compute imports DEP spectra from every OpenDEP program and from 3DEP, fits them with dielectric particle models, and reports the fitted membrane, cytoplasm and other parameters with their uncertainty, the crossover frequencies, publication figures and PDF reports.

It is part of the **OpenDEP** suite, free and open-source software for DEP research:

| Program | What it does |
|---|---|
| [OpenDEP Control](https://github.com/IoanTivig/OpenDEP_Control) | runs the experiments on a Raspberry Pi (camera, function generator, pump) and measures DEP spectra |
| **OpenDEP Compute** | converts image sets into spectra, fits spectra, reports cell parameters |
| [OpenDEP View](https://github.com/IoanTivig/OpenDEP_View) | compares spectra and model curves, averages replicates, simulates data, publication graphs |
| [OpenDEP Neuralnet](https://github.com/IoanTivig/OpenDEP_Neuralnet) | classifies DEP population images |

## Features

- **Import** spectra from OpenDEP Control, OpenDEP View, OpenDEP Compute 1.x (Excel) and 3DEP (`.csv`); disabled and outlier points are kept.
- **Convert image sets** into spectra with OpenDEP Control's grayness-factor algorithm (bright-field and fluorescence), with a draggable electrode grid.
- **Models:** homogeneous sphere and single-, two-, three- and four-shell particles, validated against MyDEP 1.0.1 to 1e-10; published parameter sets from the MyDEP database.
- **Fitting** of one or many spectra (replicates) with a free scale factor per spectrum, error weighting, multi-start, standard errors, flags for parameters the data cannot determine, crossover frequencies and R².
- **Outlier suggestions** judged from neighbouring points, independent of the model.
- **Results** grouped as membrane, cytoplasm, cell wall, nucleus…; publication figures (PNG, TIFF, SVG, PDF at journal sizes), PDF fit reports, CSV tables.
- **Projects** as single `.odcproject` files, easy to send to a colleague; **Saved fits** keep every fit of a project, ready to export together.
- **Send to View:** the selected spectra or fits open in OpenDEP View with one click. Files shared by the suite: `.odspec` (spectrum), `.odcurve` (model curve), `.odfit` (fit).
- **User guide** inside the program (**F1**) and a **Report bug** form.

## Installation

**Windows:** download `OpenDEP_Compute_Setup_<version>.exe` from the [Releases](https://github.com/IoanTivig/OpenDEP_Compute/releases) page and run it (no administrator rights needed). It registers `.odcproject` files, so a double-click opens a project.

**From the source code** (Windows, Linux, macOS; Python 3.12):

```
git clone https://github.com/IoanTivig/OpenDEP_Compute
cd OpenDEP_Compute
python -m venv venv
venv/bin/python -m pip install -r requirements.txt        (Windows: venv\Scripts\python)
venv/bin/python main.py
```

Details, including a Linux note: [Installation](docs/installation.md). Then the [Quick start](docs/quickstart.md): from a Control experiment to fitted membrane and cytoplasm values in a few minutes.

## Documentation

The user guide is in [docs/](docs/index.md) and inside the program (F1): [projects, data and fitting](docs/user-guide/workflow.md), [converting images](docs/user-guide/conversion.md), [figures and reports](docs/user-guide/reports.md), [file formats](docs/user-guide/file-formats.md), the [dielectric models](docs/concepts/models.md) and [how fitting works](docs/concepts/fitting.md). What is new: [Changes](docs/changelog.md).

## Earlier version

OpenDEP Compute 1.x (PyQt5) stays available as the tag [`v1.3.5`](https://github.com/IoanTivig/OpenDEP_Compute/tree/v1.3.5) and the branch [`v1`](https://github.com/IoanTivig/OpenDEP_Compute/tree/v1). Its Excel exports and image sets open in version 2.

## Citation

If you use OpenDEP in your research, please cite:

> Tivig I., et al. *OpenDEP: An Open-Source Platform for Dielectrophoresis Spectra Acquisition and Analysis.* ACS Omega 8 (2023) 38715–38722. [doi:10.1021/acsomega.3c06052](https://pubs.acs.org/doi/10.1021/acsomega.3c06052)

Work using OpenDEP:

- [Early differentiation of mesenchymal stem cells is reflected in their dielectrophoretic behavior](https://www.nature.com/articles/s41598-024-54350-z), *Scientific Reports* (2024)
- [Dielectrophoretic characterization of peroxidized retinal pigment epithelial cells as a model of age-related macular degeneration](https://bmcophthalmol.biomedcentral.com/articles/10.1186/s12886-024-03617-0), *BMC Ophthalmology* (2024)

## License

GNU General Public License v3.0 (see [LICENSE](LICENSE)). The published parameter sets come from the MyDEP 1.0.1 database (MIT licence; see [Dielectric models](docs/concepts/models.md#published-parameter-sets)).
