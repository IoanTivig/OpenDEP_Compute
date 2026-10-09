# OpenDEP Compute

OpenDEP Compute turns dielectrophoresis (DEP) measurements into cell properties. It imports DEP spectra from every OpenDEP program and from 3DEP, fits them with dielectric particle models (homogeneous sphere, single-, two-, three- and four-shell), and reports the fitted parameters with their uncertainty, the crossover frequencies, publication figures and PDF reports.

It is part of the OpenDEP suite (Tivig et al., *ACS Omega* 8 (2023) 38715–38722):

| Program | Does |
|---|---|
| OpenDEP Control | runs the experiments (camera, generator, pump) and measures DEP spectra |
| **OpenDEP Compute** | converts image sets, fits spectra, reports cell parameters |
| OpenDEP View | compares spectra and model curves, synthetic data, figures |
## Where to start

- [Installation](installation.md)
- [Quick start](quickstart.md): from a Control experiment to fitted membrane and cytoplasm values in a few minutes
- [Projects, data and fitting](user-guide/workflow.md), [Converting images](user-guide/conversion.md), [Figures and reports](user-guide/reports.md), [File formats](user-guide/file-formats.md)
- The physics: [Dielectric models](concepts/models.md) and [Fitting](concepts/fitting.md)

Press **F1** anywhere in the program to open the page of what you are doing.

## Licence

GNU General Public License v3.0. The published parameter sets come from the MyDEP 1.0.1 database (MIT licence; see [Dielectric models](concepts/models.md#published-parameter-sets)).
