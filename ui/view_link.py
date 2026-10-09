"""
Send to View, the Qt end: the local socket to a running OpenDEP View, or starting View with the files.

What is not Qt (message, channel name, finding View) is in src/integration/view_link.py.
"""
from pathlib import Path
import subprocess
import sys

from PyQt6.QtNetwork import QLocalSocket
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from src.integration.view_link import (SETTING_KEY, channel_name, encode_message, find_view, installation_at,
                                       is_acknowledged, launch_command)
from ui.context import AppContext

TIMEOUT_MS = 2000
COMPUTE_FOLDER = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]


def view_folder(ctx: AppContext) -> Path:
    """
    Folder of the files sent to View: a temporary folder of the project (Project.exchange_dir); View copies what
    it opens into its own project, and the files stay readable if it opens them later.

    Args:
        ctx (AppContext): Context with the open project.

    Returns:
        Path: The folder (created).
    """
    folder = ctx.project.exchange_dir
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def send_to_running_view(paths: list[Path], timeout_ms: int = TIMEOUT_MS) -> bool:
    """
    Hand files to the user's running View.

    Args:
        paths (list[Path]): Files.
        timeout_ms (int): Time allowed for each step.

    Returns:
        bool: True when a running View confirmed them.
    """
    socket = QLocalSocket()
    socket.connectToServer(channel_name())
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(encode_message(paths))
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)      # False when flush() already wrote everything: only the answer counts
    reply = bytes(socket.readAll()) if socket.waitForReadyRead(timeout_ms) else b''
    socket.disconnectFromServer()
    return is_acknowledged(reply)


def _allow_view_in_front() -> None:
    """Windows only lets the program in front pass the focus on: allow View to come forward."""
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)        # ASFW_ANY


def _start_view(command: list[str], folder: Path) -> None:
    """Start View on its own (it stays open when Compute closes)."""
    if sys.platform == 'win32':
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(command, cwd=str(folder), creationflags=flags, close_fds=True)
    else:
        subprocess.Popen(command, cwd=str(folder), start_new_session=True, close_fds=True)


def send_to_view(ctx: AppContext, paths: list[Path], parent: QWidget | None = None) -> str:
    """
    Send files to OpenDEP View: to the running View, else start View with them.

    Args:
        ctx (AppContext): Context (settings: where View is).
        paths (list[Path]): Files (.odfit, .odspec).
        parent (QWidget | None): Parent of the questions.

    Returns:
        str: "sent" (running View), "started" (View started with the files) or "" (View not found, nothing done).
    """
    _allow_view_in_front()
    if send_to_running_view(paths):
        ctx.message.emit(f'🆕 {len(paths)} file(s) sent to OpenDEP View')
        return 'sent'

    # 1. View is not running: start it, from the saved place, the usual places, or one the user shows
    installation = find_view(ctx.settings.value(SETTING_KEY, '') or None, COMPUTE_FOLDER)
    if installation is None:
        QMessageBox.information(parent, 'Send to View', 'OpenDEP View was not found next to OpenDEP Compute. '
                                'Show its folder once (the folder with the program, or main.py and ui/); it is '
                                'remembered.')
        folder = QFileDialog.getExistingDirectory(parent, 'OpenDEP View folder')
        installation = installation_at(folder) if folder else None
        if installation is None:
            if folder:
                QMessageBox.warning(parent, 'Send to View', f'No OpenDEP View in {folder}: it needs the program '
                                    '(or main.py with its venv) and the ui folder.')
            return ''
    ctx.settings.setValue(SETTING_KEY, str(installation.folder))

    # 2. Start it with the files: View opens them itself (and asks for a project when none is open)
    try:
        _start_view(launch_command(installation, paths), installation.folder)
    except OSError as e:
        QMessageBox.warning(parent, 'Send to View', f'OpenDEP View could not be started:\n{e}')
        return ''
    ctx.message.emit(f'🆕 OpenDEP View started with {len(paths)} file(s)')
    return 'started'
