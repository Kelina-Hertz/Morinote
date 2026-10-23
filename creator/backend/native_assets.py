"""Read-only resource inventory and label-based virtual assets.

The managed RPY is the sole editable registry. Opening/scanning never writes it.
"""
from __future__ import annotations
import ast
from .source_literals import literal_eval
import copy
import hashlib
import json
from pathlib import Path
import pprint
import re
import textwrap
import uuid

REGISTRY = 'game/creator_assets/asset_bindings.rpy'
BEGIN = '# creator:asset-library:begin'
END = '# creator:asset-library:end'
TYPES = {'sprite', 'background', 'cg', 'bgm', 'ambience', 'sound', 'voice', 'interface', 'unknown'}
IMAGE = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg', '.gif'}
AUDIO = {'.ogg', '.opus', '.mp3', '.wav', '.flac'}
ROLES = {'duou': '渡鸥', 'xiquan': '汐泉', 'lanxue': '蓝雪', 'wenzhu': '文竹', 'hinata': '日向', 'doragon': '梦龙'}
TOKEN = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''


def stable(kind, key):
    return 'virtual_' + hashlib.sha256((kind + ':' + key).encode('utf-8')).hexdigest()[:20]


def game_path(value):
    if not isinstance(value, str) or not value or len(value) > 2000 or '\\' in value or ':' in value or value.startswith('/'):
        raise ValueError('请选择当前工程内的素材路径。')
    if any(p in ('', '.', '..') or p.lower() in {'.creator', '.git', 'cache', 'saves', '__pycache__'} for p in value.split('/')):
        raise ValueError('素材路径不能越界或指向编辑器内部目录。')
    return value


def read_table(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if not text.strip(): return {'version': 1, 'entries': [], 'deleted': []}
    if text.count(BEGIN) != 1 or text.count(END) != 1 or BEGIN not in text or END not in text:
        raise ValueError('素材映射文件不是可识别的受管文件，请先查看源码，不会覆盖原内容。')
    raw = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    try:
        if not raw.startswith('init 998 python:\n'): raise ValueError('无效数据块')
        parsed = ast.parse(textwrap.dedent(raw.split('\n', 1)[1]))
        statement = parsed.body[0]
        if len(parsed.body) != 1 or not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name) or statement.targets[0].id != '_creator_asset_table': raise ValueError('无效数据块')
        data = literal_eval(statement.value)
    except (ValueError, TypeError, SyntaxError, IndexError) as exc: raise ValueError('素材表数据损坏，请在源码中修复或恢复历史。') from exc
    validate(data)
    return data


def validate(data):
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('entries'), list) or len(data['entries']) > 10000:
        raise ValueError('不支持的虚拟素材表。')
    seen, keys = set(), set()
    for entry in data['entries']:
        if not isinstance(entry, dict) or not re.fullmatch(r'virtual_[a-f0-9]{12,32}', str(entry.get('id', ''))) or entry['id'] in seen:
            raise ValueError('虚拟素材 ID 无效或重复。')
        seen.add(entry['id'])
        runtime = entry.get('runtime', {})
        kind, key = runtime.get('kind'), runtime.get('key')
        if kind not in {'image', 'file', 'audio-variable'} or not isinstance(key, str) or not key or len(key) > 2000:
            raise ValueError('虚拟素材运行标识无效。')
        if (kind, key) in keys: raise ValueError('运行标识已经被另一个虚拟素材使用。')
        keys.add((kind, key))
        if kind == 'image' and not re.fullmatch(r'[\w]+(?: [\w]+)*', key): raise ValueError('图片标签需为单词及空格。')
        if kind == 'file': game_path(key)
        if kind == 'audio-variable' and not re.fullmatch(r'audio\.[A-Za-z_]\w*', key): raise ValueError('音频变量无效。')
        if entry.get('type') not in TYPES: raise ValueError('素材类型无效。')
        for field in ('name', 'character', 'costume', 'expression', 'requirement', 'category'):
            if not isinstance(entry.get(field, ''), str) or len(entry.get(field, '')) > 1000: raise ValueError('素材名称或说明过长。')
        for field in ('originalPath', 'targetPath'):
            if entry.get(field): game_path(entry[field])
        if not entry.get('name', '').strip(): raise ValueError('请填写虚拟素材名称。')
        binding = entry.get('binding')
        if type(entry.get('temporary', False)) is not bool or type(entry.get('override', False)) is not bool: raise ValueError('替代标记或映射标记无效。')
        if binding is not None:
            if not isinstance(binding, dict) or binding.get('kind') not in {'original', 'label', 'file'}: raise ValueError('素材绑定类型无效。')
            if binding['kind'] == 'file': game_path(binding.get('key'))
            elif not isinstance(binding.get('key'), str) or not binding['key']: raise ValueError('请选择目标图片标签。')
            if binding['kind'] == 'label' and kind != 'image': raise ValueError('只有图片标签可以绑定已有图片定义。')
            if binding['kind'] == 'original' and (kind != 'image' or binding['key'] != key): raise ValueError('原定义绑定必须指向该图片自身。')
    if not isinstance(data.get('deleted', []), list) or len(data.get('deleted', [])) > 10000 or any(not isinstance(v, str) or not re.fullmatch(r'virtual_[a-f0-9]{12,32}', v) for v in data.get('deleted', [])): raise ValueError('素材删除记录无效。')


def inferred_type(asset, project):
    explicit = project.get('ide', {}).get('assetTypes', {}).get(asset.get('id'))
    if explicit in TYPES: return explicit
    if asset.get('kind') in ('sprite', 'background'): return asset['kind']
    path = asset.get('nativeGamePath', asset.get('path', '')).lower()
    if asset.get('kind') == 'audio':
        if re.search(r'(?:bgm|music)', path): return 'bgm'
        if re.search(r'(?:voice|/cv/)', path): return 'voice'
        if re.search(r'ambien', path): return 'ambience'
        return 'sound'
    return 'interface' if re.search(r'(?:gui|ui)/', path) else 'unknown'


def augment(project, scripts, images, constants):
    """Decorate the source projection; actual image definitions remain untouched."""
    if not project.get('nativeRenpy', {}).get('inPlace'): return
    physical = [a for a in project['assets'] if not a.get('virtual') and not a.get('nativeGamePath', '').startswith('_creator_virtual/')]
    project['assets'] = physical
    files = {f['gamePath'] for f in project['nativeRenpy']['files']}
    resources = [a for a in physical if a.get('nativeGamePath') in files and Path(a.get('nativeGamePath', '')).suffix.lower() in IMAGE | AUDIO]
    by_path = {a['nativeGamePath']: a for a in physical if a.get('nativeGamePath')}
    table_text = next((text for item, text in scripts if item['projectPath'] == REGISTRY), '')
    library_error = None
    try: table = read_table(table_text)
    except ValueError as exc:
        library_error = str(exc)
        previous = project.get('nativeAssetLibrary')
        table = data_from_library(previous) if previous else {'version': 1, 'entries': [], 'deleted': []}
    entries = {e['id']: copy.deepcopy(e) for e in table['entries']}
    runtime_entries = {(e['runtime']['kind'], e['runtime']['key']): e for e in entries.values()}
    deleted = set(table.get('deleted', []))
    declarations, references, audio_variables = {}, {}, {}
    originals = copy.deepcopy(images)
    known_files = {a['nativeGamePath']: a for a in resources}

    def seed(kind, key, asset=None, source=None, target=None):
        eid = stable(kind, key)
        if eid in deleted: return None
        existing = runtime_entries.get((kind, key))
        if existing is not None:
            if source: existing['source'] = source
            return existing
        if eid not in entries:
            asset = asset or {}
            category_id = project.get('ide', {}).get('assetCategories', {}).get(asset.get('id'))
            categories = {c['id']: c for c in project.get('ide', {}).get('categories', [])}
            category, seen = [], set()
            while category_id in categories and category_id not in seen:
                seen.add(category_id); item = categories[category_id]; category.append(item['name']); category_id = item.get('parent')
            label = key if kind != 'file' else Path(key).stem
            name = asset.get('name') or label
            if name == ' / '.join(asset.get('nativeAliases', [])): name = label
            character = asset.get('character', '')
            parts = Path(asset.get('nativeGamePath', '')).parts
            if not character and asset.get('kind') == 'sprite' and 'characters' in parts:
                position = parts.index('characters') + 1
                if position < len(parts): character = ROLES.get(parts[position], '')
            entries[eid] = {'id': eid, 'runtime': {'kind': kind, 'key': key}, 'name': name,
                'type': inferred_type(asset, project), 'character': ROLES.get(character, character), 'costume': asset.get('costume', ''),
                'expression': asset.get('expression', ''), 'requirement': asset.get('requirement', ''), 'category': '/'.join(reversed(category)),
                'binding': target or {'kind': 'original' if kind == 'image' else 'file', 'key': key},
                'temporary': asset.get('status') == 'placeholder', 'override': False,
                'fallbackAlias': asset.get('fallbackAlias', ''), 'source': source, 'originalPath': asset.get('nativeGamePath', '')}
        elif source: entries[eid]['source'] = source
        runtime_entries[(kind, key)] = entries[eid]
        return entries[eid]

    for item, text in scripts:
        if item['projectPath'] == REGISTRY: continue
        image_block = False
        for n, row in enumerate(text.splitlines(), 1):
            source = {'path': item['projectPath'], 'line': n}
            if image_block and row.strip() and not row[0].isspace(): image_block = False
            match = re.match(r'^image\s+([\w]+(?: [\w]+)*)(?:\s*=|\s*:)', row)
            if match:
                key = match[1].strip(); info = originals.get(key)
                asset = next((a for a in physical if a['id'] == (info or {}).get('asset')), None)
                declarations[key] = {'key': key, 'source': source, 'asset': asset['id'] if asset else None, 'props': (info or {}).get('props', {}), 'opaque': not bool(info)}
                seed('image', key, asset, source)
                image_block = row.rstrip().endswith(':')
            audio = re.match(r'^define\s+(audio\.[A-Za-z_]\w*)\s*=\s*(' + TOKEN + r')', row)
            if audio:
                try: path = literal_eval(audio[2])
                except (ValueError, SyntaxError): continue
                if isinstance(path, str) and Path(path).suffix.lower() in AUDIO:
                    try: game_path(path)
                    except ValueError: continue
                    audio_variables[audio[1]] = path
                    asset = by_path.get(path) or {'kind': 'audio', 'nativeGamePath': path, 'name': Path(path).stem, 'status': 'missing'}
                    e = seed('audio-variable', audio[1], asset, source, {'kind': 'file', 'key': path})
                    if e: e['originalPath'] = path
            if not match and not image_block and not row.lstrip().startswith('#'):
                for token in re.finditer(TOKEN, row):
                    try: path = literal_eval(token[0])
                    except (ValueError, SyntaxError): continue
                    if not isinstance(path, str) or Path(path).suffix.lower() not in IMAGE | AUDIO or path.startswith(('<', '/')): continue
                    try: game_path(path)
                    except ValueError: continue
                    asset = by_path.get(path)
                    if asset is not None: seed('file', path, asset, source)
    for asset in physical:
        path = asset.get('nativeGamePath', '')
        if not path or Path(path).suffix.lower() not in IMAGE | AUDIO: continue
        if Path(path).suffix.lower() in AUDIO or not asset.get('nativeAliases'):
            seed('file', path, asset)
    for key in ('black', 'white'):
        if key in originals and key not in declarations:
            seed('image', key, next((a for a in physical if a['id'] == originals[key]['asset']), None))

    # Reference lookup is conservative and excludes declarations and the registry.
    # It never rewrites the returned source ranges.
    reference_keys = {}
    for e in entries.values(): reference_keys.setdefault(e['runtime']['key'], []).append(e['id'])
    entry_sources = {e['id']: e.get('source') for e in entries.values()}
    for item, text in scripts:
        if item['projectPath'] == REGISTRY: continue
        for n, row in enumerate(text.splitlines(), 1):
            if not row.strip() or row.lstrip().startswith('#'): continue
            image_ref = re.match(r'\s*(?:show|scene)\s+(.+?)(?=\s+(?:as|at|with|onlayer|zorder|behind)\b|:|\s*$)', row)
            keys = set(re.findall(r'\baudio\.[A-Za-z_]\w*', row))
            if image_ref: keys.add(image_ref[1].strip())
            for match in re.finditer(TOKEN, row):
                try: keys.add(literal_eval(match[0]))
                except (ValueError, SyntaxError, TypeError): pass
            for key in keys:
                for eid in reference_keys.get(key, []):
                    if entry_sources[eid] != {'path': item['projectPath'], 'line': n}:
                        references.setdefault(eid, []).append({'path': item['projectPath'], 'line': n, 'text': row.strip()[:180]})

    labels = {key: {'key': key, **value} for key, value in declarations.items()}
    for e in entries.values():
        if e['runtime']['kind'] == 'image' and not e.get('override'):
            key = e['runtime']['key']
            if key in originals: labels.setdefault(key, {'key': key, 'props': (originals[key] or {}).get('props', {}), 'asset': (originals[key] or {}).get('asset')})
    resolved = []
    physical_by_id = {a['id']: a for a in physical}
    effective_files = {}
    for e in entries.values():
        binding, kind, key = e.get('binding'), e['runtime']['kind'], e['runtime']['key']
        # A hand-edited binding literal is also effective; no separate flag can
        # make the editor show one target while Ren'Py silently uses another.
        baseline_key = e.get('originalPath') if kind == 'audio-variable' else key
        expected = {'kind': 'original' if kind == 'image' else 'file', 'key': baseline_key}
        e['override'] = bool(e.get('override') or binding != expected)
        props, target_asset, opaque = {}, None, False
        available = False
        if binding and binding['kind'] in ('label', 'original'):
            target_key = binding['key']; info = originals.get(target_key)
            target_asset = physical_by_id.get((info or {}).get('asset'))
            props = copy.deepcopy((info or {}).get('props', {}))
            opaque = target_key in declarations and not bool(info)
            available = bool(info) and (not target_asset or target_asset.get('path', '').startswith('builtin:') or target_asset.get('nativeGamePath') in known_files)
            available = available or opaque
        elif binding:
            target_asset = known_files.get(binding['key']); available = bool(target_asset)
        status = 'unbound' if not binding else 'broken' if not available else 'temporary' if e.get('temporary') else 'bound'
        media = target_asset if available else None
        image_kind = e['type'] if e['type'] in ('sprite', 'background') else 'audio' if e['type'] in ('bgm', 'ambience', 'sound', 'voice') else 'image'
        cue = {'id': e['id'], 'kind': image_kind, 'name': e['name'], 'path': media.get('path', '') if media else '',
            'status': 'ready' if status == 'bound' else 'placeholder', 'requirement': e.get('requirement') or e['name'],
            'character': e.get('character', ''), 'costume': e.get('costume', ''), 'expression': e.get('expression', ''),
            'virtual': True, 'virtualStatus': status, 'mediaAssetId': media['id'] if media and not media.get('path', '').startswith('builtin:') else None,
            'nativeAliases': [key] if kind == 'image' else [], 'virtualType': e['type'], 'virtualRuntimeKind': kind}
        if kind != 'image':
            runtime_path = '_creator_virtual/audio/' + e['id'] + '.wav' if kind == 'audio-variable' else key
            cue['nativeGamePath'] = runtime_path
            effective_files[runtime_path] = cue
            if kind == 'audio-variable' and e.get('override'): constants[key] = runtime_path
        else:
            cue['nativeGamePath'] = key
            if not e.get('override') and key in originals:
                props = copy.deepcopy((originals[key] or {}).get('props', {}))
            elif binding and binding['kind'] == 'file': props = {}
            if not available: props = {}
            images[key] = {'asset': e['id'], 'props': props, 'notes': ['复杂图片定义由原引擎执行'] if opaque else []}
        entry = {**e, 'status': status, 'mediaAssetId': cue['mediaAssetId'], 'path': cue['path'], 'opaque': opaque,
            'references': references.get(e['id'], []), 'props': props,
            'targetPath': target_asset.get('nativeGamePath', '') if target_asset else ''}
        resolved.append(entry); project['assets'].append(cue)
    project['nativeAssetLibrary'] = {'version': 1, 'path': REGISTRY, 'entries': resolved,
        'resources': [{**a, 'status': 'ready'} for a in resources], 'labels': list(labels.values()), 'deleted': list(deleted)}
    if library_error: project['nativeAssetLibrary']['error'] = library_error
    project['nativeRenpy']['assetLibraryVersion'] = 1
    return effective_files


def data_from_library(library):
    fields = {'id', 'runtime', 'name', 'type', 'character', 'costume', 'expression', 'requirement', 'category', 'binding', 'temporary', 'override', 'source', 'originalPath', 'fallbackAlias', 'targetPath'}
    return {'version': 1, 'entries': [{k: v for k, v in e.items() if k in fields} for e in library['entries']], 'deleted': library.get('deleted', [])}


def render_table(data):
    validate(data)
    payload = pprint.pformat(data, width=110, sort_dicts=True).replace('\n', '\n    ')
    runtime = Path(__file__).with_name('native_assets_runtime.rpy').read_text('utf-8')
    # Both the editor and runtime read this same literal; there is no second
    # JSON copy whose changes could silently diverge from the running game.
    return ('# Managed virtual assets. Actual project resources are read-only.\n' + BEGIN + '\n' +
            'init 998 python:\n    _creator_asset_table = ' + payload + '\n' + END + '\n' + runtime)


def edit(root, project, op):
    from .workspace import read_overlay
    if not project.get('nativeRenpy', {}).get('inPlace'): raise ValueError('虚拟素材库需要直接打开原 Ren’Py 工程。')
    library = project['nativeAssetLibrary']; data = data_from_library(library)
    document = read_overlay(root, REGISTRY, op.get('documents'))
    if document['content'].strip():
        saved = read_table(document['content'])
        runtime = Path(__file__).with_name('native_assets_runtime.rpy').read_text('utf-8').strip()
        if document['content'].replace('\r\n', '\n').split(END, 1)[1].strip() != runtime:
            raise ValueError('受管素材文件的运行代码已被手工修改，请使用源码编辑或先恢复受管版本；不会覆盖自定义代码。')
    if op.get('registryHash') and op['registryHash'] != document['hash']: raise ValueError('素材映射文件已被外部修改，请重新载入。')
    action = op.get('operation'); entry = next((e for e in data['entries'] if e['id'] == op.get('id')), None)
    if action == 'create':
        eid = 'virtual_' + uuid.uuid4().hex[:20]; kind = op.get('type', 'sprite')
        if kind not in TYPES: raise ValueError('请选择素材类型。')
        key = 'creator_' + eid
        runtime = {'kind': 'file' if kind in ('bgm', 'ambience', 'sound', 'voice') else 'image', 'key': '_creator_virtual/audio/' + eid + '.wav' if kind in ('bgm', 'ambience', 'sound', 'voice') else key}
        entry = {'id': eid, 'runtime': runtime, 'name': str(op.get('name', '')).strip(), 'type': kind,
            'binding': None, 'override': True, 'temporary': False, 'character': '', 'costume': '', 'expression': '', 'category': '', 'requirement': str(op.get('name', '')).strip()}
        data['entries'].append(entry)
    elif entry is None: raise ValueError('虚拟素材不存在，请重新选择。')
    elif action == 'update':
        patch = op.get('values', {})
        for field in ('name', 'type', 'character', 'costume', 'expression', 'requirement', 'category'):
            if field in patch: entry[field] = patch[field]
        if 'type' in patch:
            is_audio = entry['runtime']['kind'] == 'audio-variable' or Path(entry['runtime']['key']).suffix.lower() in AUDIO
            if is_audio != (entry['type'] in ('bgm', 'ambience', 'sound', 'voice')): raise ValueError('音频与图片不能互相转换，请新建另一条虚拟素材。')
    elif action == 'bind':
        binding = op.get('binding', {})
        if binding.get('kind') == 'file':
            target = next((a for a in library['resources'] if a['nativeGamePath'] == binding.get('key')), None)
            if not target: raise ValueError('请选择当前工程登记的实际资源。')
            from .project import safe_path
            path = safe_path(root, target['path'])
            if not path.is_file() or path.is_symlink(): raise ValueError('绑定文件已丢失或不是普通工程文件。')
            expected_audio = entry['type'] in ('bgm', 'ambience', 'sound', 'voice')
            if (Path(binding['key']).suffix.lower() in AUDIO) != expected_audio: raise ValueError('素材类型与目标文件不匹配。')
        elif binding.get('kind') == 'label':
            if entry['runtime']['kind'] != 'image' or not any(l['key'] == binding.get('key') for l in library['labels']): raise ValueError('请选择原工程声明的图片标签。')
        else: raise ValueError('无效绑定目标。')
        entry['binding'] = binding; entry['override'] = True; entry['temporary'] = op.get('temporary') is True
    elif action == 'unbind': entry.update(binding=None, override=True, temporary=False)
    elif action == 'original':
        kind, key = entry['runtime']['kind'], entry['runtime']['key']
        if kind == 'image' and not any(l['key'] == key for l in library['labels']): raise ValueError('此条目没有原工程定义。')
        entry.update(binding={'kind': 'original' if kind == 'image' else 'file', 'key': key if kind != 'audio-variable' else entry.get('originalPath', '')}, override=False)
    elif action == 'delete':
        resolved = next(e for e in library['entries'] if e['id'] == entry['id'])
        if resolved.get('references'): raise ValueError('剧情或系统正在引用该素材，请先解除引用；也可以解绑后使用占位。')
        data['entries'] = [e for e in data['entries'] if e['id'] != entry['id']]
        data['deleted'].append(entry['id'])
    else: raise ValueError('未知虚拟素材操作。')
    # Availability hints must be updated in the same document as the binding,
    # rather than waiting for the disposable source index to be refreshed.
    for value in data['entries']:
        bound = value.get('binding')
        if bound and bound['kind'] == 'file': value['targetPath'] = bound['key']
        elif bound:
            label = next((l for l in library['labels'] if l['key'] == bound['key']), {})
            physical = next((a for a in project['assets'] if not a.get('virtual') and a['id'] == label.get('asset')), {})
            value['targetPath'] = physical.get('nativeGamePath', '')
        else: value['targetPath'] = ''
    validate(data)
    return {'path': REGISTRY, 'hash': document['hash'], 'content': render_table(data)}
