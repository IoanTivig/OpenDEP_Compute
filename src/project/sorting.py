"""
Order of the project's lists (Qt-free): the spectra (Data page and the Fit page's Spectra, one order for both) and
the memorized fits (Fit page).

Names are compared as people read them: case ignored, numbers by value ("Exp 2" before "Exp 10"). Equal keys keep
the order the items were added in.
"""
import re

from src.project.project import Project

## Orders ##

# key -> label, in the order the sort lists show them; the first is the default (the order things were added in)
SPECTRA_SORTS = {
    'added': 'Import order',
    'name': 'Name A–Z',
    'name_desc': 'Name Z–A',
    'sample': 'Sample A–Z',
    'sample_desc': 'Sample Z–A',
}
FIT_SORTS = {
    'added': 'Oldest first',
    'newest': 'Newest first',
    'name': 'Name A–Z',
    'name_desc': 'Name Z–A',
}


def natural_key(text: str) -> list[tuple[int, int, str]]:
    """
    Sort key of a name: case ignored, numbers by value.

    Args:
        text (str): The name.

    Returns:
        list[tuple[int, int, str]]: Key; "Exp 2" sorts before "Exp 10", "b" after "A".
    """
    return [(0, int(part), '') if part.isdigit() else (1, 0, part.casefold())
            for part in re.split(r'(\d+)', text or '') if part]


def spectra_order(project: Project, sort: str) -> list[str]:
    """
    The project's spectrum ids in the chosen order.

    Args:
        project (Project): The open project.
        sort (str): A key of SPECTRA_SORTS ('sample': by sample, then by name within it; spectra without a sample
            last). Unknown keys keep the import order.

    Returns:
        list[str]: Spectrum ids.
    """
    ids = list(project.spectra)
    name = lambda sid: natural_key(project.spectra[sid].spectrum.name)
    if sort in ('name', 'name_desc'):
        return sorted(ids, key=name, reverse=sort == 'name_desc')
    if sort in ('sample', 'sample_desc'):
        # 1. Spectra with a sample, grouped by it (A–Z or Z–A), names A–Z inside a sample; 2. those without one
        with_sample = [sid for sid in ids if project.spectra[sid].sample]
        without = [sid for sid in ids if not project.spectra[sid].sample]
        groups = sorted({project.spectra[sid].sample for sid in with_sample}, key=natural_key,
                        reverse=sort == 'sample_desc')
        ordered = [sid for group in groups
                   for sid in sorted((s for s in with_sample if project.spectra[s].sample == group), key=name)]
        return ordered + sorted(without, key=name)
    return ids


def fit_order(project: Project, sort: str) -> list[str]:
    """
    The project's memorized fit ids in the chosen order.

    Args:
        project (Project): The open project.
        sort (str): A key of FIT_SORTS ('added' / 'newest': by the time each fit was memorized). Unknown keys keep
            the order they were memorized in.

    Returns:
        list[str]: Fit ids.
    """
    ids = list(project.fits)
    if sort in ('name', 'name_desc'):
        return sorted(ids, key=lambda fid: natural_key(project.fits[fid].name), reverse=sort == 'name_desc')
    if sort in ('added', 'newest'):
        return sorted(ids, key=lambda fid: project.fits[fid].created, reverse=sort == 'newest')
    return ids
