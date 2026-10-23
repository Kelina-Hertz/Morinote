"""Conservative source-backed exits for graph authoring. Never evaluates game code."""
from __future__ import annotations

import ast
import hashlib
import re
from collections import Counter, defaultdict

from .workspace import read_overlay
from .story_profile import preferred_labels

PENDING_OUTLET = ' # morinote-outlet: pending'
PENDING_PATTERN = re.compile(r'[ \t]*#[ \t]*morinote-outlet:[ \t]*pending\b')


def outlet_comment(comment, pending=False):
    """Only remove our outlet annotation; keep the writer's original comment."""
    clean = PENDING_PATTERN.sub('', comment)
    return clean + PENDING_OUTLET if pending else clean


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def label_path(project, label, documents):
    """Resolve the indexed file exactly; equal basenames are not interchangeable."""
    paths = {item['projectPath'] for item in project['nativeRenpy']['files']
             if item['gamePath'] == label['file'] and item['projectPath'] in documents}
    return next(iter(paths)) if len(paths) == 1 else None


def uncomment(line):
    quote = None
    escaped = False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == '\\' and quote:
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == '#':
            return line[:i].rstrip(), line[len(line[:i].rstrip()):]
    return line.rstrip(), ''


def simple_assignment(text):
    try:
        tree = ast.parse(text.lstrip()[1:].strip())
        return len(tree.body) == 1 and isinstance(tree.body[0], (ast.Assign, ast.AugAssign)) and not any(
            isinstance(n, (ast.Call, ast.Await, ast.Yield, ast.NamedExpr)) for n in ast.walk(tree))
    except (SyntaxError, ValueError):
        return False


def dynamic_statement(text):
    return bool(re.match(r'(?:python\b|call\s+(?:expression|screen)\b|show\s+screen\b|jump\s+expression\b)', text)) or text.startswith('$') and not simple_assignment(text)


def condition_expression(value):
    if not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value:
        raise ValueError('请填写单行判断条件。')
    if uncomment(value)[1]:
        raise ValueError('判断条件中不能包含行尾注释。')
    try:
        tree = ast.parse(value.strip(), mode='eval')
    except (SyntaxError, ValueError) as exc:
        raise ValueError('判断条件格式不正确，请检查变量、比较方式和数值。') from exc
    if any(isinstance(n, (ast.Call, ast.Await, ast.Yield, ast.Lambda, ast.NamedExpr,
                          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) for n in ast.walk(tree)):
        raise ValueError('图上判断仅支持变量、比较和逻辑表达式，函数调用请使用源码。')
    return value.strip()


def ordinary(statement):
    text = statement['text']
    if text.startswith('$'):
        return simple_assignment(text)
    if re.match(r'call\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?:\([^\n]*\))?(?:\s+from\s+[A-Za-z_]\w*)?$', text):
        return not text.startswith(('call expression', 'call screen'))
    if re.match(r'(?:show|scene|hide|with|play|stop|queue|voice|pause|window|nvl|extend|centered|pass)\b', text):
        # ATL blocks are display instructions; Python/functions remain opaque.
        return not any(re.match(r'(?:python|function)\b', row['text']) for row in statement['children'])
    # Standard say statements, including speaker attributes and say arguments.
    return bool(re.match(r'''(?:(?:[\w.]+[ \t]+)+)?["']''', text)) and not statement['children']


def blocks(label, document):
    rows = document['content'].splitlines(keepends=True)
    offsets = [0]
    for row in rows:
        offsets.append(offsets[-1] + len(row))
    start = label['line']
    end = next((i for i in range(start, len(rows)) if rows[i].strip() and not rows[i][0].isspace() and not rows[i].lstrip().startswith('#')), len(rows))
    code = []
    for i in range(start, end):
        raw = rows[i].rstrip('\r\n')
        clean, comment = uncomment(raw)
        if not clean.strip():
            continue
        indent = clean[:len(clean)-len(clean.lstrip())]
        code.append({'row': i, 'line': i+1, 'start': offsets[i], 'end': offsets[i]+len(raw), 'after': offsets[i+1],
                     'indent': indent, 'level': len(indent.expandtabs(8)), 'text': clean.strip(), 'comment': comment})
    level = min((r['level'] for r in code), default=4)
    top = []
    for row in code:
        if row['level'] == level:
            top.append({**row, 'children': []})
        elif top:
            top[-1]['children'].append(row)
    return top, code, end, rows


def catalog(root, project, flow, sources=None):
    labels = project['nativeRenpy']['labels']
    active_labels = preferred_labels(project)
    active_ids = {label['id'] for label in active_labels}
    by_id = {label['id']: label for label in labels}
    counts = Counter(label['name'] for label in active_labels)
    by_name = {label['name']: label for label in active_labels if counts[label['name']] == 1}
    documents = {p: read_overlay(root, p, sources) for p in project['nativeRenpy']['codeFiles'] if p.endswith('.rpy')}
    fingerprints = {path: {'hash': doc['hash'], 'contentHash': digest(doc['content'])} for path, doc in documents.items()}
    scene_nodes = {n['id']: n for n in flow['nodes'] if n['type'] == 'scene'}
    points, scene_points, menu_points, conditions, reasons, opaque = {}, {}, {}, {}, {}, set()
    statement_points = {}

    def target_reason(label):
        if label['id'] not in active_ids:
            return '当前采用编号版本，此副本仅供查看。'
        if counts[label['name']] != 1:
            return '标签重复，无法确定运行目标。'
        if label.get('parameters') not in ('', '()'):
            return '带参数声明的场景请通过源码连接。'
        if label['name'].startswith('.') or '.' in label['name']:
            return '局部标签请通过源码连接。'
        return ''

    def destination(text, owner):
        if text == 'return':
            return None, ''
        match = re.fullmatch(r'jump\s+([\w.]+)', text)
        if not match or match[1] == 'expression':
            return None, '出口不是可安全编辑的静态跳转或无返回值 return。'
        name = owner['name'].split('.')[0]+match[1] if match[1].startswith('.') else match[1]
        target = by_name.get(name)
        if not target:
            return None, '目标不存在或标签重复，无法安全编辑。'
        return target['id'], target_reason(target)

    def point(owner, row, kind, target=None, actions=None, title=''):
        path = label_path(project, owner, documents)
        doc = documents[path]
        identity = f"{owner['id']}:{row['start']}:{kind}:{doc['content'][row['start']:row['end']]}"
        pid = 'exit_'+digest(identity)[:20]
        capabilities = list(actions or ['connect', 'insert', 'branch'])
        if 'connect' in capabilities:
            capabilities.append('end')
        status = 'connected' if target or kind in ('menu', 'condition') else 'pending' if PENDING_PATTERN.search(row.get('comment', '')) else 'ended'
        result = {'id': pid, 'owner': owner['id'], 'kind': kind, 'target': target, 'title': title, 'status': status,
                  'actions': capabilities,
                  'source': {'path': path, 'line': row['line'], 'start': row['start'], 'end': row['end'], 'hash': doc['hash']},
                  'contentHash': digest(doc['content']), 'indent': row['indent'], 'comment': row.get('comment','')}
        points[pid] = result
        if kind not in ('fallthrough', 'menu', 'condition'):
            statement_points[(owner['id'], row['line'])] = pid
        return result

    for label in labels:
        path = label_path(project, label, documents)
        if not path:
            reasons[label['id']] = '源码文件位置存在歧义，请通过源码检查。'
            continue
        top, code, end, rows = blocks(label, documents[path])
        if any(dynamic_statement(r['text']) for r in code):
            opaque.add(label['id'])
        # Multiline strings are opaque to this intentionally small scanner.
        reason = target_reason(label)
        if any('"""' in r['text'] or "'''" in r['text'] for r in code):
            reason = reason or '场景含多行字符串，无法安全定位出口。'
            opaque.add(label['id'])
        if not top:
            reasons[label['id']] = reason or '场景没有可定位的有效语句。'
            continue
        tail = top[-1]
        conditional = len(top) >= 2 and top[-2]['text'].startswith('if ') and top[-2]['text'].endswith(':') and tail['text'] == 'else:'
        # A terminal menu's individual static exits remain locatable even when
        # earlier story code is opaque. Never turn those into a whole-scene exit.
        terminal_menu = bool(re.fullmatch(r'menu(?:\s+\w+)?\s*:', tail['text']))
        if not terminal_menu:
            if any(not ordinary(row) for row in (top[:-2] if conditional else top[:-1])):
                reason = reason or '场景含多个控制出口或复杂控制流，请选择具体出口或编辑源码。'
            if any(n['label']==label['id'] and n.get('unresolved') for n in flow['nodes']):
                reason = reason or '场景含无法确定目标的跳转或子剧情调用。'
        if reason:
            reasons[label['id']] = reason
            continue
        if conditional:
            header = top[-2]
            try:
                expression = condition_expression(header['text'][3:-1])
            except ValueError as exc:
                reasons[label['id']] = str(exc)
                opaque.add(label['id'])
                continue
            control = next((n for n in flow['nodes'] if n['label'] == label['id'] and n['type'] == 'condition' and n['source']['line'] == header['line']), None)
            exits = []
            for title, row in (('是', header), ('否', tail)):
                if len(row['children']) != 1:
                    reason = '判断分支含复杂内容，请通过源码编辑。'
                    break
                target, problem = destination(row['children'][0]['text'], label)
                if problem:
                    reason = problem
                    break
                exits.append((title, row['children'][0], target))
            if reason or not control:
                reasons[label['id']] = reason or '无法安全定位判断节点。'
                continue
            edit = point(label, header, 'condition', actions=['condition'], title=expression)
            edit['node'] = control['id']
            outputs = []
            for title, row, target in exits:
                output = point(label, row, 'option', target, ['connect'], title)
                output['node'] = control['id']
                outputs.append(output['id'])
            conditions[control['id']] = {'conditionPoint': edit['id'], 'conditionExpression': expression, 'optionPoints': outputs}
            if label.get('blockKind') == 'condition' and len(top) == 2 and label['id'] in scene_nodes:
                scene_nodes[label['id']].update(blockKind='condition', controlNode=control['id'], **conditions[control['id']])
            reasons[label['id']] = '请从判断的“是／否”出口拖线。'
            continue
        if re.fullmatch(r'menu(?:\s+\w+)?\s*:', tail['text']):
            options = []
            children = tail['children']
            menu_level = min((r['level'] for r in children), default=tail['level']+4)
            headers = [i for i, row in enumerate(children) if row['level'] == menu_level]
            for index, i in enumerate(headers):
                header = children[i]
                body = children[i+1:headers[index+1] if index+1<len(headers) else len(children)]
                try:
                    text = ast.literal_eval(header['text'][:-1]) if header['text'].endswith(':') else None
                except (ValueError, SyntaxError):
                    text = None
                if not isinstance(text, str) or len(body)!=1:
                    reason = '选项含条件或复杂分支内容，仅支持单一静态跳转或 return 的选项。'
                    break
                target, problem = destination(body[0]['text'], label)
                if problem:
                    reason = problem
                    break
                options.append((text, body[0], target, header))
            if not options or reason:
                reasons[label['id']] = reason or '无法安全识别选项内容。'
                continue
            # Locate the exact raw menu node rather than relying on editorial edges.
            menu = next((n for n in flow['nodes'] if n['label']==label['id'] and n['type']=='choice' and n['source']['line']==tail['line']), None)
            if not menu:
                reasons[label['id']] = '无法定位选项源码。'
                continue
            append_row = {**tail, 'start': children[-1]['after'], 'end': children[-1]['after']}
            menu_point = point(label, append_row, 'menu', actions=['branch'])
            menu_point['node'] = menu['id']
            menu_point['optionIndent'] = children[headers[0]]['indent']
            menu_point['bodyIndent'] = options[0][1]['indent']
            menu_point['options'] = []
            for text, row, target, header in options:
                option = point(label, row, 'option', target, ['connect', 'rename'], text)
                option['header'] = {key:header[key] for key in ('start','end','line','indent','comment')}
                option['node'] = menu['id']
                menu_point['options'].append(option['id'])
            menu_points[menu['id']] = menu_point['id']
            if label.get('blockKind') == 'choice' and len(top) == 1 and label['id'] in scene_nodes:
                scene_nodes[label['id']].update(blockKind='choice', controlNode=menu['id'], branchPoint=menu_point['id'], optionPoints=menu_point['options'])
            reasons[label['id']] = '场景以选项结束，请编辑具体分支出口。'
            continue
        target, problem = destination(tail['text'], label)
        if not problem and not tail['children']:
            scene_points[label['id']] = point(label, tail, 'return' if tail['text']=='return' else 'jump', target)['id']
        elif ordinary(tail):
            following = next((l for l in labels if l['file']==label['file'] and l['line']==end+1), None)
            if end<len(rows) and following is None:
                reasons[label['id']] = '场景后的源码结构不明确，不能自动插入跳转。'
                continue
            if following and target_reason(following):
                reasons[label['id']] = target_reason(following)
                continue
            last = code[-1]
            insertion = {**tail, 'start': last['after'], 'end': last['after'], 'comment': ''}
            scene_points[label['id']] = point(label, insertion, 'fallthrough', following['id'] if following else None)['id']
        else:
            reasons[label['id']] = problem or '场景出口包含复杂控制流。'

    # Attach source-backed provenance before the editorial graph compresses jumps/calls.
    for node in flow['nodes']:
        if node['type']=='scene':
            node['editPoint'] = scene_points.get(node['id'])
            node['blockedReason'] = reasons.get(node['id'], '')
        elif node['type']=='choice':
            node['branchPoint'] = menu_points.get(node['id'])
            node['optionPoints'] = points[menu_points[node['id']]]['options'] if node['id'] in menu_points else []
            node['blockedReason'] = '' if node['id'] in menu_points else reasons.get(node['label'], '复杂选项请编辑源码。')
        elif node['type']=='condition':
            node.update(conditions.get(node['id'], {}))
            node['blockedReason'] = '' if node['id'] in conditions else reasons.get(node['label'], '复杂判断请编辑源码。')
        elif (node['label'],node['source']['line']) in statement_points:
            node['editPoint'] = statement_points[(node['label'],node['source']['line'])]
    raw_by_id = {n['id']: n for n in flow['nodes']}
    for edge in flow['edges']:
        origin = raw_by_id[edge['source']]
        pid = statement_points.get((origin['label'], origin['source']['line']))
        if origin['type']=='scene' and scene_points.get(origin['id']):
            candidate = points[scene_points[origin['id']]]
            if candidate['kind']=='fallthrough' or raw_by_id[edge['target']]['type']=='return':
                pid = candidate['id']
        if edge['kind'] in ('option', 'yes', 'no'):
            dest = raw_by_id[edge['target']]
            pid = statement_points.get((dest['label'], dest['source']['line']))
        if pid and edge['kind'] not in ('call','return','continuation'):
            edge['editPoint'] = pid

    reachability = reachable(project, flow, opaque)
    for node in flow['nodes']:
        if node['type']=='scene':
            node['reachability'] = reachability.get(node['id'], 'unknown')
    return {'points': points, 'documents': fingerprints,
            'targets': [{'id': l['id'], 'reason': target_reason(l)} for l in labels], 'reachability': reachability}


def reachable(project, flow, opaque):
    """Return summaries avoid following shared return edges into other callers."""
    nodes = {n['id']: n for n in flow['nodes']}
    outgoing = defaultdict(list)
    for edge in flow['edges']:
        if edge['kind']!='return':
            outgoing[edge['source']].append(edge)
    returns = {n['id'] for n in flow['nodes'] if n['type']=='return'}
    changed = True
    while changed:
        changed = False
        for node in flow['nodes']:
            if node['id'] in returns:
                continue
            edges = outgoing[node['id']]
            if node['type']=='call':
                possible = any(e['kind']=='call' and e['target'] in returns for e in edges) and any(e['kind']=='continuation' and e['target'] in returns for e in edges)
            else:
                possible = any(e['target'] in returns for e in edges)
            if possible:
                returns.add(node['id']); changed = True
    labels = preferred_labels(project)
    entries = [l for l in labels if l['name']=='start']
    if not entries:
        graph = next((g for g in project['graphs'] if g['id']==project['entryGraph']), {})
        entries = [l for l in labels if l['id']==graph.get('entry')]
    uncertain = len(entries)!=1 or any(l['name']==entries[0]['name'] for l in labels if entries and l is not entries[0])
    pending = [entries[0]['id']] if not uncertain else []
    seen = set()
    while pending:
        nid = pending.pop()
        if nid in seen or nid not in nodes:
            continue
        seen.add(nid); node = nodes[nid]
        if node.get('unresolved') or node['label'] in opaque:
            uncertain = True
        edges = outgoing[nid]
        if node['type']=='return':
            continue
        for edge in edges:
            if node['type']=='call' and edge['kind']=='continuation':
                callees = [e['target'] for e in edges if e['kind']=='call']
                if not any(c in returns for c in callees):
                    continue
            pending.append(edge['target'])
    return {l['id']: 'reachable' if l['id'] in seen else 'unknown' if uncertain else 'disconnected' for l in project['nativeRenpy']['labels']}


def prepare(root, project, operation):
    from .native_flow import graph, edit
    from .workspace import projection
    sources = operation.get('documents', [])
    expected = operation.get('hashes', {})
    # Check before scanning the indexed line locations: external truncation can
    # otherwise make a stale label point outside its current source document.
    for path, fingerprint in expected.items():
        current = read_overlay(root, path, sources)
        if fingerprint != {'hash': current['hash'], 'contentHash': digest(current['content'])}:
            raise ValueError('相关源码已变化，请重新打开操作：'+path)
    flow = graph(root, project, sources)
    authoring = flow['authoring']
    selected = authoring['points'].get(operation.get('point'))
    action = {'connect_exit':'connect','insert_after':'insert','branch_exit':'branch',
              'create_block':'create','disconnect_exits':'disconnect','end_exits':'end','update_condition':'condition','rename_option':'rename','insert_existing':'splice'}[operation['operation']]
    required = 'connect' if action == 'splice' else action
    if action not in ('create', 'disconnect', 'end') and (not selected or required not in selected['actions']):
        raise ValueError('此出口不能安全编辑，或编辑稿已变化，请重新选择。')
    if action == 'create' and operation.get('point') and (not selected or 'connect' not in selected['actions']):
        raise ValueError('此出口不能接入新剧情块，请重新选择。')
    working = {d['path']: dict(d) for d in sources}
    changed = set()

    def checked(path):
        doc = read_overlay(root, path, sources)
        if expected.get(path)!={'hash': doc['hash'], 'contentHash': digest(doc['content'])}:
            raise ValueError('相关源码已变化，请重新打开操作：'+path)
        return doc

    def target(label_id):
        label = next((l for l in project['nativeRenpy']['labels'] if l['id']==label_id), None)
        capability = next((t for t in authoring['targets'] if t['id']==label_id), None)
        if not label or not capability or capability['reason']:
            raise ValueError(capability['reason'] if capability else '目标场景不存在。')
        path = label_path(project, label, authoring['documents'])
        if not path:
            raise ValueError('目标场景的源码文件位置存在歧义。')
        checked(path)
        return label['name']

    src = selected['source'] if selected else None
    document = checked(src['path']) if src else None
    owner_node = next((n for n in flow['nodes'] if selected and n['id'] == selected['owner']), None)
    old_target = target(selected['target']) if selected and selected['target'] else None
    indent = selected['indent'] if selected else ''
    comment = outlet_comment(selected['comment']) if selected else ''
    created = []

    def continuation(exit):
        return 'jump '+target(exit['target']) if exit and exit['target'] else 'return'+(PENDING_OUTLET if not exit or exit['status']=='pending' else '')

    def new_scene(data, ending='return'+PENDING_OUTLET, body=None, block_kind=None):
        from .scene_metadata import scene_comment
        if not isinstance(data, dict):
            raise ValueError('请填写新场景资料。')
        default_group = owner_node['group'] if owner_node else '剧情'
        scene_comment(data.get('title'),data.get('group',default_group))
        path = data.get('path', 'game/creator_scenes.rpy')
        checked(path)
        spec = {**data, 'operation':'scene', 'documents': list(working.values()), 'blockKind':block_kind}
        spec.setdefault('group', default_group)
        result = edit(root, project, spec)
        name = re.findall(r'^label\s+(\w+):', result['content'], re.M)[-1]
        # Scene creation uses a pending return; replace only its generated tail.
        if body is not None:
            header = '\nlabel '+name+':\n'
            result['content'] = result['content'].rsplit(header, 1)[0]+header+body
        else:
            generated = '    return'+PENDING_OUTLET+'\n'
            if not result['content'].endswith(generated):
                raise ValueError('新场景出口格式已变化，请重新创建。')
            result['content'] = result['content'][:-len(generated)]+'    '+ending+'\n'
        working[result['path']] = result; changed.add(result['path'])
        created.append(name)
        return name

    def replace(text):
        content = document['content']
        if selected['kind'] in ('fallthrough','menu') and src['start'] and not content[:src['start']].endswith(('\n','\r')):
            text = '\n'+text
        if selected['kind'] in ('fallthrough','menu'):
            text += '\n'
        working[src['path']] = {**document, 'content': content[:src['start']]+text+content[src['end']:]}
        changed.add(src['path'])

    if action=='splice':
        scene_id = operation.get('scene')
        following = authoring['points'].get(operation.get('scenePoint'))
        label = next((l for l in project['nativeRenpy']['labels'] if l['id'] == scene_id), None)
        scene_node = next((n for n in flow['nodes'] if n['id'] == scene_id and n['type'] == 'scene'), None)
        if not following or not scene_node or scene_node.get('editPoint') != following['id'] or following['owner'] != scene_id:
            raise ValueError('只能自动插入具有单一简单出口的剧情块。')
        entry = next((g.get('entry') for g in project['graphs'] if g['id'] == project['entryGraph']), None)
        is_entry = label and label['name'] == 'start' or not any(l['name']=='start' for l in project['nativeRenpy']['labels']) and scene_id == entry
        if not label or is_entry or scene_id in (selected['owner'], selected['target']):
            raise ValueError('不能把入口、来源或原目标插入这条连线。')
        if any(e['target'] == scene_id for e in flow['edges']):
            raise ValueError('此剧情块已有入口连接，不能自动插入另一条连线。')
        if following['target'] not in (None, selected['target']):
            raise ValueError('此剧情块已有其他后续，请先断开后再插入。')
        pending, seen = [scene_id], set()
        while pending:
            current = pending.pop()
            if current == selected['owner']:
                raise ValueError('插入会形成循环，请通过连接操作明确设置。')
            if current in seen:
                continue
            seen.add(current)
            pending.extend(e['target'] for e in flow['edges'] if e['source'] == current and e['kind'] != 'return')
        name = target(scene_id)
        old_selected = selected
        replacements = [(selected, 'jump '+name), (following, continuation(selected))]
        for selected, command in sorted(replacements, key=lambda item:item[0]['source']['start'], reverse=True):
            src = selected['source']
            checked(src['path'])
            document = working.get(src['path'], read_overlay(root,src['path'],sources))
            replace(selected['indent']+command+outlet_comment(selected['comment']))
        selected = old_selected
    elif action in ('disconnect', 'end'):
        ids = operation.get('points')
        if not isinstance(ids, list) or not ids or any(not isinstance(pid, str) for pid in ids):
            raise ValueError('请选择要修改的出口。')
        exits = [authoring['points'].get(pid) for pid in set(ids)]
        if any(not p or 'connect' not in p['actions'] for p in exits):
            raise ValueError('出口已变化或不能安全编辑，请重新选择。')
        for exit in sorted(exits, key=lambda p:p['source']['start'], reverse=True):
            selected = exit; src = exit['source']
            checked(src['path'])
            document = working.get(src['path'], read_overlay(root,src['path'],sources))
            replace(exit['indent']+'return'+outlet_comment(exit['comment'], pending=action=='disconnect'))
    elif action=='create':
        data = operation.get('scene')
        kind = operation.get('kind', 'scene')
        original = continuation(selected)
        body = None
        if kind == 'choice':
            options = operation.get('options')
            if not isinstance(options, list) or not options or any(not isinstance(t,str) or not t.strip() for t in options):
                raise ValueError('请至少填写一个非空的分支选项。')
            targets = operation.get('targets', [None] * len(options))
            if not isinstance(targets, list) or len(targets) != len(options) or any(item is not None and not isinstance(item, str) for item in targets):
                raise ValueError('选项目标需与选项逐行对应。')
            commands = ['jump '+target(label_id) if label_id is not None else original if i==0 else 'return'+PENDING_OUTLET
                        for i, label_id in enumerate(targets)]
            body = '    menu:\n'+''.join('        '+repr(text.strip())+':\n            '+commands[i]+'\n' for i,text in enumerate(options))
        elif kind == 'condition':
            expression = condition_expression(operation.get('condition'))
            body = '    if '+expression+':\n        '+original+'\n    else:\n        return'+PENDING_OUTLET+'\n'
        elif kind != 'scene':
            raise ValueError('不支持的剧情块类型。')
        name = new_scene(data, original, body, kind)
        if selected:
            document = working.get(src['path'], document)
            replace(indent+'jump '+name+comment)
    elif action=='condition':
        expression = condition_expression(operation.get('condition'))
        replace(indent+'if '+expression+':'+comment)
    elif action=='rename':
        text = operation.get('text')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('选项文字不能为空。')
        header = selected['header']
        src = {**src, **header}
        replace(header['indent']+repr(text.strip())+':'+header['comment'])
    elif action=='connect':
        replace(indent+'jump '+target(operation.get('target'))+comment)
    elif action=='insert':
        # Patch first, then append, so using the same source file cannot erase either edit.
        data = operation.get('scene', {})
        name = data.get('name')
        if not isinstance(name,str) or not name:
            raise ValueError('新场景缺少生成的标签名称。')
        replace(indent+'jump '+name+comment)
        new_scene(data, continuation(selected))
    else:
        options = operation.get('options')
        if not isinstance(options,list) or not options:
            raise ValueError('请至少添加一个分支选项。')
        # Build all destinations in memory; nothing is applied on partial failure.
        rendered = []
        for index, option in enumerate(options,1):
            if not isinstance(option,dict) or not isinstance(option.get('text'),str) or not option['text'].strip():
                raise ValueError(f'第 {index} 个选项的文字不能为空。')
            dest = option.get('destination', {})
            if not isinstance(dest,dict):
                raise ValueError(f'第 {index} 个选项请选择去向。')
            if dest.get('kind')=='return':
                command = 'return'
            elif dest.get('kind')=='pending':
                command = 'return'+PENDING_OUTLET
            elif dest.get('kind')=='existing':
                command = 'jump '+target(dest.get('label'))
            elif dest.get('kind')=='new':
                command = 'jump '+new_scene(dest.get('scene'))
            else:
                raise ValueError(f'第 {index} 个选项请选择去向。')
            option_indent=selected.get('optionIndent',indent+'    ')
            body_indent=selected.get('bodyIndent',indent+'        ')
            rendered.append(option_indent+repr(option['text'])+':\n'+body_indent+command)
        addition = '\n'.join(rendered)
        if selected['kind']=='menu':
            # New scenes may have been appended to the same source file.
            document = working.get(src['path'], document)
            replace(addition)
        else:
            document = working.get(src['path'], document)
            replace(indent+'menu:'+comment+'\n'+addition)
    edits = [{**working[path], 'exists': read_overlay(root,path,sources)['exists']} for path in sorted(changed)]
    projection(root, project, list({**{d['path']:d for d in sources}, **{d['path']:d for d in edits}}.values()))
    return {'edits': edits, 'createdLabels': created}
