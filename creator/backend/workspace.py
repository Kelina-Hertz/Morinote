"""Project-local source documents and reversible, hash-checked transactions."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import uuid

from .project import safe_path, project_file, atomic_json, load_project

TEXT = {'.rpy', '.py', '.json', '.md', '.txt', '.toml', '.yaml', '.yml', '.ini', '.cfg', '.csv', '.xml', '.html', '.css', '.js', '.ts', '.glsl', '.gitignore', '.gitattributes'}
HIDDEN = {'.git', '.creator', 'node_modules', 'cache', 'saves', '__pycache__', 'screenshots', 'log.txt', 'errors.txt', 'traceback.txt'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_path(root, relative):
    path = safe_path(root, relative)
    if {p.casefold() for p in Path(relative).parts} & {'.git', '.creator', 'sources', 'cache', 'saves', '__pycache__'}:
        raise ValueError('该目录是内部数据或只读原稿，不能通过源码编辑器修改。')
    if path.suffix.lower() not in TEXT and path.name not in TEXT:
        raise ValueError('此文件不是支持的文本源码。')
    return path


def read_document(root, relative):
    path = source_path(root, relative)
    data = path.read_bytes() if path.is_file() else b''
    if len(data) > 4 * 1024 * 1024 or b'\0' in data:
        raise ValueError('文件过大或不是文本文件。')
    try:
        content = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('请先将源码转换为 UTF-8 编码。') from exc
    return {'path': relative, 'content': content, 'hash': digest(data), 'exists': path.exists(),
            'bom': data.startswith(b'\xef\xbb\xbf'), 'newline': '\r\n' if b'\r\n' in data else '\n'}


def file_tree(root):
    root = Path(root).resolve()
    def visit(folder, depth=0):
        if depth > 16: return []
        result = []
        for path in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if path.name.casefold() in HIDDEN or path.is_symlink() or path.suffix.lower() in {'.rpyc', '.pyc', '.psd'}:
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                result.append({'name': path.name, 'path': relative, 'children': visit(path, depth+1)})
            else:
                result.append({'name': path.name, 'path': relative, 'text': path.suffix.lower() in TEXT or path.name in TEXT})
        return result
    return visit(root)


def read_overlay(root, relative, documents=None):
    current=read_document(root,relative)
    supplied=next((d for d in (documents or []) if d['path']==relative),None)
    if supplied:
        if supplied.get('hash')!=current['hash']:raise ValueError('源码发生外部修改：'+relative)
        current['content']=supplied['content']
    return current


def validate_metadata(ide):
    if not isinstance(ide,dict):raise ValueError('项目编辑配置必须为对象。')
    scene_titles=ide.get('sceneTitles',{})
    if not isinstance(scene_titles,dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)>120 for k,v in scene_titles.items()):
        raise ValueError('剧情名称需为最多 120 字的文字。')
    asset_types=ide.get('assetTypes',{})
    allowed_types={'sprite','background','cg','bgm','ambience','sound','voice','interface','unknown'}
    if not isinstance(asset_types,dict) or any(not isinstance(k,str) or v not in allowed_types for k,v in asset_types.items()):
        raise ValueError('无效素材类型。')
    file_groups=ide.get('fileGroups',{})
    if not isinstance(file_groups,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in file_groups.items()):
        raise ValueError('无效文件用途分组。')
    categories=ide.get('categories',[])
    if not isinstance(categories,list) or len(categories)>10000:raise ValueError('素材分类数量无效。')
    by_id={}
    for category in categories:
        if not isinstance(category,dict) or not isinstance(category.get('id'),str) or not category['id'] or category['id'] in by_id or not isinstance(category.get('name'),str) or not category['name'].strip():
            raise ValueError('分类 ID 需唯一，名称不能为空。')
        by_id[category['id']]=category
    for category in categories:
        current=category;visited=set()
        while current.get('parent') is not None:
            if current['id'] in visited or current['parent'] not in by_id:raise ValueError('分类包含循环或无效父分类。')
            visited.add(current['id']);current=by_id[current['parent']]


def projection(root, project, documents):
    from .renpy_import import index_sources
    candidate=copy.deepcopy(project)
    contents={}
    for document in documents:
        path=document['path'];contents[path]=read_overlay(root,path,documents)['content']
        if path.startswith('game/') and Path(path).suffix in ('.rpy','.py') and not any(i['projectPath']==path for i in candidate['nativeRenpy']['files']):
            candidate['nativeRenpy']['files'].append({'projectPath':path,'gamePath':path.removeprefix('game/')})
    baseline_path=safe_path(root,project['nativeRenpy']['indexPath'])
    previous=json.loads(baseline_path.read_text('utf-8')) if baseline_path.exists() else None
    index_sources(root,candidate,previous=previous,source_contents=contents)
    return candidate


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def commit(root, edits, revision, *, engine=None, strict=False):
    from .project import _LOCK
    from .source_transactions import ACTIVE
    root = Path(root).resolve()
    with _LOCK:
        # Recover an earlier interrupted save before claiming this root.
        load_project(root)
        ACTIVE.add(str(root))
        try:
            return _commit(root, edits, revision, engine=engine, strict=strict)
        finally:
            ACTIVE.discard(str(root))


def _commit(root, edits, revision, *, engine=None, strict=False):
    """Code may save an invalid draft; forms must preserve a working source set."""
    root = Path(root)
    document = load_project(root)
    if document['revision'] != revision:
        raise ValueError('项目已变化，请刷新后比较并保存。')
    if not isinstance(edits, list) or not 1 <= len(edits) <= 40:
        raise ValueError('每次源码事务需要 1 至 40 个文件。')
    before, after = {}, {}
    for edit in edits:
        rel = edit['path']
        if rel in after: raise ValueError('事务中存在重复文件。')
        current = read_document(root, rel)
        if edit.get('hash') != current['hash']:
            raise ValueError('源码发生外部修改，请打开差异比较：' + rel)
        content = edit['content']
        if not isinstance(content, str) or len(content.encode('utf-8')) > 4*1024*1024:
            raise ValueError('源码必须小于 4 MiB。')
        content = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', current['newline'])
        data = (b'\xef\xbb\xbf' if current['bom'] else b'') + content.encode('utf-8')
        path = source_path(root, rel)
        before[rel] = path.read_bytes() if path.is_file() else None
        if digest(before[rel] or b'') != current['hash'] or (before[rel] is not None) != current['exists']:
            raise ValueError('源码发生外部修改，请重新比较：'+rel)
        after[rel] = None if edit.get('delete') else data
    descriptor = project_file(root)
    index_path = safe_path(root, document['nativeRenpy']['indexPath']) if document.get('nativeRenpy') else None
    original_meta = descriptor.read_bytes()
    original_index = index_path.read_bytes() if index_path and index_path.exists() else None
    from . import source_transactions as transactions
    metadata = [descriptor, root/'.creator/editor/last-valid-source.json']
    if index_path: metadata.append(index_path)
    record = transactions.begin(root, before, after, metadata)
    def write_meta(path, value):
        transactions.write_json(root, record, path, value)
    diagnostics = []
    writes_complete = False
    write_conflict = False
    def check_files(values):
        nonlocal write_conflict
        for rel, expected in values.items():
            path = source_path(root, rel)
            actual = path.read_bytes() if path.is_file() else None
            if actual != expected:
                write_conflict = True
                raise ValueError('保存期间出现外部修改：'+rel)
    try:
        for rel, data in after.items():
            check_files({rel: before[rel]})
            if data is None: source_path(root,rel).unlink(missing_ok=True)
            else: atomic_bytes(source_path(root, rel), data)
        writes_complete = True
        check_files(after)
        for rel,data in after.items():
            if data is not None and Path(rel).suffix=='.py':compile(data.decode('utf-8-sig'),rel,'exec')
            if data is not None and Path(rel).suffix=='.json':json.loads(data.decode('utf-8-sig'))
        if document.get('nativeRenpy'):
            from .renpy_import import refresh_native_files, index_sources
            candidate = copy.deepcopy(document)
            refresh_native_files(root, candidate)
            previous = json.loads(original_index) if original_index else None
            baseline = index_sources(root, candidate, previous=previous)
            candidate['revision'] += 1
            candidate['sourceStatus'] = {'valid': True}
            write_meta(index_path, baseline)
            write_meta(descriptor, candidate)
            if engine:
                if candidate['nativeRenpy'].get('inPlace') and hasattr(engine, 'check_native'):
                    engine.check_native(root)
                else:
                    engine.build(root, preview=True, output=root / '.creator/checks/source')
            document = candidate
        else:
            document['revision'] += 1
            write_meta(descriptor, document)
        check_files(after)
    except Exception as exc:
        if strict or not writes_complete or write_conflict:
            conflicts = transactions.rollback(root, record)
            if conflicts:
                record['conflicts'] = conflicts
                transactions.finish(root, record, 'recovered')
            else:
                transactions.finish(root, record, 'aborted')
            raise ValueError('修改未应用：' + str(exc)) from exc
        if index_path and original_index is not None: atomic_bytes(index_path, original_index)
        document = json.loads(original_meta)
        if document.get('sourceStatus',{}).get('valid',True):
            valid_documents=[]
            for relative in document.get('nativeRenpy',{}).get('codeFiles',[]):
                value=before.get(relative) if relative in before else source_path(root,relative).read_bytes() if source_path(root,relative).exists() else None
                if value is not None:valid_documents.append({'path':relative,'content':value.decode('utf-8-sig')})
            write_meta(root/'.creator/editor/last-valid-source.json',valid_documents)
        document['revision'] += 1
        document['sourceStatus'] = {'valid': False, 'message': str(exc)}
        write_meta(descriptor, document)
        diagnostics.append({'severity': 'error', 'message': str(exc)})
    tid = record['id']
    journal = {'id': tid, 'files': [{'path': rel,
        'before': base64.b64encode(before[rel]).decode() if before[rel] is not None else None,
        'after': base64.b64encode(data).decode() if data is not None else None} for rel, data in after.items()]}
    atomic_json(root / '.creator/editor/history' / (tid + '.json'), journal)
    transactions.finish(root, record, 'committed')
    return {'project': document, 'root': str(root), 'transaction': tid, 'diagnostics': diagnostics,
            'documents': [read_document(root, rel) for rel in after]}


def restore(root, transaction, revision, *, redo=False, engine=None):
    if not isinstance(transaction, str) or not transaction.isalnum(): raise ValueError('无效事务。')
    journal = json.loads((Path(root) / '.creator/editor/history' / (transaction + '.json')).read_text('utf-8'))
    if journal.get('kind')=='rename':
        source=journal['old'] if redo else journal['new'];target=journal['new'] if redo else journal['old']
        return rename(root,source,target,journal['hash'],revision)
    edits = []
    for item in journal['files']:
        current = read_document(root, item['path'])
        expected = item['before'] if redo else item['after']
        if current['exists'] != (expected is not None) or current['hash'] != digest(base64.b64decode(expected) if expected is not None else b''):
            raise ValueError('源码有后续修改，不能覆盖撤销：' + item['path'])
        value = item['after'] if redo else item['before']
        edits.append({'path': item['path'], 'hash': current['hash'], 'content': base64.b64decode(value).decode('utf-8-sig') if value else '', 'delete':value is None})
    return commit(root, edits, revision, engine=engine)


def rename(root, old, new, expected_hash, revision):
    document = load_project(root)
    if document['revision'] != revision: raise ValueError('项目已变化。')
    source, target = source_path(root, old), source_path(root, new)
    if not source.is_file() or target.exists() or digest(source.read_bytes()) != expected_hash:
        raise ValueError('文件已变化或目标文件已存在。')
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    try:
        from .renpy_import import refresh_native_files, index_sources
        index_path=safe_path(root,document['nativeRenpy']['indexPath'])
        previous=json.loads(index_path.read_text('utf-8')) if index_path.exists() else None
        refresh_native_files(root, document)
        baseline = index_sources(root, document, previous=previous)
        document['revision'] += 1
        atomic_json(safe_path(root, document['nativeRenpy']['indexPath']), baseline)
        atomic_json(project_file(root), document)
    except Exception:
        target.rename(source)
        raise
    tid=uuid.uuid4().hex
    atomic_json(Path(root)/'.creator/editor/history'/(tid+'.json'),{'kind':'rename','old':old,'new':new,'hash':expected_hash})
    return {'project': document, 'root': str(root), 'transaction':tid}
