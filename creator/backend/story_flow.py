"""A story-facing projection. The source CFG remains authoritative and editable."""
from __future__ import annotations
import ast
from pathlib import PurePosixPath
from .story_profile import scene_info


def label_role(label, project):
    """Classify content independently of chapter/file layout metadata."""
    # This imported wrapper only initializes/calls the chapter and returns.
    # Older import metadata marked it as story; keep it in test entry pickers,
    # but never present the wrapper as an extra plot scene or chapter group.
    if label['name']=='C2_1_import' and PurePosixPath(label['file'].replace('\\','/')).name=='script_c2_1_import.rpy':
        return 'test'
    custom=project.get('ide',{}).get('flowRoles',{}).get(label['id']) or project.get('ide',{}).get('flowRoles',{}).get(label['name'])
    if custom in ('story','conversation','system','test'):return custom
    profile = scene_info(project, label)
    if profile.get('role'): return profile['role']
    name=label['name'];path=PurePosixPath(label['file'].replace('\\','/'));base=path.name.lower()
    if 'test_script' in path.parts: return 'test'
    if name.startswith(('_ui_','_creator_')) or name in ('contact_system_demo',):return 'test'
    if name in ('splashscreen','main_menu','before_main_menu','after_load','before_load','quit','before_save','after_warp','hide_windows'):return 'system'
    if base in ('contact_system.rpy','message_system.rpy','story_workflow_runtime.rpy','_ui_qa.rpy','achievements.rpy','screens.rpy') or 'creator_assets' in path.parts:return 'system'
    if base=='message.rpy':return 'conversation'
    scene=next((s for s in project['scenes'] if s['id']==label['id']),None)
    if scene and scene['lines'] and all(l['kind']=='chat' for l in scene['lines']):return 'conversation'
    return 'story'


def narrative_labels(flow):
    by_id={n['id']:n for n in flow['nodes']}
    labels={n['id'] for n in flow['nodes'] if n['type']=='scene' and n.get('role','story')=='story'}
    # A conversation reached by a direct story jump is a story scene. A call
    # remains embedded in its caller and does not create a module on the graph.
    changed=True
    while changed:
        changed=False
        for e in flow['edges']:
            source,target=by_id.get(e['source']),by_id.get(e['target'])
            if not source or not target or e['kind'] in ('call','return'):continue
            if source['label'] in labels and target.get('role')=='conversation' and target['label'] not in labels:
                labels.add(target['label']);changed=True
    return labels


def narrative_detail(flow):
    labels=narrative_labels(flow)
    nodes=[dict(n) for n in flow['nodes'] if n['label'] in labels]
    ids={n['id'] for n in nodes};groups={n['group'] for n in nodes}
    return {'nodes':nodes,'edges':[dict(e) for e in flow['edges'] if e['source'] in ids and e['target'] in ids],
            'groups':[dict(g) for g in flow['groups'] if g['id'] in groups]}


def project_flow(flow):
    included=narrative_labels(flow)
    by_id = {n['id']: n for n in flow['nodes']}
    outgoing = {}
    for edge in flow['edges']:
        outgoing.setdefault(edge['source'], []).append(edge)
    def return_status(start):
        pending=[start];seen=set();uncertain=False
        while pending:
            current=pending.pop()
            if current in seen:continue
            seen.add(current);node=by_id.get(current)
            if not node:continue
            if node['type']=='return':return True
            if node.get('unresolved'):uncertain=True
            pending.extend(e['target'] for e in outgoing.get(current,[]) if e['kind'] not in ('return','call'))
        return None if uncertain else False
    call_status={n['id']:return_status(next((e['target'] for e in outgoing.get(n['id'],[]) if e['kind']=='call'),None))
                 for n in flow['nodes'] if n['type']=='call'}
    kept = {n['id'] for n in flow['nodes']
            if n['type'] not in ('jump', 'call') or n.get('unresolved')
            or n['type']=='call' and call_status[n['id']] is not True}
    nodes = []
    for original in flow['nodes']:
        if original['id'] not in kept or original['label'] not in included:
            continue
        node = dict(original)
        if node['type'] == 'return':
            node['title'] = '结束／返回'
        elif node.get('unresolved'):
            # Literal dynamic jumps are safe to resolve without evaluating Python.
            expression = node['title'].removeprefix('jump expression ').strip()
            try:
                name = ast.literal_eval(expression)
            except (ValueError, SyntaxError):
                name = None
            node['title'] = ('前往 ' + name) if isinstance(name, str) else '运行时确定'
        if node['type'] == 'scene':
            node['calls'] = [dict(c, target=next((e['target'] for e in outgoing.get(c['id'], [])
                                                   if e['kind'] == 'call'), None))
                             for c in sorted(flow['nodes'], key=lambda n: n['source']['line'])
                             if c['label'] == node['id'] and c['type'] == 'call'
                             and next((by_id[e['target']].get('role','story') for e in outgoing.get(c['id'],[]) if e['kind']=='call' and e['target'] in by_id),'story') in ('story','conversation')]
        nodes.append(node)

    edges = []
    for origin in nodes:
        # Return is a terminal in this view. Shared helper returns never fan out
        # to unrelated callers. Calls resume only at their own continuation.
        if origin['type'] == 'return':
            continue
        pending = [(e, frozenset()) for e in outgoing.get(origin['id'], []) if e['kind'] != 'return'
                   and not (origin['type']=='call' and call_status[origin['id']] is False and e['kind']=='continuation')]
        while pending:
            edge, seen = pending.pop(0)
            target = by_id.get(edge['target'])
            if not target or target['id'] in seen:
                continue
            if target['id'] in kept:
                key = (origin['id'], target['id'], edge['title'], edge['kind'])
                if not any((e['source'], e['target'], e['title'], e['kind']) == key for e in edges):
                    edges.append(dict(edge, id='story_' + str(len(edges)), source=origin['id'], target=target['id']))
                continue
            next_edges = outgoing.get(target['id'], [])
            if target['type'] == 'call':
                next_edges = [e for e in next_edges if e['kind'] == 'continuation']
            for nxt in next_edges:
                if nxt['kind'] == 'return':
                    continue
                pending.append((dict(nxt, title=edge['title'], kind=edge['kind']), seen | {target['id']}))
    # A single explicit "return to title" choice is one editorial ending card.
    # Keep both statements intact in the raw CFG and detailed source projection.
    lookup={n['id']:n for n in nodes};folded=set()
    for node in nodes:
        if node['type'] != 'choice': continue
        exits=[e for e in edges if e['source']==node['id']]
        if len(exits)!=1 or exits[0]['kind']!='option': continue
        target=lookup.get(exits[0]['target'])
        if not target or target['type']!='return': continue
        if sum(e['target']==target['id'] for e in edges)!=1: continue
        node['terminal']=True;node['optionTitles']=[exits[0]['title']]
        folded.add(target['id'])
    nodes=[n for n in nodes if n['id'] not in folded]
    ids={n['id'] for n in nodes};groups={n['group'] for n in nodes}
    return {'nodes': nodes, 'edges': [e for e in edges if e['source'] in ids and e['target'] in ids],
            'groups': [g for g in flow['groups'] if g['id'] in groups]}
