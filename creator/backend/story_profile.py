"""Shared IDE version and presentation defaults; never rewrite runtime sources."""
import json
from pathlib import Path, PurePosixPath
import re

PROFILE = json.loads(Path(__file__).with_name('morinote_story.json').read_text('utf-8'))


def canonical_file(filename):
    return re.sub(r' \(\d+\)(\.rpy)$', r'\1', filename.replace('\\', '/'), flags=re.I)


def preferred_files(files):
    winners = {}
    for file in files:
        key = canonical_file(file)
        if key not in winners or file.rsplit('.', 1)[0] > winners[key].rsplit('.', 1)[0]:
            winners[key] = file
    return list(winners.values())


def preferred_labels(project):
    """Prefer numbered siblings per label, following Ren'Py's stem sort order."""
    labels = project.get('nativeRenpy', {}).get('labels', [])
    winners = {}
    for label in labels:
        file = label['file'].replace('\\', '/')
        key = (canonical_file(file), label['name'])
        previous = winners.get(key)
        if previous is None or file[:-4] > previous['file'].replace('\\', '/')[:-4]:
            winners[key] = label
    return [label for label in labels if winners[(canonical_file(label['file']), label['name'])]['file'] == label['file']]


def scene_info(project, label):
    labels = project.get('nativeRenpy', {}).get('labels', [])
    names = {i['name'] for i in labels}
    if not set(PROFILE['signature']).issubset(names): return {}
    entry = PROFILE['scenes'].get(label['name'], {})
    return entry if PurePosixPath(canonical_file(label['file'])).name == entry.get('file') else {}


def numbered_copies(project):
    files = {i['file'].replace('\\', '/') for i in project.get('nativeRenpy', {}).get('labels', [])}
    result = {}
    for name in files:
        path = PurePosixPath(name)
        match = re.fullmatch(r'(.+) \(\d+\)(\.rpy)', path.name, re.I)
        if match:
            original = str(path.with_name(match[1]+match[2]))
            if original in files: result[name] = original
    return result
