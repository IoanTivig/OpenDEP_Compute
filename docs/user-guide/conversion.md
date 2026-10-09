# Converting images

**Convert images…** on the [Data page](workflow.md#data) turns population image sets into spectra. An image set is a folder with a `_DATA` subfolder (one image per frequency at the end of the exposure, named `..._<frequency>Hz.jpg/png/tif`) and, optionally, `_BKG` (just before the field goes on): the folders OpenDEP Control writes, and the layout of OpenDEP Compute 1.x. Choose one experiment folder or a folder holding several; every set found is listed.

- **Grid**: for a Control run, its own grid is used (from `experiment_parameters.csv`), with its edge width, background width and region. Otherwise lines are detected on an `Edges` image without cells (as in Compute 1.x) or suggested from the profile averaged over all images. **Check the lines on the image** (or on the profile below it): **drag** a line to move it, left click elsewhere adds a line, right click removes the nearest one. With **Snap to edges** (on by default) new and moved lines jump to the nearest edge of the profile; untick it to place a line exactly where you release it, for example when the profile is noisy. **Detect lines again** replaces the lines by detected ones (from the edges image, or the averaged images). Regions between consecutive lines alternate electrode / gap (shaded: electrodes); **Electrodes** switches which.
- **Light**: bright-field (cells darker than the medium; the sign is inverted so that cells collecting at the edges give positive values) or fluorescence (cells brighter).
- **Convert ticked sets** adds a **Grayness factor** spectrum per set, computed exactly as OpenDEP Control computes it on the final frame (its spread over the lines is the error), and, when there are background images, a **Grayness factor (image − background)** spectrum, in which the static electrode pattern cancels. The sample name is the folder above the experiment.

The DEP rate needs Control's frame series and is not computed from images; Control's own "Grayness Factor (ref)" averages the frames of the last second, of which only the final one is saved, so it is not reproduced either: import `experiment_parameters.csv` for those.

## Example

A Control experiment folder looks like this; choose `Sample_01` (or the date folder) to convert all its experiments at once:

```
2026 10 05/Frequency Spectrum/Sample_01/
    Experiment_01/
        _BKG/OpenDEP_5000Hz.jpg ...
        _DATA/OpenDEP_5000Hz.jpg ...
        experiment_parameters.csv
    Experiment_02/ ...
```

The grayness factors computed here agree with the ones Control wrote in `experiment_parameters.csv` within 0.003 (Control measured the frame before it was saved as JPEG).
