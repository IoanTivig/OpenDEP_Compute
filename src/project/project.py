"""
OpenDEP Compute projects (Qt-free).

A project is ONE file, <name>.odcproject, made to be copied and sent between users: a zip archive (any unzip tool
opens it) holding
    project.json        name, spectra (with their sample / replicate group), model curves, fits
    spectra/<id>.odspec imported spectra, as OpenDEP Spectrum v2 copies (flags and per-point data included); the
                        original files are never modified
    curves/<id>.json    model curves (from View / Compute 1.x / 3DEP files, the library, or fits)
    fits/<id>.json      saved fits: settings, results, spectra used
Saving writes a temporary file and then replaces the project, so an interrupted save never damages it; the previous
version is kept as <name>.odcproject.bak.

Projects made before 2026-10-09 are folders with the same layout (project.json at the top; older ones list .ods
spectrum copies). They open as before; the first save writes <folder name>.odcproject next to the folder, which is
left as it is. A part that cannot be read (a file deleted by hand, a damaged copy) is reported in Project.problems
and the rest of the project opens.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import uuid
import zipfile

from src.data.spectrum import ImportResult, ModelCurve, Spectrum
from src.formats.opendep_json import SPECTRUM_SUFFIX, read_scatter, scatter_document

PROJECT_SUFFIX = '.odcproject'
PROJECT_FILE = 'project.json'                   # inside the archive (and at the top of an older project folder)
FORMAT_NAME = 'OpenDEP Compute project'
FORMAT_VERSION = 2                              # 2: one file (zip); 1: a folder

## Records ##


@dataclass
class SpectrumEntry:
    """
    A spectrum of the project and its sample (replicates of one sample share the name).
    """
    id: str
    spectrum: Spectrum
    sample: str = ''


@dataclass
class FitRecord:
    """
    A saved fit (plain data, written as JSON).
    """
    id: str
    name: str
    spectra: list[str]                          # spectrum ids
    settings: dict                              # FitSettings fields
    result: dict                                # fit_summary() output
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec='seconds'))


class ProjectError(Exception):
    """A project could not be created or opened."""


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


def _reason(err: Exception) -> str:
    """Short reason a part could not be read."""
    if isinstance(err, KeyError):
        return 'missing from the project'
    if isinstance(err, FileNotFoundError):
        return 'file missing'
    return str(err) or type(err).__name__


## Project ##


class Project:
    """
    An open project: its spectra, curves and saved fits, and the file it is saved in.
    """

    def __init__(self, path: Path, name: str, created: str) -> None:
        self.path = Path(path)                  # the .odcproject file (written at the next save if new / converted)
        self.name = name
        self.created = created
        self.spectra: dict[str, SpectrumEntry] = {}
        self.curves: dict[str, ModelCurve] = {}
        self.fits: dict[str, FitRecord] = {}
        self.problems: list[str] = []           # parts that could not be read when the project was opened
        self.converted_from: Path | None = None   # older project folder this project was opened from

    # -- files --

    @property
    def folder(self) -> Path:
        """The folder holding the project file."""
        return self.path.parent

    @property
    def exchange_dir(self) -> Path:
        """
        Temporary folder for files handed to other programs (Send to View): not inside the project file, and not
        next to it, so nothing is left in the user's folders. One per project.
        """
        key = hashlib.sha1(str(self.path.resolve()).encode()).hexdigest()[:8]
        return Path(tempfile.gettempdir()) / 'OpenDEP Compute' / 'for View' / f'{self.path.stem}-{key}'

    @classmethod
    def create(cls, path: str | Path, name: str = '') -> 'Project':
        """
        Create a project file (.odcproject is added when missing; the folder is made if needed).

        Raises:
            ProjectError: The file exists already.
        """
        path = Path(path)
        if path.suffix.lower() != PROJECT_SUFFIX:
            path = path.with_name(path.name + PROJECT_SUFFIX)
        if path.exists():
            raise ProjectError(f'⚠️ {path} exists already: open it instead')
        path.parent.mkdir(parents=True, exist_ok=True)
        project = cls(path, name or path.stem, datetime.now().isoformat(timespec='seconds'))
        project.save()
        return project

    @classmethod
    def open(cls, path: str | Path) -> 'Project':
        """
        Open a project file (.odcproject), or an older project folder (or its project.json).

        Raises:
            ProjectError: Not a project, or its project.json cannot be read. Unreadable parts do not raise: they
            are listed in Project.problems.
        """
        path = Path(path)
        if path.is_dir() or path.name == PROJECT_FILE:
            folder = path if path.is_dir() else path.parent
            if not (folder / PROJECT_FILE).is_file():
                raise ProjectError(f'⚠️ {folder} is not an {FORMAT_NAME} (no {PROJECT_FILE})')
            return cls._load(lambda name: (folder / name).read_bytes(), folder, converted=True)
        if not path.is_file():
            raise ProjectError(f'⚠️ {path} was not found')
        if not zipfile.is_zipfile(path):
            raise ProjectError(f'⚠️ {path.name} is not an {FORMAT_NAME}')
        with zipfile.ZipFile(path) as archive:
            return cls._load(archive.read, path, converted=False)

    @classmethod
    def _load(cls, read, where: Path, converted: bool) -> 'Project':
        """Build a project from its parts; read(name) returns the bytes of a part ('project.json', 'spectra/…')."""
        try:
            data = json.loads(read(PROJECT_FILE).decode('utf-8'))
        except (OSError, KeyError, ValueError) as e:
            raise ProjectError(f'⚠️ Cannot read the project in {where.name}: {e}') from None
        if data.get('format') != FORMAT_NAME:
            raise ProjectError(f'⚠️ {where.name} is not an {FORMAT_NAME}')
        if converted:                           # an older folder: saved as <folder>.odcproject next to it
            path = where.parent / f'{where.name}{PROJECT_SUFFIX}'
        else:
            path = where
        project = cls(path, data.get('name') or path.stem, data.get('created', ''))
        project.converted_from = where if converted else None

        def part(name: str) -> dict:
            return json.loads(read(name).decode('utf-8'))

        for e in data.get('spectra', []):
            try:
                spectrum = read_scatter(Path(e['file']), part(e['file'])).spectra[0]
                project.spectra[e['id']] = SpectrumEntry(e['id'], spectrum, e.get('sample', ''))
            except Exception as err:            # one damaged or missing part must not block the project
                project.problems.append(f'Spectrum {e.get("file", "?")}: {_reason(err)}')
        for e in data.get('curves', []):
            try:
                project.curves[e['id']] = ModelCurve(**part(e['file']))
            except Exception as err:
                project.problems.append(f'Model curve {e.get("file", "?")}: {_reason(err)}')
        for e in data.get('fits', []):
            try:
                project.fits[e['id']] = FitRecord(**part(e['file']))
            except Exception as err:
                project.problems.append(f'Saved fit {e.get("file", "?")}: {_reason(err)}')
        return project

    def save(self) -> None:
        """
        Write the project file: a temporary archive first, then it replaces the project (the previous version is
        kept as .bak). An older project folder it was opened from is not touched.
        """
        entries, curves, fits = [], [], []
        parts: dict[str, str] = {}
        for sid, e in self.spectra.items():
            name = f'spectra/{sid}{SPECTRUM_SUFFIX}'
            parts[name] = json.dumps(scatter_document(e.spectrum), indent=1, ensure_ascii=False)
            entries.append({'id': sid, 'file': name, 'sample': e.sample})
        for cid, c in self.curves.items():
            name = f'curves/{cid}.json'
            parts[name] = json.dumps(asdict(c), indent=1, ensure_ascii=False)
            curves.append({'id': cid, 'file': name})
        for fid, f in self.fits.items():
            name = f'fits/{fid}.json'
            parts[name] = json.dumps(asdict(f), indent=1, ensure_ascii=False)
            fits.append({'id': fid, 'file': name})
        data = {'format': FORMAT_NAME, 'format_version': FORMAT_VERSION, 'name': self.name, 'created': self.created,
                'saved': datetime.now().isoformat(timespec='seconds'), 'spectra': entries, 'curves': curves,
                'fits': fits}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(PROJECT_FILE, json.dumps(data, indent=1, ensure_ascii=False))
            for name, text in parts.items():
                archive.writestr(name, text)
        if self.path.exists():
            shutil.copy2(self.path, self.path.with_name(self.path.name + '.bak'))
        os.replace(tmp, self.path)
        self.converted_from = None

    # -- content --

    def add_import(self, result: ImportResult, sample: str = '') -> tuple[list[str], list[str]]:
        """
        Add everything read from a file. A saved fit in the file (.odfit) becomes a saved fit of the new spectra.

        Args:
            result (ImportResult): Import result.
            sample (str): Sample / replicate group for its spectra (default: the samples stored in a fit file).

        Returns:
            tuple[list[str], list[str]]: (new spectrum ids, new curve ids).
        """
        # 1. Samples stored with the fit's links, unless one is given
        samples = [sample] * len(result.spectra)
        for fit in result.fits:
            for index, fit_sample in zip(fit['spectra'], fit['samples']):
                samples[index] = sample or fit_sample

        # 2. Spectra and curves
        sids, cids = [], []
        for s, s_sample in zip(result.spectra, samples):
            sid = _new_id()
            self.spectra[sid] = SpectrumEntry(sid, s, s_sample)
            sids.append(sid)
        for c in result.curves:
            cid = _new_id()
            self.curves[cid] = c
            cids.append(cid)

        # 3. Saved fits, pointing to the new spectrum ids
        for fit in result.fits:
            self.add_fit(fit['name'], [sids[i] for i in fit['spectra']], fit['settings'], fit['result'])
        return sids, cids

    def add_curve(self, curve: ModelCurve) -> str:
        cid = _new_id()
        self.curves[cid] = curve
        return cid

    def add_fit(self, name: str, spectra: list[str], settings: dict, result: dict) -> str:
        fid = _new_id()
        self.fits[fid] = FitRecord(fid, name, list(spectra), settings, result)
        return fid

    def samples(self) -> list[str]:
        """
        Sample names in use, sorted.
        """
        return sorted({e.sample for e in self.spectra.values() if e.sample})
