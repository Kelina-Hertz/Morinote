"""Line-based three-way merge. Only overlapping edits require a choice."""
from difflib import SequenceMatcher


def merge(base, local, disk):
    if any(not isinstance(s, str) or len(s.encode('utf-8')) > 4*1024*1024 for s in (base, local, disk)):
        raise ValueError('合并内容必须为不超过 4 MiB 的文本。')
    normalize = lambda s: s.replace('\r\n', '\n').replace('\r', '\n').splitlines(keepends=True)
    original, ours, theirs = map(normalize, (base, local, disk))
    changes = []
    for side, lines in (('local', ours), ('disk', theirs)):
        for tag, a, b, c, d in SequenceMatcher(None, original, lines).get_opcodes():
            if tag != 'equal': changes.append({'side': side, 'a': a, 'b': b, 'text': lines[c:d]})
    changes.sort(key=lambda c: (c['a'], c['b']))
    groups = []
    for change in changes:
        if groups and (change['a'] < groups[-1]['b'] or change['a'] == groups[-1]['b'] and
                       (change['a'] == change['b'] or groups[-1]['a'] == groups[-1]['b'])):
            groups[-1]['items'].append(change)
            groups[-1]['b'] = max(groups[-1]['b'], change['b'])
        else: groups.append({'a': change['a'], 'b': change['b'], 'items': [change]})
    def version(group, side):
        result, pos = [], group['a']
        for change in group['items']:
            if change['side'] != side: continue
            result.extend(original[pos:change['a']]); result.extend(change['text']); pos = change['b']
        result.extend(original[pos:group['b']])
        return ''.join(result)
    parts, pos = [], 0
    for group in groups:
        if pos < group['a']: parts.append({'text': ''.join(original[pos:group['a']]), 'conflict': False})
        before, left, right = ''.join(original[group['a']:group['b']]), version(group, 'local'), version(group, 'disk')
        conflict = left != right and left != before and right != before
        parts.append({'base': before, 'local': left, 'disk': right, 'line': group['a']+1,
                      'conflict': conflict, 'text': right if left == before else left})
        pos = group['b']
    if pos < len(original): parts.append({'text': ''.join(original[pos:]), 'conflict': False})
    return {'parts': parts}
