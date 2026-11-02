"""Prepare candidate source overlays. Publication and user acceptance are host-owned."""
from __future__ import annotations
import json
from . import workspace, native_assets, native_stage, fragment_authoring

REGISTRY = native_assets.REGISTRY


def prepare(root, project, body):
    documents = list(body.get('documents', []))
    changed = {}

    def update(edit):
        changed[edit['path']] = edit
        documents[:] = [d for d in documents if d['path'] != edit['path']] + [edit]

    bindings = {'voices': {}}
    entries = {}
    for item in body.get('imports', []):
        candidate = workspace.projection(root, project, documents, ide=body.get('ide'))
        target = body.get('target', {}) if body['kind'] != 'fragment' else {}
        entry_id = target.get('assetId') or body.get('entryIds', {}).get(item['key'])
        if entry_id:
            if not any(e['id'] == entry_id for e in candidate['nativeAssetLibrary']['entries']):
                raise ValueError('要更换的虚拟素材已不存在，请重新选择。')
        else:
            edit = native_assets.edit(root, candidate, {'operation': 'create', 'type': item.get('assetType', 'background' if item['kind'] == 'image' else 'voice'),
                'name': body['title'] + (' · 背景' if item['key'] == 'background' else ' · ' + item['key']), 'documents': documents})
            entry_id = edit['entryId']
            update(edit)
        candidate = workspace.projection(root, project, documents, ide=body.get('ide'))
        update(native_assets.edit(root, candidate, {'operation': 'bind', 'id': entry_id, 'binding': {'kind': 'file', 'key': item['gamePath']},
                                                   'temporary': False, 'documents': documents}))
        entries[item['key']] = entry_id
        if item['kind'] == 'image':
            bindings['background'] = entry_id
        else:
            bindings['voices'][item['key']] = {'assetId': entry_id, 'jobId': item['jobId'], 'ttsHash': item['ttsHash'], 'artifactHash': item['sha256'], 'candidateId': item.get('candidateId'), 'promptRevision': item.get('promptRevision')}

    result = {'entryIds': entries}
    if body['kind'] == 'fragment':
        edit = fragment_authoring.prepare(root, project, {**body, 'bindings': bindings, 'documents': documents})
        update(edit)
        result.update({key: edit[key] for key in ('path', 'label', 'sceneId', 'nodeMap')})
    elif body['kind'] == 'voice' and body.get('target', {}).get('nodeId'):
        candidate = workspace.projection(root, project, documents, ide=body.get('ide'))
        node_id = body['target']['nodeId']
        line = next((l for scene in candidate['scenes'] for l in scene['lines'] if l['id'] == node_id), None)
        if not line or fragment_authoring.text_hash(line['text'].replace('[[', '[').replace('{{', '{')) != body['target']['textHash']:
            raise ValueError('目标台词已改变，请确认新台词后再应用配音；已有产物保留。')
        item = next(i for i in body['imports'] if i['kind'] == 'voice')
        edit = native_stage.edit(root, candidate, {'operation': 'voice', 'nodeId': node_id, 'asset': entries[item['key']], 'documents': documents, 'hash': workspace.read_overlay(root, 'game/' + line['source']['file'], documents)['hash']})
        update(edit)
        parsed = workspace.projection(root, project, documents, ide=body.get('ide'))
        target = next((l for s in parsed['scenes'] for l in s['lines'] if l['id'] == node_id), None)
        if target is None:
            # Stable say IDs can change when a previously untracked source is indexed.
            matches = [l for s in parsed['scenes'] for l in s['lines'] if l['source']['file'] == line['source']['file'] and l['text'] == line['text'] and l.get('speaker') == line.get('speaker')]
            target = matches[0] if len(matches) == 1 else None
        if not target:
            raise ValueError('配音插入后无法定位原台词。')
        rows = edit['content'].splitlines(keepends=True)
        index = target['source']['line'] - 1
        indent = rows[index][:len(rows[index])-len(rows[index].lstrip())]
        metadata = {'jobId': item['jobId'], 'textHash': body['target']['textHash'], 'speakerName': target.get('speaker', ''),
                    'ttsHash': item['ttsHash'], 'artifactHash': item['sha256'], 'candidateId': item.get('candidateId')}
        for pos in range(index-1, max(-1, index-7), -1):
            if rows[pos].lstrip().startswith('# creator-voice:'):
                del rows[pos]
                index -= 1
        rows.insert(index, indent + '# creator-voice: ' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':')) + '\n')
        update({**edit, 'content': ''.join(rows)})
        result['path'] = edit['path']
    result['edits'] = list(changed.values())
    return result
