"""Project-wide source-linked control flow for standard Ren'Py statements."""
from __future__ import annotations
import hashlib
import re
import uuid
from pathlib import Path
from .workspace import read_document, read_overlay
from .flow_authoring import label_path, uncomment


def graph(root, project, sources=None, *, presentation_labels=None):
    from .story_flow import label_role, narrative_detail
    from .story_profile import scene_info, numbered_copies, preferred_labels, canonical_file
    labels=project['nativeRenpy']['labels'] if presentation_labels is None else presentation_labels
    nodes=[]; edges=[]; groups={}; returns={}; calls=[]; name_ids={}
    visible_ids={label['id'] for label in labels}
    for label in preferred_labels(project):
        if label['id'] in visible_ids: name_ids.setdefault(label['name'],[]).append(label['id'])
    def target(name):
        matches=name_ids.get(name,[])
        return matches[0] if len(matches)==1 else None
    def group(label):
        overrides=project.get('ide',{}).get('flowGroups',{})
        custom=overrides.get(label['id']) or overrides.get(label['name'])
        if not custom:
            custom=next((overrides[l['id']] for l in project['nativeRenpy']['labels'] if l['name']==label['name'] and canonical_file(l['file'])==canonical_file(label['file']) and overrides.get(l['id'])),None)
        if custom: return custom
        if label.get('displayGroup'): return label['displayGroup']
        preset=scene_info(project,label)
        if preset.get('group'): return preset['group']
        m=re.match(r'C(\d+)',label['name'],re.I)
        role=label_role(label,project)
        return '第'+m[1]+'章' if m else '聊天剧情' if role=='conversation' else '番外' if 'ova' in label['file'].lower() and role=='story' else '序章' if label['name']=='start' else '剧情' if role=='story' else '系统与测试'
    def edge(a,b,kind='next',title='',**extra):
        if a and b: edges.append({'id':str(len(edges)), 'source':a,'target':b,'kind':kind,'title':title,**extra})
    documents={}
    for path in project['nativeRenpy']['codeFiles']:
        if path.endswith('.rpy'): documents[path]=read_overlay(root,path,sources)
    for li,label in enumerate(labels):
        path=label_path(project,label,documents)
        if not path: continue
        doc=documents[path]; rows=doc['content'].splitlines(keepends=True)
        offsets=[0]
        for row in rows: offsets.append(offsets[-1]+len(row))
        chapter=group(label); groups.setdefault(chapter,{'id':chapter,'title':chapter})
        end=next((j for j in range(label['line'],len(rows)) if rows[j].strip() and not rows[j][0].isspace() and not rows[j].lstrip().startswith('#')),len(rows))
        items=[]; skip=None; triple=None
        for j in range(label['line'],end):
            raw=rows[j].rstrip('\r\n'); stripped=uncomment(raw)[0].strip(); indent=len(raw)-len(raw.lstrip())
            if triple:
                if raw.count(triple)%2: triple=None
                continue
            if not stripped or stripped.startswith('#'): continue
            ts=next((q for q in ('"""',"'''") if raw.count(q)%2),None)
            if ts: triple=ts; continue
            if skip is not None:
                if indent>skip: continue
                skip=None
            if re.match(r'(?:python\b|(?:show|scene|camera|transform)\b.*:)',stripped): skip=indent; continue
            items.append({'row':j,'text':stripped,'indent':indent})
        def make(item,kind,title=None):
            j=item['row']; nid='flow_'+hashlib.sha256((path+':'+str(j)+':'+item['text']).encode()).hexdigest()[:16]
            nodes.append({'id':nid,'type':kind,'title':title or item['text'],'group':chapter,'label':label['id'],'role':label_role(label,project),
                'source':{'path':path,'line':j+1,'start':offsets[j],'end':offsets[j]+len(rows[j].rstrip('\r\n')),'hash':doc['hash']}})
            return nid
        loop_targets=[]
        def block(start,stop,level,continuation):
            # Construct backwards so call continuations and merges stay explicit.
            statements=[]; i=start
            while i<stop:
                item=items[i]
                if item['indent']<level: break
                j=i+1
                while j<stop and items[j]['indent']>item['indent']: j+=1
                if item['indent']==level: statements.append((i,j))
                i=j
            nxt=continuation
            for a,b in reversed(statements):
                item=items[a]; text=item['text']
                if text.startswith(('elif ','else:')): continue
                if text.startswith('menu') and text.endswith(':'):
                    nid=make(item,'choice','选项')
                    k=a+1
                    while k<b:
                        option=items[k]; q=k+1
                        while q<b and items[q]['indent']>option['indent']: q+=1
                        if option['text'].startswith(('"',"'")) and option['text'].endswith(':'):
                            branch=block(k+1,q,items[k+1]['indent'],nxt) if k+1<q else nxt
                            edge(nid,branch,'option',option['text'][:-1])
                        k=q
                    nxt=nid
                elif text.startswith('if ') and text.endswith(':'):
                    nid=make(item,'condition',text[3:-1])
                    yes=block(a+1,b,items[a+1]['indent'],nxt) if a+1<b else nxt
                    edge(nid,yes,'yes','是')
                    # elif/else siblings are attached to this if, not inferred as independent scenes.
                    no=nxt; index=statements.index((a,b))+1; siblings=[]
                    while index<len(statements) and items[statements[index][0]]['text'].startswith(('elif ','else:')):
                        siblings.append(statements[index]); index+=1
                    for c,d in reversed(siblings):
                        alt=items[c]; branch=block(c+1,d,items[c+1]['indent'],nxt) if c+1<d else nxt
                        if alt['text'].startswith('else:'): no=branch
                        else:
                            alt_id=make(alt,'condition',alt['text'][5:-1]);edge(alt_id,branch,'yes','是');edge(alt_id,no,'no','否');no=alt_id
                    edge(nid,no,'no','否');nxt=nid
                elif text.startswith('while ') and text.endswith(':'):
                    nid=make(item,'loop',text[6:-1]);loop_targets.append((nid,nxt))
                    body=block(a+1,b,items[a+1]['indent'],nid) if a+1<b else nid
                    loop_targets.pop()
                    edge(nid,body,'yes','继续');edge(nid,nxt,'no','结束');nxt=nid
                elif text in ('break','continue') and loop_targets:
                    nid=make(item,'jump',text)
                    edge(nid,loop_targets[-1][1 if text=='break' else 0],text,text);nxt=nid
                elif re.match(r'(?:call|jump)\s+',text) and not text.startswith('call screen '):
                    m=re.match(r'(call|jump)\s+([\w.]+)(.*)',text)
                    if not m: continue
                    kind,name=m[1],m[2]
                    if name.startswith('.'): name=label['name'].split('.')[0]+name
                    nid=make(item,kind,text)
                    dest=target(name) if name!='expression' else None
                    if dest: edge(nid,dest,kind)
                    else:
                        node=nodes[-1];node['unresolved']=True
                    if kind=='call':
                        edge(nid,nxt,'continuation','返回后继续');calls.append((nid,name,nxt))
                    nxt=nid
                elif text=='return' or text.startswith('return '):
                    nid=make(item,'return');returns.setdefault(label['id'],[]).append(nid);nxt=nid
            return nxt
        following=next((l['id'] for l in labels[li+1:] if l['file']==label['file']),None)
        head=block(0,len(items),min((i['indent'] for i in items),default=4),following)
        j=label['line']-1
        nodes.append({'id':label['id'],'type':'scene','title':label['name'],'group':chapter,'label':label['id'],'role':label_role(label,project),
            'source':{'path':path,'line':j+1,'start':offsets[j],'end':offsets[j]+len(rows[j].rstrip('\r\n')),'hash':doc['hash']}})
        edge(label['id'],head)
    for call,name,continuation in calls:
        for ret in returns.get(target(name),[]): edge(ret,continuation,'return','返回',callSite=call)
    result={'nodes':nodes,'edges':edges,'groups':list(groups.values())}
    from .flow_authoring import catalog
    result['authoring']=catalog(root,project,result,sources)
    from .story_flow import project_flow
    result['story']=project_flow(result)
    result['storyDetail']=narrative_detail(result)
    if presentation_labels is None:
        copies=numbered_copies(project)
        if copies:
            # The story view, static targets and authoring use the same numbered
            # default. Other declarations remain accessible in source details.
            preferred=preferred_labels(project)
            display=graph(root,project,sources,presentation_labels=preferred)
            result['story'],result['storyDetail']=display['story'],display['storyDetail']
            result['sourceCopies']=[{'path':'game/'+copy,'original':'game/'+original} for copy,original in sorted(copies.items())]
    return result


def edit(root, project, operation):
    if operation.get('operation') in ('connect_exit','insert_after','branch_exit','create_block','disconnect_exits','end_exits','update_condition','rename_option','insert_existing'):
        from .flow_authoring import prepare
        return prepare(root,project,operation)
    if operation.get('operation')=='scene':
        from .scene_metadata import scene_comment
        path=operation.get('path','game/creator_scenes.rpy')
        if not isinstance(path,str): raise ValueError('源码文件需位于 game/ 内，并以 .rpy 结尾。')
        path=path.replace('\\','/')
        if not path.startswith('game/') or any(p in ('','..','.') for p in path.split('/')) or not path.endswith('.rpy'):
            raise ValueError('源码文件需位于 game/ 内，并以 .rpy 结尾。')
        doc=read_overlay(root,path,operation.get('documents'))
        if operation.get('hash') is not None and operation['hash'] != doc['hash']:
            raise ValueError('流程源码已有修改。')
        names={label['name'] for label in project['nativeRenpy']['labels']}
        # Include newly added disk files and every unsaved source document.
        from .renpy_import import OMIT_DIRS
        paths={p.relative_to(root).as_posix() for p in (Path(root)/'game').rglob('*.rpy') if not any(part in OMIT_DIRS for part in p.relative_to(root).parts)}
        paths.update(d['path'] for d in operation.get('documents',[]) if d['path'].endswith('.rpy'))
        for source in paths:
            names.update(re.findall(r'^label\s+([\w.]+)\s*(?:\([^\n]*\))?\s*:',read_overlay(root,source,operation.get('documents'))['content'],re.M))
        name=operation.get('name')
        if name is None:
            name='scene_'+uuid.uuid4().hex[:12]
            while name in names: name='scene_'+uuid.uuid4().hex[:12]
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z_]\w*',name) or name in names:
            raise ValueError('标签名称无效或已存在。')
        comment=scene_comment(operation['title'],operation.get('group','剧情'),operation.get('blockKind'))+'\n' if 'title' in operation else ''
        from .flow_authoring import PENDING_OUTLET
        return {'path':path,'hash':doc['hash'],'content':doc['content']+'\n\n'+comment+'label '+name+':\n    "新场景"\n    return'+PENDING_OUTLET+'\n'}
    node=next((n for n in graph(root,project,operation.get('documents'))['nodes'] if n['id']==operation.get('node')),None)
    if not node: raise ValueError('流程节点已变化，请刷新。')
    src=node['source'];doc=read_overlay(root,src['path'],operation.get('documents'))
    if operation.get('hash')!=doc['hash']: raise ValueError('流程源码已有修改。')
    raw=doc['content'][src['start']:src['end']]
    kind=operation.get('operation')
    if kind=='target':
        name=operation['target']
        if not any(l['name']==name for l in project['nativeRenpy']['labels']): raise ValueError('目标标签不存在。')
        new=re.sub(r'^(\s*(?:call|jump)\s+)[\w.]+',lambda m:m[1]+name,raw)
        if new==raw: raise ValueError('此节点不是可编辑的静态跳转。')
        return {'path':src['path'],'hash':doc['hash'],'content':doc['content'][:src['start']]+new+doc['content'][src['end']:]}
    if kind in ('choice','condition'):
        indent=' '*(len(raw)-len(raw.lstrip())+(4 if node['type']=='scene' else 0))
        if kind=='choice':
            options=operation.get('options')
            if not isinstance(options,list) or not options: raise ValueError('请至少填写一个选项。')
            for i, option in enumerate(options,1):
                if not isinstance(option,dict) or not isinstance(option.get('text'),str) or not option['text'].strip():
                    raise ValueError(f'第 {i} 个选项的文字不能为空。')
                if not isinstance(option.get('target'),str) or len([l for l in project['nativeRenpy']['labels'] if l['name']==option['target']]) != 1:
                    raise ValueError(f'第 {i} 个选项请选择存在且标签唯一的目标场景。')
            addition=indent+'menu:\n'+''.join(indent+'    '+repr(o['text'])+':\n'+indent+'        jump '+o['target']+'\n' for o in options)
        else:
            condition=operation['condition']
            import ast
            ast.parse(condition,mode='eval')
            if '\n' in condition: raise ValueError('条件必须为单个表达式。')
            for name in (operation['yes'],operation['no']):
                if not any(l['name']==name for l in project['nativeRenpy']['labels']):raise ValueError('目标标签不存在。')
            addition=indent+'if '+condition+':\n'+indent+'    jump '+operation['yes']+'\n'+indent+'else:\n'+indent+'    jump '+operation['no']+'\n'
        point=doc['content'].find('\n',src['end'])+1 if node['type']=='scene' else src['start']
        if point==0:point=len(doc['content'])
        return {'path':src['path'],'hash':doc['hash'],'content':doc['content'][:point]+addition+doc['content'][point:]}
    raise ValueError('不支持此流程操作。')
