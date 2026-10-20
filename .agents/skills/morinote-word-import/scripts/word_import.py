"""Word source extraction and IDE indexing; no model, engine, lint or play launch."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
W14 = '{http://schemas.microsoft.com/office/word/2010/wordml}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
REMOVED = {W+'del', W+'moveFrom'}
MAX_XML = 16*1024*1024


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('w', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def xml_member(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_XML:
        raise ValueError('Word XML 过大：'+name)
    return ET.fromstring(archive.read(info))


def paragraph_text(paragraph):
    result = []
    def walk(node):
        if node is not paragraph and node.tag == W+'p' or node.tag in REMOVED:
            return
        if node.tag == W+'t': result.append(node.text or '')
        elif node.tag == W+'tab': result.append('\t')
        elif node.tag in {W+'br', W+'cr'}: result.append('\n')
        elif node.tag == W+'noBreakHyphen': result.append('\u2011')
        elif node.tag == W+'softHyphen': result.append('\u00ad')
        for child in node: walk(child)
    walk(paragraph)
    return ''.join(result)


def extract(args):
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if source.suffix.lower() != '.docx': raise ValueError('仅支持 .docx；旧 .doc 请先另存为 .docx。')
    if source.stat().st_size > 64*1024*1024: raise ValueError('Word 文件超过 64 MiB。')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('输出目录已有内容，请为本次导入选择新的版本目录。')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with zipfile.ZipFile(source) as archive:
        tree = xml_member(archive, 'word/document.xml')
        body = tree.find(W+'body')
        if body is None: raise ValueError('Word 中没有正文。')
        parents = {child: parent for parent in body.iter() for child in parent}
        tables = {node: i for i, node in enumerate(body.iter(W+'tbl'), 1)}
        paragraphs, seen, skipped = [], Counter(), 0
        for number, paragraph in enumerate(body.iter(W+'p'), 1):
            ancestors, node = [], paragraph
            while node in parents:
                node = parents[node]; ancestors.append(node)
            if any(a.tag in REMOVED for a in ancestors): skipped += 1; continue
            text = paragraph_text(paragraph)
            drawings = []
            def picture_ids(node):
                if node is not paragraph and node.tag == W+'p' or node.tag in REMOVED: return
                if node.tag == A+'blip':
                    rid = node.get(R+'embed') or node.get(R+'link')
                    if rid: drawings.append(rid)
                if node.tag.endswith('}imagedata') and node.get(R+'id'): drawings.append(node.get(R+'id'))
                for child in node: picture_ids(child)
            picture_ids(paragraph)
            if not text.strip() and not drawings: continue
            word_id = paragraph.get(W14+'paraId')
            key = 'p_'+word_id.lower() if word_id else f'p{number:06d}'
            seen[key] += 1
            if seen[key] > 1: key += '_'+str(seen[key])
            props = paragraph.find(W+'pPr')
            style = props.find(W+'pStyle') if props is not None else None
            numbering = props.find(W+'numPr') if props is not None else None
            record = {'id': key, 'index': number, 'text': text,
                      'style': style.get(W+'val', '') if style is not None else '',
                      'numbering': {c.tag.removeprefix(W): c.get(W+'val') for c in numbering} if numbering is not None else None,
                      'images': drawings}
            cell = next((a for a in ancestors if a.tag == W+'tc'), None)
            row = next((a for a in ancestors if a.tag == W+'tr'), None)
            table = next((a for a in ancestors if a.tag == W+'tbl'), None)
            if cell is not None and row is not None and table is not None:
                record['table'] = {'id': tables[table], 'row': list(table.iter(W+'tr')).index(row)+1,
                                   'cell': list(row.iter(W+'tc')).index(cell)+1}
            paragraphs.append(record)
        relationships = []
        rel_name = 'word/_rels/document.xml.rels'
        if rel_name in archive.namelist():
            relationships = [{'id': n.get('Id'), 'target': n.get('Target'), 'mode': n.get('TargetMode', 'Internal'),
                              'type': n.get('Type', '').rsplit('/', 1)[-1]} for n in xml_member(archive, rel_name)]
        ancillary = {}
        for name in ('footnotes', 'endnotes', 'comments'):
            member = 'word/'+name+'.xml'
            if member in archive.namelist():
                ancillary[name] = [paragraph_text(p) for p in xml_member(archive, member).iter(W+'p') if paragraph_text(p).strip()]
        changes = {name: sum(1 for _ in body.iter(W+name)) for name in ('ins', 'del', 'moveFrom', 'moveTo')}
    warnings = []
    if any(changes.values()): warnings.append('存在修订；正文保留插入和移入，排除删除和移出，请核对修订意图。')
    if ancillary: warnings.append('存在脚注、尾注或批注，已单独提取，尚未归入玩家正文。')
    if any(p['images'] for p in paragraphs): warnings.append('存在内嵌／引用图片，仅登记关系，未自动复制为游戏素材。')
    if any(p['numbering'] is not None for p in paragraphs): warnings.append('存在自动列表编号；已登记编号属性，但未将 Word 显示编号伪造为正文，请核对选项和列表结构。')
    if any(n > 1 for n in seen.values()): warnings.append('存在重复 Word 段落 ID，已添加后缀，请核对后续版本匹配。')
    if any(not p.get('id', '').startswith('p_') for p in paragraphs): warnings.append('部分段落没有 Word 稳定 ID；插入段落后需按原文与上下文匹配旧节点，不能按新句序覆盖。')
    result = {'version': 1, 'source': {'filename': source.name, 'sha256': digest, 'revision_view': 'insertions-included-deletions-excluded'},
              'paragraphs': paragraphs, 'relationships': relationships, 'ancillary': ancillary,
              'tracked_changes': changes, 'skipped_deleted_paragraphs': skipped, 'warnings': warnings}
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output/'source.docx')
    if hashlib.sha256((output/'source.docx').read_bytes()).hexdigest() != digest:
        raise ValueError('提取期间原 Word 发生变化，保留输出供比较，请使用新目录重新提取。')
    write_json(output/'source.json', result)
    (output/'source.txt').write_text('\n\n'.join('['+p['id']+']'+(' '+str(p['table']) if 'table' in p else '')+'\n'+p['text'] for p in paragraphs)+'\n', encoding='utf-8')
    return {'output': str(output), 'paragraphs': len(paragraphs), 'source_sha256': digest, 'warnings': warnings}


def coverage(args):
    source_path = Path(args.source).resolve()
    source = json.loads(source_path.read_text('utf-8-sig'))
    mapping = json.loads(Path(args.map).read_text('utf-8-sig'))
    original = {p['id']: p for p in source['paragraphs']}
    rows, nodes = mapping.get('paragraphs', []), mapping.get('nodes', [])
    errors, pending = [], []
    if source.get('version') != 1 or mapping.get('version') != 1: errors.append('不支持的来源映射版本。')
    if mapping.get('source_sha256') != source['source']['sha256']: errors.append('来源摘要不匹配。')
    preserved = source_path.with_name('source.docx')
    if not preserved.is_file() or hashlib.sha256(preserved.read_bytes()).hexdigest() != source['source']['sha256']:
        errors.append('原 Word 副本不存在或已变化。')
    ids = [n['id'] for n in nodes]
    if len(ids) != len(set(ids)): errors.append('节点 ID 重复。')
    node_ids, row_counts = set(ids), Counter(r['id'] for r in rows)
    for pid in original:
        if row_counts[pid] != 1: errors.append(pid+'：来源处置缺失或重复。')
    by_node = {n['id']: set(n.get('paragraph_ids', [])) for n in nodes}
    for row in rows:
        pid = row['id']
        if pid not in original: errors.append(pid+'：未知段落。'); continue
        if row.get('original') != original[pid]['text']: errors.append(pid+'：登记的原文与提取结果不同。')
        kind = row.get('disposition')
        if kind not in {'text', 'direction', 'note', 'heading', 'pending'}: errors.append(pid+'：未知处置。')
        if kind == 'pending': pending.append(pid)
        if kind != 'text' and not str(row.get('reason', '')).strip(): errors.append(pid+'：非正文处置需说明理由。')
        refs = row.get('node_ids', [])
        if kind == 'text' and not refs: errors.append(pid+'：正文没有对应节点。')
        for nid in refs:
            if nid not in node_ids or pid not in by_node[nid]: errors.append(pid+'：节点来源关系不匹配：'+nid)
    for node in nodes:
        refs = node.get('paragraph_ids', [])
        if not refs or any(p not in original for p in refs): errors.append(node['id']+'：节点来源缺失或不在原文中。')
        if any(node['id'] not in next((r.get('node_ids', []) for r in rows if r['id'] == pid), []) for pid in refs):
            errors.append(node['id']+'：来源段落没有反向关联节点。')
    result = {'ok': not errors and not pending, 'paragraphs': len(original), 'nodes': len(nodes),
              'errors': errors, 'pending': pending, 'scope': '只核对来源登记；不证明 RPY 正文、字符串转义、分支或运行效果正确。'}
    if args.output: write_json(Path(args.output), result)
    return result


def refresh(args):
    root = Path(args.project).expanduser().resolve()
    backend = root/'creator/backend/renpy_import.py'
    if not (root/'game').is_dir() or not backend.is_file():
        raise ValueError('请选择同时包含 game/ 和 creator/backend/ 的仓库根目录。')
    patch = json.loads(Path(args.metadata).read_text('utf-8-sig')) if args.metadata else {}
    allowed = {'sceneTitles', 'flowGroups', 'flowRoles'}
    if not isinstance(patch, dict) or set(patch)-allowed or any(not isinstance(v, dict) for v in patch.values()):
        raise ValueError('元数据只支持 sceneTitles、flowGroups、flowRoles 字典。')
    sys.path.insert(0, str(root/'creator'))
    from backend.project import atomic_json, load_project, project_file
    from backend.renpy_import import open_native
    descriptor = root/'.creator/editor/project.json'
    if args.expected_revision is not None:
        if not descriptor.is_file() or load_project(root)['revision'] != args.expected_revision:
            raise ValueError('IDE 版本已变化，请重新读取并比较后刷新。')
    root, project = open_native(root)
    labels = project['nativeRenpy']['labels']
    for field, values in patch.items():
        target = project.setdefault('ide', {}).setdefault(field, {})
        for key, value in values.items():
            found = [label for label in labels if label['name'] == key or label['id'] == key]
            if len(found) != 1 or not isinstance(value, str) or not value.strip() or len(value) > 120:
                raise ValueError('名称或 label 无效／不唯一：'+str(key))
            if field == 'flowRoles' and value not in {'story', 'conversation', 'system', 'test'}:
                raise ValueError('无效流程角色：'+value)
            # Display names use stable label IDs; graph grouping uses names.
            label = found[0]
            target[label['id'] if field == 'sceneTitles' else label['name']] = value
    if patch:
        path = project_file(root)
        if json.loads(path.read_text('utf-8-sig'))['revision'] != project['revision']:
            raise ValueError('刷新期间项目又有变化，未覆盖元数据，请重新读取。')
        project['revision'] += 1
        atomic_json(path, project)
    return {'project': str(root), 'revision': project['revision'], 'labels': len(labels),
            'indexed_only': True, 'message': '已从 RPY 刷新 IDE 索引；未启动引擎或修改剧情源码。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    cmd = commands.add_parser('extract'); cmd.add_argument('input'); cmd.add_argument('--output', required=True); cmd.set_defaults(action=extract)
    cmd = commands.add_parser('coverage'); cmd.add_argument('--source', required=True); cmd.add_argument('--map', required=True); cmd.add_argument('--output'); cmd.set_defaults(action=coverage)
    cmd = commands.add_parser('refresh'); cmd.add_argument('--project', required=True); cmd.add_argument('--metadata'); cmd.add_argument('--expected-revision', type=int); cmd.set_defaults(action=refresh)
    args = parser.parse_args()
    try:
        result = args.action(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('ok') is False else 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
