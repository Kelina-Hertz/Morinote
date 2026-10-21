"""Source-owned ATL presets. No imported expressions are evaluated."""
from __future__ import annotations
import copy
import json
import math
import re
import textwrap


def actor_source(root,project,node_id,tag,documents=None):
    """Resolve the selected instance against the same projected source buffers."""
    from .workspace import read_overlay
    scene=next((s for s in project['scenes'] if any(l['id']==node_id for l in s['lines'])),None)
    if scene is None:raise ValueError('文字节点已变化，请重新选择立绘。')
    visual=None
    for line in scene['lines']:
        if line.get('visual') is not None:visual=line['visual']
        if line['id']==node_id:break
    actor=next((s for s in (visual or {}).get('sprites',[]) if s['id']==tag),None)
    source=(actor or {}).get('nativeSource')
    if not source:raise ValueError('此立绘没有可定位的 show 语句，请从场景源码编辑。')
    def snippet(location):
        doc=read_overlay(root,location['path'],documents)
        rows=doc['content'].splitlines(keepends=True)
        start=location['line']-1;end=location.get('endLine',start+1)
        if not 0<=start<end<=len(rows):raise ValueError('立绘源码位置已变化，请刷新。')
        if location.get('statement') is not None and rows[start].rstrip('\r\n')!=location['statement']:
            raise ValueError('立绘源码位置已变化，请刷新。')
        return textwrap.dedent(''.join(rows[start:end])).rstrip()
    command=snippet(source)
    if not command.startswith('show '):raise ValueError('单独预览需要可定位的 show 语句。')
    action_source=source
    named=re.search(r'\bat\s+([\w.]+)',command.splitlines()[0])
    if named and not command.splitlines()[0].rstrip().endswith(':'):
        for path in project['nativeRenpy']['codeFiles']:
            if not path.endswith('.rpy'):continue
            rows=read_overlay(root,path,documents)['content'].splitlines()
            match=next((i for i,row in enumerate(rows) if re.match(r'^transform\s+'+re.escape(named[1])+r'(?:\s*\(|\s*:)',row)),None)
            if match is not None:action_source={'path':path,'line':match+1};break
    background=(visual or {}).get('nativeBackground',{}).get('source')
    return {'source':source,'actionSource':action_source,'command':command,
            'background':snippet(background) if background else 'scene',
            'label':next(l['name'] for l in project['nativeRenpy']['labels'] if l['id']==scene['id'])}


def preview_script(root,project,request):
    item=actor_source(root,project,request.get('nodeId'),request.get('tag'))
    commands=item['background']+'\n'+item['command']
    # This file lives only in the external session search path. It executes the
    # exact authored show/ATL, including named transforms, in the real engine.
    return ('label _cn_motion_clip:\n'+textwrap.indent(commands,'    ')+
            '\n    call screen _cn_motion_controls\n    return\n')

BEGIN = '# creator:motion '
END = '# creator:motion end'
KINDS = {'move','enter_left','enter_right','fadein','jump','shake'}
EASINGS = {'linear','ease','easein','easeout'}


def validate(spec):
    if not isinstance(spec,dict) or spec.get('version')!=1 or spec.get('kind') not in KINDS or spec.get('easing') not in EASINGS:
        raise ValueError('无效立绘动作。')
    if not isinstance(spec.get('tag'),str) or not re.fullmatch(r'\w+',spec['tag']):raise ValueError('无效人物实例。')
    if not isinstance(spec.get('image'),str) or not re.fullmatch(r'[\w ]+',spec['image']):raise ValueError('无效图片标签。')
    if not isinstance(spec.get('nodeId'),str) or type(spec.get('wait')) is not bool:raise ValueError('动作需要文字节点和等待设置。')
    def number(value,low,high):
        if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('动作参数超出范围。')
    number(spec.get('duration'),.05,30);number(spec.get('amplitude'),0,2000)
    if type(spec.get('repeat')) is not int or not 1<=spec['repeat']<=10:raise ValueError('重复次数需为 1 至 10。')
    for key in ('start','end'):
        if not isinstance(spec.get(key),list) or len(spec[key])!=2:raise ValueError('需要动作起止位置。')
        for value in spec[key]:number(value,-100000,100000)
    geom=spec.get('geometry',{})
    for key,low,high in [('zoom',0,100),('xanchor',-10,10),('yanchor',-10,10),('xzoom',-10,10),('zorder',-10000,10000)]:number(geom.get(key),low,high)
    number(spec.get('intrinsicZoom'),.000001,100)
    return spec


def render(spec,indent=''):
    validate(spec)
    # Canonical source makes it possible to detect hand edits before replacing.
    lines=[BEGIN+json.dumps(spec,ensure_ascii=False,sort_keys=True,separators=(',',':')),
           'show '+spec['image']+' as '+spec['tag']+' zorder '+str(int(spec['geometry']['zorder']))+':']
    def num(value):return format(value,'.10g')
    def pos(value):return str(round(value)) # Integers are pixel coordinates in ATL.
    x,y=spec['start'];ex,ey=spec['end'];kind=spec['kind'];duration=spec['duration'];easing=spec['easing']
    if kind in ('jump','shake'):x,y=ex,ey
    for key,value in [('xpos',pos(x)),('ypos',pos(y)),('xanchor',num(spec['geometry']['xanchor'])),('yanchor',num(spec['geometry']['yanchor'])),('zoom',num(spec['geometry']['zoom'])),('xzoom',num(spec['geometry']['xzoom'])),('xoffset','0'),('yoffset','0'),('alpha','0.0' if kind in ('enter_left','enter_right','fadein') else '1.0')]:
        lines.append('    '+key+' '+value)
    if kind=='jump':
        step=num(duration/(2*spec['repeat']))
        for _ in range(spec['repeat']):lines.extend(['    '+easing+' '+step+' ypos '+pos(ey-spec['amplitude']),'    '+easing+' '+step+' ypos '+pos(ey)])
    elif kind=='shake':
        step=num(duration/(3*spec['repeat']))
        for _ in range(spec['repeat']):
            for dx in (-spec['amplitude'],spec['amplitude'],0):lines.append('    '+easing+' '+step+' xpos '+pos(ex+dx))
    else:lines.append('    '+easing+' '+num(duration)+' xpos '+pos(ex)+' ypos '+pos(ey)+' alpha 1.0')
    if spec['wait']:lines.append('$ renpy.pause('+num(duration)+', hard=True)')
    lines.append(END)
    return ''.join(indent+row+'\n' for row in lines)


def blocks(rows):
    for start,row in enumerate(rows):
        stripped=row.strip()
        if not stripped.startswith(BEGIN+'{'):continue
        try:spec=validate(json.loads(stripped[len(BEGIN):]))
        except (ValueError,TypeError,KeyError) as exc:raise ValueError('动作标记已手工修改，请从源码修复。') from exc
        indent=row[:len(row)-len(row.lstrip())]
        end=next((j for j in range(start+1,len(rows)) if rows[j].strip()==END and rows[j].startswith(indent)),None)
        if end is None:raise ValueError('动作边界不完整，请从源码修复。')
        yield start,end+1,spec,indent


def ensure_owned(rows,block):
    start,end,spec,indent=block
    actual=''.join(rows[start:end]).replace('\r\n','\n')
    if actual!=render(spec,indent):raise ValueError('动作代码已手工修改，请从源码调整，未覆盖。')


def edit(root,project,op,doc,i):
    rows=doc['content'].splitlines(keepends=True)
    line=next((l for s in project['scenes'] for l in s['lines'] if l['id']==op.get('nodeId')),None)
    if line is None:raise ValueError('请先选择动作开始的台词。')
    scene=next(s for s in project['scenes'] if line in s['lines'])
    visual=None
    for current in scene['lines']:
        if current.get('visual') is not None:visual=current['visual']
        if current['id']==line['id']:break
    actor=next((a for a in (visual or {}).get('sprites',[]) if a['id']==op.get('tag')),None)
    if actor is None:raise ValueError('当前句没有这个人物，请先添加立绘。')
    existing=[b for b in blocks(rows) if b[2]['nodeId']==line['id'] and b[2]['tag']==actor['id']]
    if len(existing)>1:raise ValueError('此句存在重复动作，请从源码整理。')
    old=existing[0] if existing else None
    if old:ensure_owned(rows,old)
    if op.get('action')=='remove':
        if not old:raise ValueError('本句没有此人物的可移除动作。')
        del rows[old[0]:old[1]]
        return {'path':doc['path'],'hash':doc['hash'],'content':''.join(rows)}
    if actor.get('nativeSource') and re.search(r'\b(?:onlayer|behind)\b',actor['nativeSource'].get('statement','')):
        raise ValueError('此人物使用自定义图层，请从源码设置动作。')
    source=actor.get('nativeOriginal',{});intrinsic=source.get('intrinsicZoom',1)
    if not intrinsic:raise ValueError('图片内置缩放为零，请从源码调整。')
    spec={**op.get('motion',{}),'version':1,'nodeId':line['id'],'tag':actor['id'],'image':source.get('image',''),
          'intrinsicZoom':intrinsic,'geometry':{'zoom':actor['scale']/intrinsic,'xanchor':actor['anchorX'],'yanchor':actor['anchorY'],'xzoom':-1 if actor['flip'] else 1,'zorder':actor['z']}}
    validate(spec)
    if not any(spec['image'] in a.get('nativeAliases',[]) for a in project['assets']):raise ValueError('人物图片标签未登记。')
    indent=rows[i][:len(rows[i])-len(rows[i].lstrip())]
    point=i
    if i and rows[i-1].lstrip().startswith('$ creator_native_auto_prepare('):point=i-1
    if old:
        if old[1]>point or old[3]!=indent:raise ValueError('动作不在当前台词之前，请从源码检查。')
        rows[old[0]:old[1]]=[render(spec,indent)]
    else:rows[point:point]=[render(spec,indent)]
    return {'path':doc['path'],'hash':doc['hash'],'content':''.join(rows)}


def update_owned(root,project,op,doc,i):
    """Keep generated markers valid when regular position/image controls edit them."""
    from .workspace import read_overlay
    rows=doc['content'].splitlines(keepends=True)
    block=next((b for b in blocks(rows) if b[0]<=i<b[1]),None)
    if not block:return None
    ensure_owned(rows,block);start,end,original,indent=block;spec=copy.deepcopy(original)
    if op['operation']=='image':
        from .native_tracks import catalog
        scripts=[({'projectPath':path},read_overlay(root,path,op.get('documents'))['content']) for path in project['nativeRenpy']['codeFiles'] if path.endswith('.rpy')]
        cue=catalog(copy.deepcopy(project),scripts)[1].get(op['value'])
        if not cue:raise ValueError('请选择已登记且可以解析的图片标签。')
        intrinsic=cue['props'].get('zoom',1)
        if not intrinsic:raise ValueError('图片内置缩放为零。')
        spec['geometry']['zoom']*=spec['intrinsicZoom']/intrinsic;spec['intrinsicZoom']=intrinsic;spec['image']=op['value']
    else:
        values=op['values'] if op['operation']=='properties' else {op['property']:op['value']}
        for key,value in values.items():
            if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('无效动作构图数值。')
            if key in ('xpos','ypos'):
                axis=0 if key=='xpos' else 1;spec['end'][axis]=value
                if spec['kind'] in ('jump','shake','fadein'):spec['start'][axis]=value
            elif key in ('zoom','xanchor','yanchor','xzoom','zorder'):
                spec['geometry'][key]=value/spec['intrinsicZoom'] if key=='zoom' and op.get('effective') else value
            else:raise ValueError('此属性请在动作源码中调整。')
    rows[start:end]=[render(spec,indent)]
    return {'path':doc['path'],'hash':doc['hash'],'content':''.join(rows)}
