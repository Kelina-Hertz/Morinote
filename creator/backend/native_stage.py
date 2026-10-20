"""Minimal source operations for native dialogue, composition and audio."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
import io
import tokenize
from .workspace import read_overlay


def split_comment(line):
    try:
        comment=next((t for t in tokenize.generate_tokens(io.StringIO(line).readline) if t.type==tokenize.COMMENT),None)
    except (tokenize.TokenError,IndentationError):comment=None
    return (line[:comment.start[1]],'#',line[comment.start[1]+1:]) if comment else (line,'','')


def edit(root, project, op):
    if op['operation']=='image_asset':
        asset=next((a for a in project['assets'] if a['id']==op['asset']),None)
        if not asset or (asset.get('status')!='ready' and not asset.get('virtual')) or not asset.get('nativeGamePath'):raise ValueError('请选择已登记的图片或虚拟素材。')
        alias='creator_'+asset['id']
        definitions=read_overlay(root,'game/creator_assets/images.rpy',op.get('documents'))
        definition='\nimage '+alias+' = '+repr(asset['nativeGamePath'])+'\n'
        nested={**op,'operation':'insert','command':('scene ' if (asset['kind']=='background' or op.get('asBackground')) else 'show ')+alias+('' if (asset['kind']=='background' or op.get('asBackground')) else ' as '+alias+':\n    xpos 960\n    ypos 960\n    xanchor 0.5\n    yanchor 0.5')}
        insertion=edit(root,project,nested)
        return {'edits':[{'path':definitions['path'],'hash':definitions['hash'],'content':definitions['content']+definition},insertion]}
    if op.get('nodeId'):
        line=next((l for s in project['scenes'] for l in s['lines'] if l['id']==op['nodeId']),None)
        if line is None:raise ValueError('文字节点已变化，请重新选择。')
        op={**op,'path':'game/'+line['source']['file'],'line':line['source']['line']}
    path=op['path'];doc=read_overlay(root,path,op.get('documents'))
    if op.get('hash')!=doc['hash']:raise ValueError('演出源码已变化，请刷新。')
    rows=doc['content'].splitlines(keepends=True)
    i=int(op['line'])-1
    if op['operation'] in ('property','properties','image'):
        from .native_motion import update_owned
        if not 0<=i<len(rows):raise ValueError('无效源码位置。')
        if op.get('statement') is not None and rows[i].rstrip('\r\n')!=op['statement']:raise ValueError('演出语句位置已变化，请重新选择后编辑。')
        owned=update_owned(root,project,op,doc,i)
        if owned:return owned
    if op['operation']=='properties':
        content=doc['content']
        for prop,value in op['values'].items():
            result=edit(root,project,{**op,'operation':'property','property':prop,'value':value,'documents':[{'path':path,'hash':doc['hash'],'content':content}]})
            content=result['content']
        return {'path':path,'hash':doc['hash'],'content':content}
    if op['operation']=='insert' and i==len(rows):
        return {'path':path,'hash':doc['hash'],'content':doc['content']+('\n' if not doc['content'].endswith('\n') else '')+'\n'.join('    '+s for s in op['command'].splitlines())+'\n'}
    if not 0<=i<len(rows):raise ValueError('无效源码位置。')
    raw=rows[i].rstrip('\r\n');indent=raw[:len(raw)-len(raw.lstrip())];kind=op['operation']
    if op.get('statement') is not None and raw!=op['statement']:raise ValueError('演出语句位置已变化，请重新选择后编辑。')
    if kind=='motion':
        from .native_motion import edit as motion_edit
        return motion_edit(root,project,op,doc,i)
    elif kind=='audio_layer':
        from .native_audio import layer_edit
        return layer_edit(root,project,op,doc,i)
    elif kind=='split_track':
        track=op.get('track');scene=next((s for s in project['scenes'] if any(l['id']==op.get('nodeId') for l in s['lines'])),None)
        if not scene or track not in ('visual','audio'):raise ValueError('请重新选择文字节点。')
        state=None
        for line in scene['lines']:
            if line.get(track) is not None:state=line[track]
            if line['id']==op['nodeId']:break
        if state is None or state.get('nativeUnknown'):raise ValueError('当前状态随路线变化，请先明确设置。')
        commands=[]
        if track=='visual':
            background=state.get('nativeBackground',{}).get('source')
            if not background:raise ValueError('请先选择背景。')
            source=read_overlay(root,background['path'],op.get('documents'))['content'].splitlines()
            original=source[background['line']-1:background['endLine']]
            import textwrap
            commands.append(textwrap.dedent('\n'.join(original)).rstrip())
            for sprite in state.get('sprites',[]):
                original=sprite['nativeOriginal'];props=original.get('props',{})
                command='show '+original['image']+' as '+sprite['id']
                if 'zorder' in props:command+=' zorder '+str(int(props['zorder']))
                values=[(k,v) for k,v in props.items() if k!='zorder']
                if values:command+=':\n'+'\n'.join('    '+k+' '+str(v) for k,v in values)
                commands.append(command)
        else:
            for channel in state:
                cue=state.get(channel)
                if not isinstance(cue,dict):continue
                file_volume=cue.get('fileVolume',cue.get('volume',1))
                multiplier=cue.get('volume',1)/file_volume if file_volume else 1
                commands.append('$ renpy.music.set_volume('+repr(multiplier)+', delay=0, channel='+repr(channel)+')')
        return edit(root,project,{**op,'operation':'insert','boundary':track,'command':'\n'.join(commands)})
    elif kind=='auto_wait':
        from .renpy_import import SAY
        value=op.get('value');match=SAY.match(raw)
        if not match or re.search(r'interact\s*=\s*False',match['tail']):raise ValueError('预填或非文字语句不能设置 Auto 等待。')
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=3600):raise ValueError('Auto 等待需要 0 至 3600 秒。')
        marker=re.compile(r'^\s*\$ creator_native_auto_prepare\(')
        prior=i-1 if i and marker.match(rows[i-1]) else None
        code,sep,comment=split_comment(raw)
        if prior is None and re.search(r'\bafm\s*=',match['tail']):raise ValueError('此句已有手写 Auto 参数，请从源码调整。')
        if value is None:
            if prior is None:return {'path':path,'hash':doc['hash'],'content':doc['content']}
            prefix,tail=code[:match.end('token')],code[match.end('token'):]
            tail=re.sub(r'\bafm\s*=\s*False\s*,?\s*','',tail)
            tail=re.sub(r',\s*\)',')',tail);tail=re.sub(r'\s*\(\s*\)\s*$','',tail)
            code=prefix+tail
            rows[i]=code.rstrip()+(' #'+comment if sep else '')+'\n';del rows[prior]
        else:
            if prior is None:
                tail=code[match.end('token'):].strip()
                if tail.startswith('('):code=code.rstrip()[:-1]+(', ' if tail[1:-1].strip() else '')+'afm=False)'
                else:code=code.rstrip()+' (afm=False)'
                rows[i]=code+(' #'+comment if sep else '')+'\n'
                rows.insert(i,indent+'$ creator_native_auto_prepare('+repr(op.get('nodeId') or path+':'+str(i+1))+', '+repr(value)+')\n')
            else:rows[prior]=re.sub(r',\s*[0-9.eE+-]+\s*\)\s*$',', '+repr(value)+')\n',rows[prior])
        result={'path':path,'hash':doc['hash'],'content':''.join(rows)}
        helper=read_overlay(root,'game/creator_assets/auto.rpy',op.get('documents'))
        if value is not None and helper['content'] and 'def creator_native_auto_prepare(' not in helper['content']:raise ValueError('game/creator_assets/auto.rpy 已有其他自定义内容，未覆盖。请先从源码调整冲突。')
        if value is not None and not helper['exists'] and not helper['content']:
            return {'edits':[result,{'path':helper['path'],'hash':helper['hash'],'content':Path(__file__).with_name('native_auto.rpy').read_text('utf-8')}]}
        return result
    elif kind=='text':
        from .renpy_import import SAY
        m=SAY.match(raw)
        if not m:raise ValueError('此语句请在源码中编辑。')
        rows[i]=raw[:m.start('token')]+json.dumps(op['value'],ensure_ascii=False)+raw[m.end('token'):]+'\n'
    elif kind=='speaker':
        from .renpy_import import SAY
        m=SAY.match(raw);alias=op.get('value','')
        if not m:raise ValueError('此句请使用源码编辑。')
        if alias and not any(c['alias']==alias and c['kind']==op.get('kind','dialogue') for c in project['nativeRenpy'].get('characters',[])):raise ValueError('请选择相应类型的已定义角色。')
        rows[i]=raw[:m.start('who')]+(alias+' ' if alias else '')+raw[m.start('token'):]+'\n'
    elif kind=='delete_text':
        from .renpy_import import SAY
        if not SAY.match(raw):raise ValueError('这里只能删除一条文字语句。')
        del rows[i]
    elif kind=='image':
        alias=op['value']
        if not any(alias in a.get('nativeAliases',[]) for a in project['assets']):raise ValueError('图片标签没有在本项目登记。')
        m=re.match(r'(\s*(?:show|scene)\s+)(.+?)(?=\s+(?:as|at|with|onlayer|zorder|behind)\s+|\s*:\s*$|\s*(?:#.*)?$)',raw)
        if not m:raise ValueError('此图片语句请使用源码编辑。')
        rows[i]=raw[:m.start(2)]+alias+raw[m.end(2):]+'\n'
    elif kind=='property':
        prop=op['property'];value=op['value']
        if prop=='zoom' and op.get('effective'):
            sprite=next((s for scene in project['scenes'] for line in scene['lines'] for s in (line.get('visual') or {}).get('sprites',[])
                         if s.get('nativeSource',{}).get('path')==path and s['nativeSource']['line']==i+1),None)
            intrinsic=(sprite or {}).get('nativeOriginal',{}).get('intrinsicZoom',1)
            if not intrinsic:raise ValueError('原图片缩放为零，请从源码调整。')
            value=value/intrinsic
        if prop not in {'xpos','ypos','xanchor','yanchor','zoom','xzoom','yzoom','alpha','xoffset','yoffset','zorder'} or type(value) not in (int,float) or not math.isfinite(value):raise ValueError('无效画面属性。')
        if not re.match(r'\s*(?:show|scene)\s+(?!screen\b)',raw):raise ValueError('属性需绑定到原 show/scene 语句。')
        if prop=='zorder':
            code,sep,comment=split_comment(raw);suffix=':' if code.rstrip().endswith(':') else '';code=code.rstrip().removesuffix(':')
            if re.search(r'\bzorder\s+[^\s:]+',code):code=re.sub(r'\bzorder\s+[^\s:]+','zorder '+str(int(value)),code)
            elif ' with ' in code:code=code.replace(' with ',' zorder '+str(int(value))+' with ',1)
            else:code+=' zorder '+str(int(value))
            rows[i]=code+suffix+(' #'+comment if sep else '')+'\n'
            return {'path':path,'hash':doc['hash'],'content':''.join(rows)}
        end=i+1
        while end<len(rows) and (not rows[end].strip() or len(rows[end])-len(rows[end].lstrip())>len(indent)):end+=1
        found=False
        for j in range(i+1,end):
            if re.match(r'\s*'+prop+r'\s+',rows[j]) and len(rows[j])-len(rows[j].lstrip())==len(indent)+4:
                rows[j]=re.sub(r'^(\s*'+prop+r'\s+)[^#\r\n]+',lambda m:m[1]+str(value)+' ',rows[j]);found=True;break
        if not found:
            code,sep,comment=split_comment(raw)
            if not code.rstrip().endswith(':'):rows[i]=code.rstrip()+':'+(' #'+comment if sep else '')+'\n'
            rows.insert(i+1,indent+'    '+prop+' '+str(value)+'\n')
    elif kind=='audio':
        channel=op.get('channel','music')
        from .native_audio import valid_channel, with_registration
        if not valid_channel(project,channel):raise ValueError('无效声道。')
        setter=re.match(r'\s*\$ renpy\.music\.set_volume\(',raw)
        if setter:
            field=op['property'];value=op['value']
            cue=next((v[channel] for s in project['scenes'] for l in s['lines'] if (v:=l.get('audio')) and channel in v
                      and v[channel].get('nativeSource',{}).get('path')==path and v[channel]['nativeSource']['line']==i+1),None)
            if cue is None:raise ValueError('音频状态已变化。')
            if field=='volume' and type(value) in (int,float) and math.isfinite(value) and value>=0:
                base=cue.get('fileVolume',1)
                if not base:raise ValueError('原播放音量为零，请从原播放语句调整。')
                rows[i]=indent+'$ renpy.music.set_volume('+repr(value/base)+', delay=0, channel='+repr(channel)+')\n'
            elif field=='asset':
                asset=next((a for a in project['assets'] if a['id']==value and a['kind']=='audio' and a.get('nativeGamePath')),None)
                if value and not asset:raise ValueError('音频不属于当前项目。')
                rows[i]=indent+'$ renpy.music.set_volume(1.0, delay=0, channel='+repr(channel)+')\n'+indent+('play '+channel+' '+repr(asset['nativeGamePath'])+' volume '+str(cue['volume'])+' fadeout 0.5 fadein 0.8' if asset else 'stop '+channel+' fadeout '+str(cue.get('fadeout',.5)))+'\n'
            else:raise ValueError('此段只调整音量；淡入淡出请在播放段设置。')
            return with_registration(root,project,op,{'path':path,'hash':doc['hash'],'content':''.join(rows)})
        if not re.match(r'\s*(?:play|stop|queue)\s+'+channel+r'\b',raw):raise ValueError('此位置没有对应音频语句。')
        field=op['property'];value=op['value']
        if field=='asset':
            asset=next((a for a in project['assets'] if a['id']==value and a['kind']=='audio'),None)
            if value and not asset:raise ValueError('音频不属于当前项目。')
            filename=(asset or {}).get('nativeGamePath')
            if value and not filename:raise ValueError('音频缺少原工程路径。')
            from .renpy_import import TOKEN
            code,sep,comment=split_comment(raw)
            match=re.match(r'(\s*(?:play|queue)\s+'+channel+r'\s+)('+TOKEN+r'|[A-Za-z_][\w.]*)(.*)',code)
            if value and match:
                code=match[1]+repr(filename)+match[3]
                if not re.search(r'\bfadeout\s+',code):code=code.rstrip()+' fadeout 0.5'
                if not re.search(r'\bfadein\s+',code):code=code.rstrip()+' fadein 0.8'
            else:
                fade=re.search(r'\bfadeout\s+([0-9.eE+-]+)',code)
                fadeout=fade[1] if fade else '0.5'
                code=indent+('play '+channel+' '+repr(filename)+' fadeout 0.5 fadein 0.8' if value else 'stop '+channel+' fadeout '+fadeout)
            rows[i]=code.rstrip()+(' #'+comment if sep else '')+'\n'
        elif field in ('volume','fadein','fadeout') and type(value) in (int,float) and math.isfinite(value) and value>=0:
            if not raw.lstrip().startswith('play '):raise ValueError('请先选择要播放的音频。')
            if field=='volume' and op.get('effective'):
                cue=next((v[channel] for s in project['scenes'] for l in s['lines'] if (v:=l.get('audio')) and channel in v
                          and v[channel].get('nativeSource',{}).get('path')==path and v[channel]['nativeSource']['line']==i+1),{})
                multiplier=cue.get('channelVolume',1)
                if not multiplier:raise ValueError('声道音量为零，请从独立音量段调整。')
                value/=multiplier
            pattern=r'\b'+field+r'\s+[^\s#]+'
            code,sep,comment=split_comment(raw)
            code=re.sub(pattern,field+' '+str(value),code) if re.search(pattern,code) else code.rstrip()+' '+field+' '+str(value)
            rows[i]=code.rstrip()+(' #'+comment if sep else '')+'\n'
        else:raise ValueError('无效音频参数。')
    elif kind=='insert':
        command=op['command']
        if not isinstance(command,str) or len(command)>20000:raise ValueError('插入内容过长。')
        track=op.get('boundary')
        if track in ('visual','audio'):command='# creator:'+track+'-boundary begin\n'+command+'\n# creator:'+track+'-boundary end'
        rows[i:i]=[indent+row+'\n' for row in command.splitlines()]
    elif kind=='restore':
        track=op.get('track')
        if track not in ('visual','audio'):raise ValueError('无效轨道。')
        start=next((j for j in range(i,-1,-1) if rows[j].strip()=='# creator:'+track+'-boundary begin'),None)
        if start is None:raise ValueError('此段由原代码设置，请在源码中调整。')
        end=next((j for j in range(start+1,len(rows)) if rows[j].strip()=='# creator:'+track+'-boundary end'),None)
        if end is None or end>=i:raise ValueError('此句前没有可恢复的独立设置。')
        del rows[start:end+1]
    elif kind=='remove':
        tag=op['tag']
        if not re.fullmatch(r'\w+',tag):raise ValueError('无效人物实例。')
        rows.insert(i,indent+'hide '+tag+'\n')
    else:raise ValueError('未知演出操作。')
    result={'path':path,'hash':doc['hash'],'content':''.join(rows)}
    if kind=='audio':
        from .native_audio import with_registration
        return with_registration(root,project,op,result)
    return result
