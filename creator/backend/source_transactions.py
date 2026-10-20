"""Durable write-ahead records for a set of source files and editor metadata."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import uuid

ACTIVE = set()


def _encode(data):
    return None if data is None else base64.b64encode(data).decode('ascii')


def _decode(value):
    return None if value is None else base64.b64decode(value, validate=True)


def _path(root, relative):
    from .project import safe_path
    if Path(relative).parts[0].casefold() == '.git':
        raise ValueError('事务不能修改 Git 内部文件。')
    return safe_path(root, relative)


def _read(path):
    return path.read_bytes() if path.is_file() else None


def _store(root, record):
    from .project import atomic_json
    folder = Path(root)/'.creator/editor/save-transactions'
    if record['state'] == 'recovered': folder = folder/'recovered'
    atomic_json(folder/(record['id']+'.json'), record)


def begin(root, before, after, metadata):
    record = {'version': 1, 'id': uuid.uuid4().hex, 'state': 'pending', 'files': [
        {'path': name, 'before': _encode(data), 'after': _encode(after[name]), 'source': True}
        for name, data in before.items()]}
    for path in metadata:
        relative = path.relative_to(root).as_posix()
        data = _read(path)
        record['files'].append({'path': relative, 'before': _encode(data), 'after': _encode(data), 'source': False})
    _store(root, record)  # durable before the first source write
    return record


def write_json(root, record, path, value):
    from .project import atomic_json
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    relative = path.relative_to(root).as_posix()
    item = next(i for i in record['files'] if i['path'] == relative)
    previous = _decode(item['after'])
    item.setdefault('expectedHashes', []).append(None if previous is None else hashlib.sha256(previous).hexdigest())
    item['after'] = _encode(data)
    _store(root, record)  # metadata's intended content is also recorded first
    atomic_json(path, value)


def finish(root, record, state):
    record['state'] = state
    _store(root, record)
    if state in ('committed', 'aborted', 'recovered'):
        (Path(root)/'.creator/editor/save-transactions'/(record['id']+'.json')).unlink(missing_ok=True)


def rollback(root, record):
    from .workspace import atomic_bytes
    conflicts = []
    for item in record['files']:
        path = _path(root, item['path'])
        before, after = _decode(item['before']), _decode(item['after'])
        current = _read(path)
        current_hash = None if current is None else hashlib.sha256(current).hexdigest()
        if current not in (before, after) and current_hash not in item.get('expectedHashes', []):
            conflicts.append(item['path'])  # preserve edits made outside this transaction
            continue
        if current == before:
            continue
        if before is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, before)
    return conflicts


def recover(root):
    root = Path(root).resolve()
    if str(root) in ACTIVE:
        return
    folder = root/'.creator/editor/save-transactions'
    if not folder.exists():
        return
    for path in sorted(folder.glob('*.json')):
        record = json.loads(path.read_text('utf-8'))
        if record.get('state') in ('committed', 'aborted'):
            path.unlink(missing_ok=True)
            continue
        if record.get('state') != 'pending':
            continue
        if record.get('version') != 1 or record.get('id') != path.stem:
            raise ValueError('保存恢复记录损坏：'+path.name)
        # Validate the entire record before restoring any path.
        for item in record['files']:
            _path(root, item['path'])
            _decode(item['before']); _decode(item['after'])
        record['conflicts'] = rollback(root, record)
        finish(root, record, 'recovered')


def notices(root):
    result = []
    for path in sorted((Path(root)/'.creator/editor/save-transactions/recovered').glob('*.json')):
        record = json.loads(path.read_text('utf-8'))
        if record.get('state') != 'recovered' or record.get('reviewed'):
            continue
        documents = []
        for item in record['files']:
            if not item['source'] or item['after'] is None:
                continue
            before = _decode(item['before'])
            data = before or b''
            documents.append({'base': {'path': item['path'], 'content': data.decode('utf-8-sig'),
                'exists': before is not None, 'hash': hashlib.sha256(data).hexdigest(),
                'bom': data.startswith(b'\xef\xbb\xbf'), 'newline': '\r\n' if b'\r\n' in data else '\n'},
                'value': _decode(item['after']).decode('utf-8-sig')})
        result.append({'id': record['id'], 'documents': documents, 'conflicts': record.get('conflicts', []),
                       'paths': [i['path'] for i in record['files'] if i['source']]})
    return {'items': result}


def acknowledge(root, ids):
    for tid in ids:
        if not isinstance(tid, str) or len(tid) != 32 or any(c not in '0123456789abcdef' for c in tid):
            raise ValueError('无效保存恢复记录。')
        path = Path(root)/'.creator/editor/save-transactions/recovered'/(tid+'.json')
        record = json.loads(path.read_text('utf-8'))
        if record.get('state') != 'recovered':
            raise ValueError('该记录不是待确认的中断恢复。')
        record['reviewed'] = True
        # Keep intended source edits in the normal undo history before clearing
        # the larger recovery record (which also contains editor metadata).
        from .project import atomic_json
        atomic_json(Path(root)/'.creator/editor/history'/(tid+'.json'),
                    {'id': tid, 'files': [{k: i[k] for k in ('path', 'before', 'after')}
                                         for i in record['files'] if i['source']]})
        _store(root, record)
        path.unlink(missing_ok=True)
