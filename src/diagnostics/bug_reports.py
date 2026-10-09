"""
Bug reports, in the format of OpenDEP Control and OpenDEP View.

Each report is one Markdown file with a small YAML header (status, commit, context, ...) followed by the tester's
description, the last error and the recent console / log output; a screenshot is saved next to it as .png. Nothing is
sent anywhere. From source the reports go to bug_reports/ in the repository, so testers commit and push them with the
code; the installed program cannot write to its own folder (Program Files) and uses Documents/OpenDEP Compute/
bug_reports instead. After a fix, set "status" to "fixed" and "fixed_in" to the commit.

No Qt here: the window is ui/bug_report_dialog.py.
"""
import collections
import json
import logging
import platform
import re
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

from src import __version__

PROGRAM = 'OpenDEP Compute'
SOURCE_FOLDER = Path(__file__).resolve().parents[2]
REPORTS_FOLDER = (Path.home() / 'Documents' / PROGRAM / 'bug_reports' if getattr(sys, 'frozen', False)
                  else SOURCE_FOLDER / 'bug_reports')
STATUSES = ('open', 'fixed', 'wont-fix')
LOG_LINES = 200
FRONT_MATTER = re.compile(r'\A---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)

logger = logging.getLogger(__name__)


## Recent output ##


class OutputBuffer:
    """
    The last lines written to the console (print, warnings, tracebacks) and to the log, with their time.
    """

    def __init__(self, capacity: int = LOG_LINES) -> None:
        self.lines: collections.deque[str] = collections.deque(maxlen=capacity)
        self.partial = ''
        self.lock = threading.Lock()                    # written from worker threads too

    def add_text(self, text: str) -> None:
        with self.lock:
            text = self.partial + text
            *complete, self.partial = text.split('\n')
            stamp = datetime.now().strftime('%H:%M:%S')
            for line in complete:
                if line.strip():
                    self.lines.append(f'{stamp} {line}')

    def text(self) -> str:
        with self.lock:
            return '\n'.join(list(self.lines) + ([self.partial] if self.partial.strip() else []))


class TeeStream:
    """
    A stream that copies everything written to it into the buffer (stdout / stderr).
    """

    def __init__(self, stream, buffer: OutputBuffer) -> None:
        self.stream = stream
        self.buffer = buffer

    def write(self, text: str) -> int:
        self.buffer.add_text(text)
        if self.stream is not None:                     # None in a windowed (frozen) program
            try:
                return self.stream.write(text)
            except Exception:                           # a broken console must never break the program
                pass
        return len(text)

    def flush(self) -> None:
        if self.stream is not None:
            try:
                self.stream.flush()
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self.stream, name)


class BufferHandler(logging.Handler):
    """Log records into the buffer."""

    def __init__(self, buffer: OutputBuffer) -> None:
        super().__init__()
        self.buffer = buffer
        self.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.add_text(self.format(record) + '\n')
        except Exception:
            pass


_output_buffer: OutputBuffer | None = None
_last_error = ''


def install_output_buffer() -> OutputBuffer:
    """Keep the console output and the log records for the reports (call once, at start)."""
    global _output_buffer
    if _output_buffer is None:
        _output_buffer = OutputBuffer()
        sys.stdout = TeeStream(sys.stdout, _output_buffer)
        sys.stderr = TeeStream(sys.stderr, _output_buffer)
        logging.getLogger().addHandler(BufferHandler(_output_buffer))
    return _output_buffer


def recent_output() -> str:
    return _output_buffer.text() if _output_buffer is not None else ''


def record_error(exc_type, exc_value, exc_tb) -> str:
    """Remember the traceback of an unhandled error for the next report; returns it as text."""
    global _last_error
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _last_error = f'[{stamp}]\n' + ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    return _last_error


def last_error() -> str:
    return _last_error


## Report files ##


def git_commit(folder: Path = SOURCE_FOLDER) -> str:
    """Short commit of the working copy, '+ local changes' when modified; the version when there is no git."""
    try:
        commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=folder, capture_output=True, text=True,
                                timeout=5).stdout.strip()
        if not commit:
            return f'version {__version__} (no git)'
        dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=folder,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return f'{commit} + local changes' if dirty else commit
    except (OSError, subprocess.SubprocessError):
        return f'version {__version__} (no git)'


def system_info() -> dict[str, str]:
    info = {'version': __version__, 'os': f'{platform.system()} {platform.release()} ({platform.machine()})',
            'python': platform.python_version()}
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
        info['qt'] = f'Qt {QT_VERSION_STR}, PyQt {PYQT_VERSION_STR}'
    except ImportError:
        pass
    for name in ('numpy', 'scipy', 'lmfit', 'matplotlib'):
        module = sys.modules.get(name)
        if module is not None:
            info[name] = str(getattr(module, '__version__', '?'))
    return info


def slug(title: str, length: int = 40) -> str:
    """File-name-safe short version of a title."""
    text = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return text[:length].rstrip('-') or 'report'


def code_block(text: str) -> str:
    """Fenced code block that survives backticks inside the text."""
    fence = '````' if '```' in text else '```'
    return f'{fence}text\n{text.rstrip()}\n{fence}'


def header_lines(header: dict) -> list[str]:
    """YAML header lines: strings written as JSON strings (valid YAML), one level of nesting."""
    lines = []
    for key, value in header.items():
        if isinstance(value, dict):
            lines.append(f'{key}:' if value else f'{key}: {{}}')
            lines += [f'  {k}: {json.dumps(str(v), ensure_ascii=False)}' for k, v in value.items()]
        else:
            lines.append(f'{key}: {json.dumps(str(value), ensure_ascii=False)}')
    return lines


def save_report(report: dict, folder: str | Path = REPORTS_FOLDER, now: datetime | None = None) -> Path:
    """
    Save a report as <date>_<time>_<title>.md (and .png).

    Args:
        report (dict): title, steps, expected, actual, error, output, context (dict), screenshot_png (bytes | None).
        folder (str | Path): Reports folder.
        now (datetime | None): Time of the report (tests).

    Returns:
        Path: The report file.
    """
    now = now or datetime.now()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f'{now:%Y-%m-%d_%H%M%S}_{slug(report["title"])}'
    path = folder / f'{stem}.md'
    n = 2
    while path.exists():
        path = folder / f'{stem}-{n}.md'
        n += 1

    header = {'id': path.stem, 'status': 'open', 'title': report['title'].strip(), 'program': PROGRAM,
              'commit': git_commit(), 'date': f'{now:%Y-%m-%d %H:%M:%S}', **system_info(),
              'context': report.get('context', {}), 'fixed_in': ''}
    parts = ['---', *header_lines(header), '---', '', f'# {report["title"].strip()}', '']
    for heading, key in (('What I did', 'steps'), ('What I expected', 'expected'),
                         ('What happened instead', 'actual')):
        parts += [f'## {heading}', '', report.get(key, '').strip() or '_(not given)_', '']
    if report.get('error', '').strip():
        parts += ['## Error', '', code_block(report['error']), '']
    if report.get('screenshot_png'):
        png = path.with_suffix('.png')
        png.write_bytes(report['screenshot_png'])
        parts += ['## Screenshot', '', f'![screenshot]({png.name})', '']
    if report.get('output', '').strip():
        output = '\n'.join(report['output'].splitlines()[-LOG_LINES:])
        parts += [f'## Console and log (last {LOG_LINES} lines)', '', code_block(output), '']
    path.write_text('\n'.join(parts), encoding='utf-8')
    logger.info('Bug report saved: %s', path)
    return path


def read_header(path: str | Path) -> dict:
    """Top-level values of a report header ({} when missing); also reads headers written by PyYAML."""
    try:
        match = FRONT_MATTER.match(Path(path).read_text(encoding='utf-8'))
    except OSError:
        return {}
    if not match:
        return {}
    header = {}
    for line in match.group(1).splitlines():
        if line.startswith((' ', '\t')) or ':' not in line:
            continue
        key, value = line.split(':', 1)
        value = value.strip()
        try:
            value = json.loads(value) if value.startswith('"') else value.strip("'")
        except ValueError:
            pass
        header[key.strip()] = value
    return header


def list_reports(folder: str | Path = REPORTS_FOLDER) -> list[dict]:
    """All saved reports, newest first: [{path, id, title, status, date}]."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    entries = []
    for path in folder.glob('*.md'):
        header = read_header(path)
        if header:
            entries.append({'path': path, 'id': str(header.get('id', path.stem)),
                            'title': str(header.get('title', path.stem)),
                            'status': str(header.get('status', 'open')), 'date': str(header.get('date', ''))})
    return sorted(entries, key=lambda e: e['id'], reverse=True)
