# Installation

OpenDEP Compute runs on **Windows** (installer) and on **Linux and macOS** (from the source code). It needs no internet connection.

## Windows: the installer

1. Download `OpenDEP_Compute_Setup_<version>.exe` from the **Releases** page of the [OpenDEP Compute repository](https://github.com/IoanTivig/OpenDEP_Compute/releases).
2. Run it. It installs the program for the current user (no administrator rights needed), adds it to the Start menu and, if you tick it, to the desktop.
3. Uninstall from Windows Settings → Apps. Your projects are not touched.

Projects are single `.odcproject` files: keep them wherever you like (for example next to your data) and double-click one to open it in OpenDEP Compute.

From the command line (e.g. for several computers): `OpenDEP_Compute_Setup_<version>.exe /VERYSILENT` installs without questions; add `/ALLUSERS` to install for all users (needs administrator rights).

## From the source code (Windows, Linux, macOS)

You need **Python 3.12**.

```
git clone https://github.com/IoanTivig/OpenDEP_Compute
cd OpenDEP_Compute
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt      (Linux, macOS: venv/bin/python)
venv\Scripts\python main.py
```

On Linux, if the program stops with *"could not load the Qt platform plugin xcb"*, install `libxcb-cursor0` (Debian, Ubuntu: `sudo apt install libxcb-cursor0`).

## Next to OpenDEP Compute 1.x

The new version has its own folder and settings; Compute 1.x keeps working (it stays available as the tag `v1.3.5` and the branch `v1` of the repository). Its Excel files (data and fit) open in the new version with **Import…**, and its image sets with **Convert images…**.
