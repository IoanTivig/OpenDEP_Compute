"""
Send to View: hand files (.odfit, .odspec) to OpenDEP View, which adds them to its open project.

A running View listens on a local channel (a named pipe on Windows, a socket file on Linux and macOS; nothing leaves
the computer), one per user. Compute sends the files there; without a running View it starts View with the files as
arguments, and View opens them itself. The Qt end (QLocalSocket) is ui/view_link.py; this module holds what is not Qt:
the message, the channel name, finding View and the command that starts it.

Protocol (the same as OpenDEP View's src/classes/instance_link.py; change both together): one line of UTF-8 JSON
    {"open": ["<absolute path>", ...], "version": 1}\\n
answered by the line
    {"ok": true}\\n
"""
from dataclasses import dataclass
from pathlib import Path
import getpass
import json
import os
import re
import sys

PROTOCOL_VERSION = 1
CHANNEL_PREFIX = 'OpenDEP-View-'
CHANNEL_VARIABLE = 'OPENDEP_VIEW_CHANNEL'        # replaces the channel name (tests)
SETTING_KEY = 'view_location'                    # QSettings key: View's folder, chosen by the user
# A file every View folder has: ui/main.ui in the source and in releases built with PyInstaller < 6; the installed
# View (PyInstaller >= 6) keeps its data in _internal/ next to the program (bug report #2, 2026-10-12)
VIEW_MARKERS = (Path('ui') / 'main.ui', Path('_internal') / 'ui' / 'main.ui')
FROZEN_NAMES = ('OpenDEP View', 'main')          # View's program file in a release, without the extension


## Message ##

def channel_name() -> str:
    """
    Name of the local channel of the user's View.

    Returns:
        str: "OpenDEP-View-<user>", or the value of OPENDEP_VIEW_CHANNEL when it is set.
    """
    if os.environ.get(CHANNEL_VARIABLE):
        return os.environ[CHANNEL_VARIABLE]
    try:
        user = getpass.getuser()
    except Exception:                            # no user name available: one channel for the computer
        user = 'user'
    return CHANNEL_PREFIX + (re.sub(r'[^A-Za-z0-9_-]', '_', user) or 'user')


def encode_message(paths: list[Path | str]) -> bytes:
    """
    Message asking View to open files.

    Args:
        paths (list[Path | str]): Files (made absolute).

    Returns:
        bytes: One JSON line.
    """
    files = [str(Path(p).resolve()) for p in paths]
    return (json.dumps({'open': files, 'version': PROTOCOL_VERSION}) + '\n').encode('utf-8')


def is_acknowledged(reply: bytes) -> bool:
    """
    Args:
        reply (bytes): What View answered.

    Returns:
        bool: True when View confirmed the message.
    """
    for line in reply.splitlines():
        try:
            if json.loads(line.decode('utf-8')).get('ok') is True:
                return True
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            continue
    return False


## Finding View ##

@dataclass
class ViewInstallation:
    """
    Where OpenDEP View is and how to start it.

    Attributes:
        folder (Path): View's folder (it must run from there: it reads ui/ and docs/ relative to it).
        command (list[str]): Program and arguments before the files.
    """
    folder: Path
    command: list[str]


def installation_at(path: Path | str | None) -> ViewInstallation | None:
    """
    View at a folder (or at its program file): a release (OpenDEP View.exe / main.exe, its data in _internal/ when
    installed) or the source with its venv.

    Args:
        path (Path | str | None): View's folder, its program or main.py.

    Returns:
        ViewInstallation | None: None when no View is there.
    """
    if not path:
        return None
    path = Path(path)
    folder = path if path.is_dir() else path.parent
    if not any((folder / marker).is_file() for marker in VIEW_MARKERS):
        return None
    # 1. Release: the frozen program
    suffix = '.exe' if sys.platform == 'win32' else ''
    for name in FROZEN_NAMES:
        program = folder / f'{name}{suffix}'
        if program.is_file():
            return ViewInstallation(folder, [str(program)])
    # 2. Source: main.py with View's own environment (its packages differ from Compute's); pythonw on Windows, so
    #    no console window opens
    if (folder / 'main.py').is_file():
        candidates = (folder / 'venv' / 'Scripts' / 'pythonw.exe', folder / 'venv' / 'Scripts' / 'python.exe') \
            if sys.platform == 'win32' else (folder / 'venv' / 'bin' / 'python3', folder / 'venv' / 'bin' / 'python')
        for python in candidates:
            if python.is_file():
                return ViewInstallation(folder, [str(python), str(folder / 'main.py')])
    return None


def candidate_folders(compute_folder: Path) -> list[Path]:
    """
    Where View usually is: next to Compute (installed side by side, or the source folders of the suite), then the
    standard program folders.

    Args:
        compute_folder (Path): Compute's own folder.

    Returns:
        list[Path]: Folders to look in, in order.
    """
    parent = Path(compute_folder).resolve().parent
    folders = [parent / 'OpenDEP View', parent / 'OpenDEP_View']
    if sys.platform == 'win32':
        for variable in ('LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)'):
            base = os.environ.get(variable)
            if base:
                folders += [Path(base) / 'Programs' / 'OpenDEP View', Path(base) / 'OpenDEP View']
    else:
        folders += [Path.home() / '.local' / 'share' / 'OpenDEP View', Path('/opt/OpenDEP View'),
                    Path('/opt/opendep-view')]
    return folders


def find_view(setting: str | None, compute_folder: Path) -> ViewInstallation | None:
    """
    OpenDEP View: the folder the user chose (setting), else the usual places.

    Args:
        setting (str | None): Saved location (SETTING_KEY).
        compute_folder (Path): Compute's own folder.

    Returns:
        ViewInstallation | None: None when View was not found.
    """
    for folder in ([Path(setting)] if setting else []) + candidate_folders(compute_folder):
        installation = installation_at(folder)
        if installation is not None:
            return installation
    return None


def launch_command(installation: ViewInstallation, paths: list[Path | str]) -> list[str]:
    """
    Command that starts View with files (run it in installation.folder).

    Args:
        installation (ViewInstallation): View.
        paths (list[Path | str]): Files to open.

    Returns:
        list[str]: Program and arguments.
    """
    return installation.command + [str(Path(p).resolve()) for p in paths]
