"""Source-preserving Ren'Py import. Indexing never executes the imported code.

The index is an editing projection, not a replacement interpreter. Original
control flow, Python, ATL, screens and character callbacks continue to run.
"""
from __future__ import annotations
import ast
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid

from .demo import make_project
from .project import atomic_json, safe_path, project_file, EDITOR_PROJECT

IMAGE = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.gif', '.svg'}
AUDIO = {'.ogg', '.mp3', '.wav', '.opus', '.flac'}
OMIT_DIRS = {'cache', 'saves', '__pycache__', '.git', '.creator', 'screenshots'}
OMIT_FILES = {'log.txt', 'traceback.txt', 'errors.txt', 'script_version.txt'}
TOKEN = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
SAY = re.compile(r'^(?P<indent>[ \t]+)(?P<who>(?:[^\W\d]\w*\s+)?)' + r'(?P<token>' + TOKEN + r')(?P<tail>\s*(?:\([^\n]*\))?\s*(?:#.*)?)$')
LABEL = re.compile(r'^label\s+([\w.]+)\s*(\([^\n]*\))?\s*:\s*(?:#.*)?$')


def ident(prefix, value):
    return prefix + hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]


def game_directory(source):
    source = Path(source).expanduser().resolve()
    if source.is_file() and source.name == 'project.json':
        source = source.parent
    if source.is_dir() and source.name.lower() == 'game':
        source = source.parent
    game = source / 'game' if (source / 'game').is_dir() else source
    if not game.is_dir() or not any(game.rglob('*.rpy')):
        raise ValueError('请选择包含 game/*.rpy 的 Ren’Py 工程文件夹。只有分发包或 .rpyc 的工程需要先提供源脚本。')
    return source, game


def index_sources(root, document, previous=None, source_contents=None):
    """Create conservative, source-linked text/label/edge and opaque-code indexes."""
    root = Path(root)
    native = document['nativeRenpy']
    scripts = []
    characters = {'nvl_narrator': ''}
    chat_aliases = set()
    character_sources={}
    auto_defaults={'afmTime':15.0,'bonus':25.0,'characters':250.0}
    for item in native['files']:
        if not item['gamePath'].endswith('.rpy'):
            continue
        path = safe_path(root, item['projectPath'])
        text = (source_contents or {}).get(item['projectPath'])
        if text is None: text = path.read_text(encoding='utf-8-sig')
        scripts.append((item, text))
        for key,name in (('afmTime','preferences.afm_time'),('bonus','config.afm_bonus'),('characters','config.afm_characters')):
            value=re.search(r'(?m)^define\s+'+re.escape(name)+r'\s*=\s*([0-9.]+)',text)
            if value:auto_defaults[key]=float(value[1])
        for role in re.finditer(r'(?ms)^define\s+(\w+)\s*=\s*Character\((.*?)(?=^define\s|^label\s|\Z)',text):
            if re.search(r'kind\s*=\s*nvl\b',role[2]):chat_aliases.add(role[1])
        for match in re.finditer(r'(?m)^\s*define\s+(\w+)\s*=\s*Character\(\s*(' + TOKEN + ')', text):
            try:
                characters[match[1]] = ast.literal_eval(match[2])
                character_sources[match[1]]={'path':item['projectPath'],'line':text[:match.start()].count('\n')+1}
            except (SyntaxError, ValueError):
                pass
        for match in re.finditer(r'(?m)^\s*define\s+(\w+)\s*=\s*Character\(\s*None\b',text):
            characters[match[1]]=''
            character_sources[match[1]]={'path':item['projectPath'],'line':text[:match.start()].count('\n')+1}
            chat_aliases.discard(match[1])
    old_ids = {}
    graphs, scenes, labels, edges, opaque, line_records = [], [], [], [], [], {}
    known_resources = {item['gamePath'] for item in native['files']}
    resource_hints = []
    for item, text in scripts:
        game_path = item['gamePath']
        gid = ident('file_', game_path)
        graph = {'id': gid, 'title': game_path, 'parent': None, 'entry': '', 'nodes': []}
        current = None
        local_base = ''
        skip_indent = None
        triple = None
        phone_title = '手机聊天'
        phone_mode = game_path == 'message.rpy'
        source_rows=text.splitlines(keepends=True)
        for number, raw in enumerate(source_rows, 1):
            body = raw.rstrip('\r\n')
            stripped = body.strip()
            indent = len(body) - len(body.lstrip(' \t'))
            if triple:
                if body.count(triple) % 2:
                    triple = None
                continue
            triples = [q for q in ('"""', "'''") if body.count(q) % 2]
            if triples and not stripped.startswith('#'):
                triple = triples[0]
                if current: opaque.append({'file': game_path, 'line': number, 'kind': 'multiline', 'label': current['name']})
                continue
            match = LABEL.match(body)
            if match:
                name = match[1]
                if name.startswith('.'):
                    name = local_base + name
                else:
                    local_base = name
                sid = ident('label_', game_path + ':' + name)
                prior=[s for s in (previous or {}).get('scenes',[]) if s.get('title')==name]
                if len(prior)==1:sid=prior[0]['id']
                current = {'id': sid, 'name': name, 'graph': gid, 'file': game_path,
                           'line': number, 'parameters': match[2] or '', 'callable': match[2] in (None, '()')}
                labels.append(current)
                phone_mode = game_path == 'message.rpy'
                scenes.append({'id': sid, 'title': name, 'lines': [], 'nativeLabel': name})
                graph['nodes'].append({'id': sid, 'type': 'scene', 'title': name, 'scene': sid})
                graph['entry'] = graph['entry'] or sid
                skip_indent = None
                continue
            if stripped and not stripped.startswith('#') and indent == 0:
                current = None
                skip_indent = None
            if not current or not stripped or stripped.startswith('#'):
                continue
            phone = re.match(r'show screen qq_\w+\(\s*(' + TOKEN + ')',stripped)
            if phone:
                phone_mode = True
                try:phone_title=ast.literal_eval(phone[1])
                except (SyntaxError,ValueError):pass
            mode=re.match(r'\$\s*nvl_mode\s*=\s*(.*)',stripped)
            if mode: phone_mode=mode[1].strip().strip('"\'')=='phone'
            if skip_indent is not None:
                if indent > skip_indent:
                    continue
                skip_indent = None
            # Python and ATL strings are not narration. Keep their whole block opaque.
            if re.match(r'(?:python(?:\s+\w+)*|(?:show|scene|camera)\b.*):\s*(?:#.*)?$', stripped):
                skip_indent = indent
                opaque.append({'file': game_path, 'line': number, 'kind': 'code-block', 'label': current['name']})
                continue
            jump = re.match(r'(jump|call)\s+(?!screen\b)([\w.]+)(.*)', stripped)
            if jump:
                target = jump[2]
                if target.startswith('.'):
                    target = local_base + target
                edges.append({'source': current['id'], 'targetLabel': target, 'kind': jump[1],
                              'file': game_path, 'line': number, 'dynamic': target == 'expression', 'statement': stripped})
            match = SAY.match(body)
            if match:
                alias = match['who'].strip()
                # Unknown say aliases can be custom statements; leave them intact.
                if alias and alias not in characters:
                    opaque.append({'file': game_path, 'line': number, 'kind': 'custom-say', 'label': current['name']})
                    continue
                try:
                    value = ast.literal_eval(match['token'])
                except (SyntaxError, ValueError):
                    continue
                current_scene = next(s for s in reversed(scenes) if s['id'] == current['id'])
                lid = old_ids.get((current_scene['id'], len(current_scene['lines'])), ident('text_', game_path + ':' + str(number)))
                record = {'file': game_path, 'path': item['projectPath'], 'line': number, 'original': body,
                          'tokenStart': match.start('token'), 'tokenEnd': match.end('token'), 'text': value}
                line_records[lid] = record
                wait=None
                if number>=2:
                    prepared=re.search(r'\$ creator_native_auto_prepare\([^\n]*,\s*([0-9.eE+-]+)\s*\)',source_rows[number-2])
                    if prepared:wait=float(prepared[1])
                chat = phone_mode and (alias in chat_aliases or alias=='nvl_narrator')
                next(s for s in reversed(scenes) if s['id'] == current['id'])['lines'].append({
                    'id': lid, 'kind': 'chat' if chat else 'dialogue' if alias and characters.get(alias) else 'narration', 'speaker': characters.get(alias, ''),
                    'text': value, 'autoWait': wait, 'visual': None, 'audio': None,
                    **({'advance': not bool(re.search(r'interact\s*=\s*False',match['tail'])), 'phone':{'title':phone_title}} if chat else {}),
                    'source': {'file': game_path, 'line': number, 'label': current['name'], 'alias': alias}})
            elif not jump:
                opaque.append({'file': game_path, 'line': number, 'kind': 'source-statement', 'label': current['name']})
        if graph['nodes']:
            graphs.append(graph)
        # This is a conservative resource report, not a claim that Python's
        # dynamic resource lookup has been resolved.
        image_context=False
        for number, raw in enumerate(text.splitlines(), 1):
            if raw.lstrip().startswith('#'):
                continue
            if raw.strip() and not raw[0].isspace():image_context=raw.startswith('image ')
            say=SAY.match(raw)
            if say and (not say['who'].strip() or say['who'].strip() in characters):continue
            for token in re.findall(TOKEN, raw):
                try:
                    value = ast.literal_eval(token)
                except (SyntaxError, ValueError):
                    continue
                if not isinstance(value, str) or Path(value).suffix.lower() not in IMAGE | AUDIO or any(c in value for c in '[{'):
                    continue
                if value.replace('\\', '/').removeprefix('./') not in known_resources:
                    hard=image_context or bool(re.match(r'(?:image|scene|show|play|voice|add)\b|(?:define|default)\s+(?:audio\.|phone_|config\.)',raw.lstrip()))
                    resource_hints.append({'file': game_path, 'line': number, 'path': value,'required':hard})
    by_name = {}
    for label in labels:
        by_name.setdefault(label['name'], []).append(label['id'])
    for edge in edges:
        matches = by_name.get(edge['targetLabel'], [])
        edge['target'] = matches[0] if len(matches) == 1 and not edge['dynamic'] else None
    if not graphs:
        raise ValueError('源工程没有可索引的 label；源码保留导入需要至少一个剧情标签。')
    entry = next((label for label in labels if label['name'] == 'start'), labels[0])
    next(graph for graph in graphs if graph['id'] == entry['graph'])['entry'] = entry['id']
    document.update(graphs=graphs, scenes=scenes, entryGraph=entry['graph'])
    native.update(labels=labels, edges=edges, opaque=opaque,
                  autoDefaults=auto_defaults,
                  characters=[{'alias':alias,'name':name,'kind':'chat' if alias in chat_aliases or alias=='nvl_narrator' else 'dialogue','source':character_sources.get(alias)} for alias,name in characters.items()],
                  codeFiles=[i['projectPath'] for i in native['files'] if i['gamePath'].endswith(('.rpy', '.py'))], unresolvedResources=resource_hints)
    if native.get('inPlace') and not any(i['gamePath'].endswith('.rpa') for i in native['files']):
        for hint in resource_hints:
            if not hint.get('required'):continue
            relative=hint['path'].replace('\\','/').removeprefix('./')
            if any(a.get('nativeGamePath')==relative for a in document['assets']):continue
            physical=('game/' if native.get('inPlace') else 'assets/renpy/')+relative
            document['assets'].append({'id':ident('asset_',relative),'name':Path(relative).stem,'kind':'audio' if Path(relative).suffix.lower() in AUDIO else 'sprite' if 'characters/' in relative else 'background' if 'scene/' in relative else 'image',
                'path':physical,'nativeGamePath':relative,'status':'missing','requirement':'缺少 '+relative})
    # Match unchanged runs rather than assigning a previous ID by ordinal.
    for scene in scenes:
        old = next((s for s in (previous or {}).get('scenes',[]) if s['id']==scene['id']),None)
        if not old: continue
        key=lambda line:(line.get('source',{}).get('alias',''),line['text'])
        matcher=difflib.SequenceMatcher(a=[key(l) for l in old['lines']],b=[key(l) for l in scene['lines']],autojunk=False)
        replacements=[]
        for tag,a,b,c,d in matcher.get_opcodes():
            if tag=='equal' or tag=='replace' and b-a==d-c==1:
                replacements.extend((scene['lines'][j],old['lines'][a+j-c]['id']) for j in range(c,d))
        # IDs for newly inserted source rows must not collide with reused IDs.
        reused={lid for _,lid in replacements}
        selected={id(line) for line,_ in replacements}
        for line in scene['lines']:
            if id(line) not in selected and line['id'] in reused:
                old_id=line['id'];line['id']=ident('text_',old_id+':'+line['text']);line_records[line['id']]=line_records.pop(old_id)
        records=[(line,new,line_records[line['id']]) for line,new in replacements]
        for line,_,_ in records: line_records.pop(line['id'],None)
        for line,new,record in records: line['id']=new;line_records[new]=record
    from .native_tracks import project_tracks
    project_tracks(document, scripts, line_records)
    baseline = {'graphs': copy.deepcopy(graphs), 'scenes': copy.deepcopy(scenes), 'lines': line_records,
                'variables': copy.deepcopy(document['variables']), 'events': copy.deepcopy(document['events']),
                'components': copy.deepcopy(document['components']), 'entryGraph': document['entryGraph']}
    return baseline


def import_renpy(root, source, title=None):
    root = Path(root).expanduser().resolve()
    source, game = game_directory(source)
    if root == source or root.is_relative_to(source) or source.is_relative_to(root):
        raise ValueError('迁移目标必须位于原工程之外，不能覆盖或嵌套原工程。')
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('请选择空文件夹作为迁移目标。')
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = root.with_name(root.name + '.import-' + uuid.uuid4().hex)
    stage.mkdir()
    try:
        doc = make_project(title or source.name, False)
        doc.update(assets=[], components=[], variables=[], events=[])
        native = {'version': 1, 'mode': 'source-preserving', 'sourceName': source.name, 'files': [],
                  'excluded': [], 'indexPath': 'sources/renpy-index.json'}
        doc['nativeRenpy'] = native
        for file in sorted(game.rglob('*')):
            relative = file.relative_to(game)
            if not file.is_file():
                continue
            if not file.resolve().is_relative_to(game.resolve()) or file.is_symlink():
                raise ValueError('原工程包含指向目录外的链接：' + relative.as_posix())
            if any(p.lower() in OMIT_DIRS for p in relative.parts) or file.name.lower() in OMIT_FILES or file.suffix.lower() in {'.psd', '.log', '.pyc'}:
                native['excluded'].append(relative.as_posix())
                continue
            if file.suffix.lower() == '.rpyc' and file.with_suffix('.rpy').exists():
                continue
            if file.name in {'creator_native_preview.rpy', 'creator_native_config.rpy', 'creator_native_tracks.rpy'}:
                raise ValueError('原工程使用了制作器保留文件名：' + file.name)
            code = file.suffix.lower() in {'.rpy', '.py'}
            project_path = ('extensions/renpy/' if code else 'assets/renpy/') + relative.as_posix()
            target = safe_path(stage, project_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
            item = {'gamePath': relative.as_posix(), 'projectPath': project_path}
            native['files'].append(item)
            if code:
                original = safe_path(stage, 'sources/renpy-original/' + relative.as_posix())
                original.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, original)
            elif file.suffix.lower() in IMAGE | AUDIO:
                aid = ident('asset_', relative.as_posix())
                kind = 'audio' if file.suffix.lower() in AUDIO else 'sprite' if 'characters' in relative.parts else 'background' if 'scene' in relative.parts else 'image'
                doc['assets'].append({'id': aid, 'name': file.stem, 'path': project_path, 'kind': kind,
                                      'status': 'ready', 'nativeGamePath': relative.as_posix()})
                item['assetId'] = aid
        baseline = index_sources(stage, doc)
        atomic_json(stage / native['indexPath'], baseline)
        atomic_json(stage / 'project.json', doc)
        report = {'source': source.name, 'mode': native['mode'], 'labels': len(native['labels']),
                  'editableLines': len(baseline['lines']), 'assets': len(doc['assets']),
                  'preservedStatements': len(native['opaque']), 'excluded': native['excluded'],
                  'unresolvedResources': native['unresolvedResources'],
                  'notes': ['原控制流、Python、ATL、手机和自定义 Screen 继续由原源码执行。',
                            '常见背景、静态立绘和音频映射到三轨；未解析演出标明由源码控制。',
                            '只识别静态 call/jump；条件、动态跳转和自定义语句不推测其执行结果。',
                            'PSD、缓存、存档与调试日志未复制，原工程保留这些文件。']}
        atomic_json(stage / 'sources/migration-report.json', report)
        if root.exists():
            root.rmdir()  # Only the checked, still-empty user-selected target.
        os.replace(stage, root)
        return doc
    except Exception:
        # Remove only this uniquely named staging tree, never the selected source.
        if stage.parent == root.parent and stage.name.startswith(root.name + '.import-'):
            shutil.rmtree(stage, ignore_errors=True)
        raise


def native_files(root):
    """Discover author-owned runtime files in place, never copying assets."""
    root = Path(root).resolve()
    game = safe_path(root, 'game')
    if not game.is_dir():
        raise ValueError('请选择包含 game 文件夹的 Ren’Py 工程目录。')
    result, excluded = [], []
    for file in sorted(game.rglob('*')):
        relative = file.relative_to(game)
        if file.is_symlink():
            raise ValueError('工程包含符号链接，请先改为普通项目文件：' + relative.as_posix())
        if not file.is_file(): continue
        if any(p.lower() in OMIT_DIRS for p in relative.parts) or file.name.lower() in OMIT_FILES or file.suffix.lower() in {'.psd', '.log', '.pyc'}:
            excluded.append(relative.as_posix()); continue
        if file.suffix.lower() == '.rpyc' and file.with_suffix('.rpy').exists(): continue
        if file.stem in {'creator_native_config', 'creator_native_preview'} and file.suffix in {'.rpy', '.rpyc'}:
            raise ValueError('工程包含制作器保留文件名，请先重命名原文件：' + relative.as_posix())
        safe_path(root, 'game/' + relative.as_posix())
        result.append({'gamePath': relative.as_posix(), 'projectPath': 'game/' + relative.as_posix()})
    return result, excluded


def refresh_native_files(root, document):
    files, excluded = native_files(root)
    document['assets'] = [a for a in document['assets'] if not a.get('virtual')]
    old_assets = {a.get('nativeGamePath'): a for a in document['assets'] if a.get('nativeGamePath')}
    present = set()
    for item in files:
        suffix = Path(item['gamePath']).suffix.lower()
        if suffix not in IMAGE | AUDIO: continue
        relative = Path(item['gamePath'])
        aid = ident('asset_', item['gamePath'])
        previous = old_assets.get(item['gamePath'])
        if previous:
            previous.update(path=item['projectPath'], status='placeholder' if previous.get('status')=='placeholder' else 'ready')
            aid = previous['id']
        else:
            document['assets'].append({'id': aid, 'name': relative.stem,
                'kind': 'audio' if suffix in AUDIO else 'sprite' if 'characters' in relative.parts else 'background' if 'scene' in relative.parts else 'image',
                'path': item['projectPath'], 'status': 'ready', 'nativeGamePath': item['gamePath']})
        present.add(item['gamePath'])
        item['assetId'] = aid
    for name, asset in old_assets.items():
        if name not in present and asset.get('status')!='placeholder': asset['status'] = 'missing'
    document['nativeRenpy'].update(files=files, excluded=excluded)


def open_native(source):
    """Attach the editor to an existing tree; all added files live in .creator."""
    root, game = game_directory(source)
    if game != root / 'game':
        raise ValueError('直接打开需要选择包含 game 文件夹的工程目录。')
    descriptor = safe_path(root, EDITOR_PROJECT)
    if descriptor.exists():
        from .project import load_project
        document = load_project(root)
        if not document.get('nativeRenpy', {}).get('inPlace'):
            raise ValueError('此目录的编辑器元数据不是原地工程，无法覆盖。')
        index = safe_path(root, document['nativeRenpy']['indexPath'])
        try:
            previous = json.loads(index.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            previous = document
        # Opening always reads RPY; cached text must never overwrite a source
        # edit made outside the editor, even if a previous cache write failed.
        refresh_native_files(root, document)
        baseline = index_sources(root, document, previous=previous)
        atomic_json(index, baseline)
        document['revision'] += 1
    else:
        document = make_project(root.name, False)
        document.update(assets=[], components=[], variables=[], events=[])
        document['nativeRenpy'] = {'version': 1, 'mode': 'source-preserving', 'inPlace': True,
            'sourceName': root.name, 'files': [], 'excluded': [], 'indexPath': '.creator/editor/renpy-index.json'}
        refresh_native_files(root, document)
        baseline = index_sources(root, document)
        atomic_json(safe_path(root, document['nativeRenpy']['indexPath']), baseline)
    atomic_json(descriptor, document)
    return root, document


def checked_projection(root, document):
    baseline = json.loads(safe_path(root, document['nativeRenpy']['indexPath']).read_text(encoding='utf-8'))
    for key in ('entryGraph', 'variables', 'events', 'components'):
        if document.get(key) != baseline[key]:
            raise ValueError('源码兼容工程的流程／状态／组件由原 RPY 控制，请通过源码修改后重新扫描。')
    normalize_graphs = lambda graphs: [{**g, 'nodes': [{k: v for k, v in n.items() if k != 'position'} for n in g['nodes']]} for g in graphs]
    if normalize_graphs(document['graphs']) != normalize_graphs(baseline['graphs']):
        raise ValueError('源码兼容工程的流程图是源码索引，不能将图上修改冒充为已修改原流程。')
    old_scenes = copy.deepcopy(baseline['scenes'])
    scenes = copy.deepcopy(document['scenes'])
    for collection in (old_scenes, scenes):
        for scene in collection:
            for line in scene['lines']:
                line.pop('text', None)
    if scenes != old_scenes:
        raise ValueError('源码兼容工程只回写已识别对白文字；演出轨道是原 RPY 的视图，演出编辑请修改对应源码后重新扫描。')
    for scene in document['scenes']:
        for line in scene['lines']:
            for sprite in (line.get('visual') or {}).get('sprites', []):
                if sprite.get('animation'):
                    raise ValueError('迁移工程的动画保留在原 RPY；三轨目前编辑静态构图，请在源码添加动画。')
            if (line.get('visual') or {}).get('components'):
                raise ValueError('迁移工程的自定义组件请通过原 RPY 编辑。')
    return baseline


def rendered_sources(root, document):
    baseline = checked_projection(root, document)
    values = {line['id']: line['text'] for scene in document['scenes'] for line in scene['lines']}
    contents = {}
    for item in document['nativeRenpy']['files']:
        if item['gamePath'].endswith(('.rpy', '.py')):
            path = safe_path(root, item['projectPath'])
            if path.is_file():
                contents[item['projectPath']] = path.read_text(encoding='utf-8-sig')
    changes = {}
    for lid, record in baseline['lines'].items():
        if values[lid] != record['text']:
            changes.setdefault(record['path'], []).append((record, values[lid]))
    for path, edits in changes.items():
        if path not in contents:
            raise ValueError('已编辑对白对应的源码文件被删除，请先处理冲突：' + path)
        lines = contents[path].splitlines(keepends=True)
        for record, value in edits:
            index = record['line'] - 1
            if index >= len(lines) or lines[index].rstrip('\r\n') != record['original']:
                raise ValueError('源码与对白索引发生冲突，请先重新扫描源码：' + record['file'] + ':' + str(record['line']))
            raw = lines[index]
            lines[index] = raw[:record['tokenStart']] + json.dumps(value, ensure_ascii=False) + raw[record['tokenEnd']:]
        contents[path] = ''.join(lines)
    return contents


def reindex_project(root, document):
    """Commit pending text patches before regenerating the conservative index."""
    baseline_before = checked_projection(root, document)
    contents = rendered_sources(root, document)
    if document['nativeRenpy'].get('inPlace'):
        refresh_native_files(root, document)
    known = {item['projectPath'] for item in document['nativeRenpy']['files']}
    for path in sorted((Path(root) / 'extensions').rglob('*')) if not document['nativeRenpy'].get('inPlace') else []:
        if not path.is_file() or path.suffix not in {'.rpy', '.py'}:
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in known:
            safe_path(root, relative)
            game_path = relative.removeprefix('extensions/renpy/') if relative.startswith('extensions/renpy/') else relative
            document['nativeRenpy']['files'].append({'gamePath': game_path, 'projectPath': relative})
    baseline = index_sources(root, document, previous=baseline_before, source_contents=contents)
    for path, text in contents.items():
        target = safe_path(root, path)
        if target.read_text(encoding='utf-8-sig') != text:
            stage = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
            stage.write_text(text, encoding='utf-8', newline='')
            os.replace(stage, target)
    atomic_json(safe_path(root, document['nativeRenpy']['indexPath']), baseline)
    return document


def generate_native(root, output, document, entry=None, preview=False):
    contents = rendered_sources(root, document)
    in_place = document['nativeRenpy'].get('inPlace')
    missing=[a for a in document['assets'] if not a.get('virtual') and a.get('status')=='missing' and a.get('nativeGamePath')] if not in_place else []
    if missing:raise ValueError('请先补充或明确选择占位素材：'+'、'.join(a.get('requirement') or a['name'] for a in missing[:8]))
    placeholders=[a for a in document['assets'] if not a.get('virtual') and a.get('status')=='placeholder' and a.get('nativeGamePath')] if not in_place else []
    placeholder_map={}
    for asset in placeholders:
        placeholder_map[asset['nativeGamePath']]='_creator_placeholder_'+asset['id'] if asset['kind']!='audio' else '_creator_placeholders/'+asset['id']+'.wav'
    if placeholder_map:
        def substitute(match):
            try:value=ast.literal_eval(match[0])
            except (ValueError,SyntaxError):return match[0]
            return repr(placeholder_map[value]) if value in placeholder_map else match[0]
        baseline=checked_projection(root,document)
        for path,text in list(contents.items()):
            protected={r['line'] for r in baseline['lines'].values() if r['path']==path}
            contents[path]=''.join(raw if number in protected or raw.lstrip().startswith('#') else re.sub(TOKEN,substitute,raw) for number,raw in enumerate(text.splitlines(keepends=True),1))
    game = Path(output) / 'game'
    game.mkdir(parents=True, exist_ok=True)
    assets = {asset['id']: asset for asset in document['assets'] if not asset.get('virtual')}
    keep = set()
    source_map = {'schemaVersion': 1, 'project': document['id'], 'revision': document['revision'], 'files': {}}
    for item in document['nativeRenpy']['files']:
        target = safe_path(game, item['gamePath'])
        target.parent.mkdir(parents=True, exist_ok=True)
        keep.add(target.relative_to(game).as_posix())
        if item['projectPath'] in contents:
            original = safe_path(root, item['projectPath'])
            if contents[item['projectPath']] == original.read_text(encoding='utf-8-sig'):
                shutil.copy2(original, target)
            else:
                target.write_text(contents[item['projectPath']], encoding='utf-8', newline='')
        else:
            asset = assets.get(item.get('assetId'))
            source = safe_path(root, asset['path'] if asset else item['projectPath'])
            if asset and Path(asset['path']).suffix.lower() != Path(item['gamePath']).suffix.lower():
                raise ValueError('源码工程替换素材需保持文件格式，或在原 RPY 修改引用：' + item['gamePath'])
            if asset and asset.get('status') != 'ready' and not in_place:
                raise ValueError('源码工程的素材占位需要同步修改 RPY 引用，不能静默替换原素材：' + asset['name'])
            shutil.copy2(source, target)
    # New components and assets added after migration remain usable. Their
    # authored relative paths are also their runtime paths.
    known_paths = {item['projectPath'] for item in document['nativeRenpy']['files']}
    known_assets = {item.get('assetId') for item in document['nativeRenpy']['files']}
    for source in sorted((Path(root) / 'extensions').rglob('*')):
        if not source.is_file() or source.suffix not in {'.rpy', '.py', '.json'}:
            continue
        relative = source.relative_to(root).as_posix()
        if relative in known_paths:
            continue
        runtime_path = relative.removeprefix('extensions/renpy/') if relative.startswith('extensions/renpy/') else relative
        target = safe_path(game, runtime_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        keep.add(target.relative_to(game).as_posix())
        shutil.copy2(safe_path(root, relative), target)
    for aid, asset in assets.items():
        if aid in known_assets or asset.get('status') != 'ready' or asset['path'].startswith('builtin:'):
            continue
        target = safe_path(game, asset['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        keep.add(target.relative_to(game).as_posix())
        shutil.copy2(safe_path(root, asset['path']), target)
    baseline = checked_projection(root, document)
    positions = {}
    current_lines = {l['id']: l for s in document['scenes'] for l in s['lines']}
    for lid, record in baseline['lines'].items():
        expected = record['original']
        if current_lines[lid]['text'] != record['text']:
            expected = expected[:record['tokenStart']] + json.dumps(current_lines[lid]['text'], ensure_ascii=False) + expected[record['tokenEnd']:]
        rows = contents[record['path']].splitlines()
        position = next((i for i in range(positions.get(record['path'], 0), len(rows)) if rows[i] == expected), None)
        if position is not None:
            positions[record['path']] = position + 1
            source_map['files'].setdefault('game/' + record['file'], {})[str(position + 1)] = {'line': lid, 'source': record}
    from .compiler import symbol
    config = ('# Isolated creator build configuration.\ninit 999 python:\n'
              '    config.save_directory = ' + repr('creator-native-' + document['id'] + ('-preview' if preview else '')) + '\n'
              '    build.name = ' + repr(symbol(document['id'])) + '\n'
              '    build.directory_name = ' + repr(symbol(document['id']) + '-1.0') + '\n')
    for pattern in ('creator_native_preview.*', '*.log', 'saves/**', 'screenshots/**', 'source_map.json', '.creator-native-files.json', '.creator-native-index.json', 'asset-gaps.json', '.creator/**'):
        config += '    build.classify(' + repr(pattern) + ', None)\n'
    (game / 'creator_native_config.rpy').write_text(config, encoding='utf-8')
    keep.add('creator_native_config.rpy')
    marker = Path(output) / '.creator-native-files.json'
    if marker.is_file():
        for relative in json.loads(marker.read_text(encoding='utf-8')):
            if relative not in keep:
                old = safe_path(game, relative)
                old.unlink(missing_ok=True)
                if old.suffix == '.rpy':
                    old.with_suffix('.rpyc').unlink(missing_ok=True)
    if placeholders:
        import wave
        helper=['# Explicit project placeholder decisions; originals are unchanged.','init 999 python:']
        for asset in placeholders:
            if asset['kind']=='audio':
                target=safe_path(game,placeholder_map[asset['nativeGamePath']]);target.parent.mkdir(parents=True,exist_ok=True)
                with wave.open(str(target),'w') as silent:
                    silent.setparams((1,2,22050,0,'NONE',''));silent.writeframes(b'\0\0'*22050)
                keep.add(target.relative_to(game).as_posix())
            else:
                size=(480,900) if asset['kind']=='sprite' else tuple(document['resolution']) if asset['kind']=='background' else (600,600)
                label=asset.get('requirement') or asset['name']
                helper.append('    renpy.image('+repr(placeholder_map[asset['nativeGamePath']])+', Composite('+repr(size)+', (0,0), Solid("#243b45"), (24,24), Text('+repr('占位：'+label)+', size=28, color="#ffffff", xmaximum='+str(size[0]-48)+')))')
        filename='creator_native_placeholders.rpy';(game/filename).write_text('\n'.join(helper)+'\n',encoding='utf-8');keep.add(filename)
        atomic_json(Path(output)/'asset-gaps.json',[{'asset':a['id'],'requirement':a.get('requirement') or a['name'],'status':'placeholder'} for a in placeholders])
    else:
        (Path(output)/'asset-gaps.json').unlink(missing_ok=True)
    atomic_json(marker, sorted(keep))
    label = (entry or {}).get('nativeLabel')
    if not label and (entry or {}).get('scene'):
        label = next((item['name'] for item in document['nativeRenpy']['labels'] if item['id'] == entry['scene']), None)
    if label:
        spec = next((item for item in document['nativeRenpy']['labels'] if item['name'] == label), None)
        if not spec or not spec['callable'] and 'args' not in (entry or {}):
            raise ValueError('此标签需要参数或不存在，请从原游戏入口试玩。')
    atomic_json(Path(output) / 'source_map.json', source_map)
    return {'output': str(output), 'sourceMap': source_map, 'native': True, 'nativeLabel': label or 'start',
            'diagnostics': [{'severity': 'warning', 'message': '原工程由原 RPY 执行；流程图和三轨是源码索引，动态演出以引擎试玩为准。'}]}
