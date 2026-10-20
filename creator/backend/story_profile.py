"""Presentation defaults only; never rename labels or alter runtime sources."""
import json
from pathlib import Path, PurePosixPath
import re

PROFILE = json.loads(Path(__file__).with_name('morinote_story.json').read_text('utf-8'))


def scene_info(project, label):
    labels = project.get('nativeRenpy', {}).get('labels', [])
    names = {i['name'] for i in labels}
    if not set(PROFILE['signature']).issubset(names): return {}
    entry = PROFILE['scenes'].get(label['name'], {})
    return entry if PurePosixPath(label['file'].replace('\\', '/')).name == entry.get('file') else {}


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
