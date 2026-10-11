"""
Send bug reports to the OpenDEP website (tester accounts only; ADR-014).

A tester signs in once with the account the OpenDEP team created for them. The website answers with a device token,
which the program keeps instead of the password. Reports are sent with that token; the website refuses and discards
everything else. The same client, with its own settings block, is in every program of the suite.

Only the standard library is used (urllib), so the installed program needs nothing more. Passwords travel only over
https; plain http is accepted for a local copy of the website (localhost) during development.

No Qt here: the window is ui/bug_report_dialog.py.
"""
import base64
import json
import os
import platform
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from src import __version__
from src.diagnostics import bug_reports

PROGRAM_KEY = 'compute'                 # the website's name for this program
# The OpenDEP website. OPENDEP_BUG_SERVER overrides it (a local copy of the site, tests).
DEFAULT_SERVER = 'https://opendep.org'
TIMEOUT_S = 30
LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')


class UploadError(Exception):
    """The website could not be reached or refused the request; the message is written for the tester."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


## Website address ##


def default_server() -> str:
    return os.environ.get('OPENDEP_BUG_SERVER', DEFAULT_SERVER).strip().rstrip('/')


def check_server(server: str) -> str:
    """
    The website address, normalised; https is required except for a local copy.

    Args:
        server (str): e.g. https://opendep.org

    Returns:
        str: The address without a trailing slash.

    Raises:
        UploadError: Not a web address, or plain http to another computer.
    """
    server = server.strip().rstrip('/')
    parts = urllib.parse.urlsplit(server)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise UploadError('Give the address of the OpenDEP website, e.g. https://opendep.org.')
    if parts.scheme == 'http' and parts.hostname not in LOCAL_HOSTS:
        raise UploadError('The website must be reached over https: your password is sent to it.')
    return server


## Requests ##


def _request(method: str, url: str, data: dict | None = None, token: str = '') -> dict:
    """One JSON request; the website's own error message becomes the UploadError's."""
    request = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data is not None else None,
                                     headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                              'User-Agent': f'OpenDEP-{PROGRAM_KEY}/{__version__}'})
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read() or b'{}').get('error', '')
        except (ValueError, AttributeError):
            message = ''
        raise UploadError(message or f'The website answered with error {error.code}.', error.code) from error
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, 'reason', error)
        raise UploadError(f'The website cannot be reached ({reason}).') from error
    try:
        return json.loads(raw) if raw else {}
    except ValueError as error:
        raise UploadError('The website gave an answer this program does not understand.') from error


def device_name() -> str:
    """How this installation appears in the team's list of tester devices."""
    return f'{bug_reports.PROGRAM} {__version__} on {platform.node() or "this computer"}'


def sign_in(server: str, username: str, password: str) -> str:
    """
    Sign in with a tester account.

    Args:
        server (str): Website address.
        username (str): Tester's user name.
        password (str): Tester's password (sent once, never stored).

    Returns:
        str: The device token to keep.
    """
    answer = _request('POST', f'{check_server(server)}/api/bugs/token',
                      {'username': username, 'password': password, 'device': device_name()})
    token = answer.get('token', '')
    if not token:
        raise UploadError('The website did not return a sign-in token.')
    return token


def sign_out(server: str, token: str) -> None:
    """Revoke the device token on the website (forgotten locally whatever happens)."""
    try:
        _request('DELETE', f'{check_server(server)}/api/bugs/token', token=token)
    except UploadError:
        pass


@dataclass(frozen=True)
class Sent:
    """The website's answer to a report: its number there, and whether it already had it (nothing stored again)."""
    number: int
    duplicate: bool = False


def report_payload(report: dict) -> dict:
    """
    The website's report format from a report of the Report Bug window, or one read back from its file.

    Args:
        report (dict): title, steps, expected, actual, error, output, context, screenshot_png (as for save_report);
            from a saved file also id, version, commit and system (those of the program that saved it).

    Returns:
        dict: JSON-ready report.
    """
    payload = {
        'program': PROGRAM_KEY,
        'client_id': report.get('id', ''),
        'version': report.get('version') or __version__,
        'commit': report.get('commit') or bug_reports.git_commit(),
        'title': report.get('title', '').strip(),
        'steps': report.get('steps', ''),
        'expected': report.get('expected', ''),
        'actual': report.get('actual', ''),
        'error': report.get('error', ''),
        'log': report.get('output', ''),
        'context': {str(k): str(v) for k, v in report.get('context', {}).items()},
        'system': report.get('system') or bug_reports.system_info(),
    }
    if report.get('screenshot_png'):
        payload['screenshot'] = base64.b64encode(report['screenshot_png']).decode('ascii')
    return payload


def send_report(server: str, token: str, report: dict) -> Sent:
    """
    Send one report. The website keeps no copy of a report it already has (the same saved file, or the same text):
    it answers with the existing number and duplicate=True.

    Args:
        server (str): Website address.
        token (str): Device token from sign_in.
        report (dict): As for save_report (or load_report).

    Returns:
        Sent: The report's number on the website, and whether it was already there.
    """
    answer = _request('POST', f'{check_server(server)}/api/bugs/reports', report_payload(report), token=token)
    return Sent(int(answer.get('id', 0)), bool(answer.get('duplicate')))


def send_saved(server: str, token: str, paths: list[Path]) -> list[dict]:
    """
    Send saved reports one after the other; each one sent (or found on the website) gets its number in its header.

    Stops at a refusal that would repeat for the rest (sign-in needed, not allowed, too many reports).

    Args:
        server (str): Website address.
        token (str): Device token from sign_in.
        paths (list[Path]): Report files.

    Returns:
        list[dict]: Per report: path, title, number, duplicate, error ('' when sent), status (HTTP, 0 without one).
    """
    results = []
    for path in paths:
        result = {'path': Path(path), 'title': Path(path).stem, 'number': 0, 'duplicate': False, 'error': '',
                  'status': 0}
        try:
            report = bug_reports.load_report(path)
            result['title'] = report['title'] or result['title']
            sent = send_report(server, token, report)
            bug_reports.mark_sent(path, sent.number)
            result.update(number=sent.number, duplicate=sent.duplicate)
        except UploadError as e:
            result.update(error=str(e), status=e.status)
            results.append(result)
            if e.status in (401, 403, 429):
                break
            continue
        except (OSError, ValueError) as e:
            result['error'] = f'cannot read the file ({e})'
        results.append(result)
    return results


def summary(results: list[dict]) -> str:
    """'3 sent, 1 already on the website, 1 not sent: <reason>'."""
    new = sum(1 for r in results if r['number'] and not r['duplicate'])
    old = sum(1 for r in results if r['duplicate'])
    failed = [r for r in results if r['error']]
    parts = [f'{new} sent'] + ([f'{old} already on the website'] if old else [])
    if failed:
        parts.append(f'{len(failed)} not sent: {failed[-1]["error"]}')
    return ', '.join(parts) + '.'


def my_reports(server: str, token: str) -> list[dict]:
    """The reports this tester sent, newest first, with their status on the website."""
    return list(_request('GET', f'{check_server(server)}/api/bugs/reports', token=token).get('reports', []))
