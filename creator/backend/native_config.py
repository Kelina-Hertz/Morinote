"""Morinote configuration adapters. Parse expressions; never execute game Python."""
from __future__ import annotations
import ast
import hashlib
import re
from pathlib import Path
from .workspace import read_document, read_overlay
from .story_profile import canonical_file, preferred_files

GROUPS = [
    ('phone', '手机外观与音效', 'message_system.rpy', ('phone_', 'p_', 'top_', 'title_position', 'intro_position', 'audio.phone')),
    ('roles', '手机人物与头像', 'message.rpy', ('phone_avatars',)),
    ('contacts', '通讯录', 'contact_system.rpy', ('contact_registry', 'contact_list')),
    ('ova', 'OVA 目录', 'ova.rpy', ('OVA_NOVELS',)),
    ('achievements', '成就', 'achievements.rpy', ('ACHIEVEMENTS',)),
    ('sounds', 'UI 音效', '00_ui_sounds.rpy', ('ui_hover_sound', 'ui_click_sound')),
    ('game', '游戏基础配置', 'options.rpy', ('config.name', 'config.version', 'build.name', 'config.window_icon', 'config.main_menu_music', 'config.has_', 'preferences.text_cps', 'preferences.afm_time', 'config.enter_transition', 'config.exit_transition', 'config.intra_transition', 'config.after_load_transition', 'config.end_game_transition')),
    ('sessions','手机会话','message.rpy',()),
    ('fonts','字体','gui.rpy',('gui.text_font','gui.name_text_font','gui.interface_text_font')),
]
LABELS = {'phone_xy':'手机位置','phone_xysize':'手机尺寸','phone_bg':'手机背景','phone_fg':'手机外框',
 'p_frame_xy':'消息区域位置','p_frame_xysize':'消息区域尺寸','p_frame_spacing':'消息间距',
 'phone_avatar_xysize':'头像尺寸','ui_hover_sound':'悬停音效','ui_click_sound':'点击音效',
 'config.name':'游戏标题','config.version':'版本','preferences.text_cps':'默认文字速度','preferences.afm_time':'默认 Auto 速度'}


def value_node(text, start):
    """Parse a multiline assignment RHS without evaluating it."""
    tail = text[start:]
    for end in [m.end() for m in re.finditer('\n', tail)] + [len(tail)]:
        candidate = tail[:end].rstrip()
        try:
            expression = ast.parse(candidate, mode='eval').body
            return expression, candidate
        except SyntaxError:
            continue
    return None, ''


def node_span(expression, node, offset):
    rows = expression.splitlines(keepends=True)
    def at(line, col):
        return sum(len(r) for r in rows[:line-1]) + len(rows[line-1].encode('utf-8')[:col].decode('utf-8'))
    return offset + at(node.lineno, node.col_offset), offset + at(node.end_lineno, node.end_col_offset)


def catalog(root, project, documents=None):
    groups, bindings = [], {}
    for gid, title, filename, prefixes in GROUPS:
        files = [p for p in preferred_files(project['nativeRenpy']['codeFiles']) if canonical_file(p).endswith('/'+filename)]
        group = {'id':gid, 'title':title, 'fields':[], 'tables':[], 'sources':files, 'actions':[]}
        for path in files:
            doc = read_overlay(root, path, documents)
            text = doc['content']
            # Statements may be at top level or nested in init python.
            pattern = r'(?m)^\s*(?:(?:define|default)\s+)?([A-Za-z_]\w*(?:\.\w+)*)\s*=\s*'
            for match in re.finditer(pattern, text):
                name = match[1]
                if not any(name.startswith(p) for p in prefixes): continue
                node, expression = value_node(text, match.end())
                if node is None: continue
                def binding(n, label):
                    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('_','__') and len(n.args)==1 and isinstance(n.args[0],ast.Constant):n=n.args[0]
                    start, end = node_span(expression, n, match.end())
                    raw = text[start:end]
                    bid = hashlib.sha256((path+':'+str(start)+':'+raw).encode()).hexdigest()[:20]
                    try:
                        value = ast.literal_eval(n)
                        editable = isinstance(value, (str, float, int, bool, tuple, list, type(None)))
                    except (ValueError, TypeError):
                        value, editable = raw, False
                    field = {'id':bid,'label':LABELS.get(label,label),'name':label,'value':value,'editable':editable,
                             'expression':raw,'path':path,'line':text[:start].count('\n')+1,
                             'start':start,'end':end,'hash':doc['hash']}
                    if label=='id':field['editable']=False
                    if isinstance(value,tuple): field['value']=list(value); field['tuple']=True
                    if isinstance(value,(str,type(None))):
                        if 'sound' in label or label.startswith('audio.') or 'music' in label: field['assetKind']='audio'
                        elif any(s in label for s in ('avatar','background','_bg','_fg','icon','frame')): field['assetKind']='image'
                    bindings[bid] = field
                    if not editable and 'transition' in label and isinstance(n,ast.Name):field['references']=['None','dissolve','fade','chara_trans']
                    return field
                if name in {'ACHIEVEMENTS','OVA_NOVELS','contact_registry','phone_avatars','contact_list'}:
                    table = binding(node,name)
                    table.update(entries=[], container='dict' if isinstance(node,ast.Dict) else 'sequence')
                    if isinstance(node,ast.Dict):
                        pairs=list(zip(node.keys,node.values))
                    elif isinstance(node,(ast.List,ast.Tuple)):
                        pairs=list(enumerate(node.elts))
                    else: pairs=[]
                    for key, item in pairs:
                        key_name = ast.get_source_segment(expression,key) if isinstance(key,ast.AST) else str(key+1)
                        entry = binding(item,key_name)
                        entry['key']=key_name
                        if isinstance(key, ast.AST): entry['rowStart']=node_span(expression,key,match.end())[0]
                        else: entry['rowStart']=entry['start']
                        if isinstance(item,ast.Dict):
                            entry['fields']=[binding(v,ast.literal_eval(k) if isinstance(k,ast.Constant) else ast.get_source_segment(expression,k)) for k,v in zip(item.keys,item.values) if k is not None]
                        else: entry['fields']=[binding(item,key_name)]
                        table['entries'].append(entry)
                    group['tables'].append(table)
                else:
                    group['fields'].append(binding(node,name))
        groups.append(group)
    action_groups={'contact_':'contacts','unlock_achievement':'achievements','check_achievements':'achievements','ova_mark_completed':'ova','qq_':'sessions'}
    for path in project['nativeRenpy']['codeFiles']:
        if not path.endswith('.rpy'):continue
        doc=read_overlay(root,path,documents);text=doc['content']
        pattern=r'(?m)^[ \t]+(?:\$\s*|call\s+|show screen\s+)((?:contact_\w+|unlock_achievement|check_achievements|ova_mark_completed|qq_\w+)\([^\n]*\))'
        for match in re.finditer(pattern,text):
            try:call=ast.parse(match[1],mode='eval').body
            except SyntaxError:continue
            if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Name):continue
            gid=next((gid for prefix,gid in action_groups.items() if call.func.id.startswith(prefix)),None)
            if not gid:continue
            fields=[]
            for label,arg in [(('聊天标题' if i==0 else '介绍') if gid=='sessions' else ('联系人／ID' if i==0 else '参数 '+str(i+1)),v) for i,v in enumerate(call.args)]+[(kw.arg,kw.value) for kw in call.keywords if kw.arg]:
                start,end=node_span(match[1],arg,match.start(1));raw=text[start:end]
                bid=hashlib.sha256((path+':'+str(start)+':'+raw).encode()).hexdigest()[:20]
                try:value=ast.literal_eval(arg);editable=True
                except (ValueError,TypeError):value=raw;editable=False
                field={'id':bid,'name':label,'label':label,'value':value,'editable':editable,'expression':raw,'path':path,'line':text[:start].count('\n')+1,'start':start,'end':end,'hash':doc['hash']}
                bindings[bid]=field;fields.append(field)
            line=text[:match.start()].count('\n')+1
            label=next((l for l in sorted(project['nativeRenpy']['labels'],key=lambda l:l['line'],reverse=True) if path.endswith('/'+l['file']) and l['line']<=line),None)
            next(g for g in groups if g['id']==gid)['actions'].append({'id':path+':'+str(match.start()),'title':match[1],'path':path,'line':line,'fields':fields,'label':label['id'] if label else None})
    return {'groups':groups,'bindings':bindings}


def edit(root, project, operation):
    data = catalog(root,project,operation.get("documents"))
    field = data['bindings'].get(operation.get('binding'))
    if operation.get('operation') in ('delete','key'):
        field=next((entry for group in data['groups'] for table in group['tables'] for entry in table['entries'] if entry['id']==operation.get('binding')),field)
    if not field: raise ValueError('配置位置已变化，请刷新后重新选择。')
    doc = read_overlay(root,field['path'],operation.get('documents'))
    if operation.get('hash') != doc['hash']: raise ValueError('配置源码已变化，请先刷新或比较差异。')
    start,end = field['start'],field['end']
    op = operation.get('operation','set')
    if op == 'set':
        if not field['editable'] and not field.get('references'): raise ValueError('此字段包含代码表达式，请使用源码编辑。')
        value = operation.get('value')
        if field.get('tuple') and isinstance(value,list): value=tuple(value)
        replacement=repr(value)
        if field.get('references'):
            if value not in field['references']:raise ValueError('请选择项目支持的转场。')
            replacement=value
    elif op == 'append':
        expression = field['expression']
        close = end - len(expression) + max(expression.rfind(']'),expression.rfind(')'),expression.rfind('}'))
        if close < start: raise ValueError('此配置不是可追加的列表或字典。')
        start=end=close
        value=operation['value']
        replacement=repr(value)
        if field.get('container')=='dict': replacement=repr(operation['key'])+': '+replacement
        inner=doc['content'][field['start']+1:close].rstrip()
        replacement=(',' if inner and not inner.endswith(',') else '')+'\n        '+replacement+',\n    '
    elif op == 'delete':
        start=field.get('rowStart',start)
        rest=doc['content'][end:]
        comma=re.match(r'[ \t]*,',rest)
        if comma: end+=comma.end()
        else:
            prev=doc['content'][:start].rstrip()
            if prev.endswith(','): start=len(prev)-1
        replacement=''
    elif op == 'key':
        if 'rowStart' not in field or field['rowStart']==start:raise ValueError('此条目没有可修改的字典键。')
        start=field['rowStart'];end=start+len(field['key'])
        if not isinstance(operation['value'],str):raise ValueError('键必须为文字。')
        replacement=repr(operation['value'])
    else: raise ValueError('无效配置操作。')
    return {'path':field['path'],'hash':doc['hash'],'content':doc['content'][:start]+replacement+doc['content'][end:]}
