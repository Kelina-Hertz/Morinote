"""Voice belongs to one say statement, never to an inherited music segment."""
import json
import re

TOKEN = r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')"""


def parse(raw, path, number, constants, resource):
    if not re.match(r'\s*(?:voice\b|(?:play|stop|queue)\s+voice\b)',raw):return None
    from .native_stage import split_comment
    from .native_tracks import literal
    code=split_comment(raw)[0].strip()
    match=re.fullmatch(r'(voice|(?:play|stop|queue)\s+voice)(?:\s+(.*))?',code)
    if not match:return None
    command,tail=match[1],match[2] or ''
    source={'path':path,'line':number,'endLine':number,'statement':raw}
    result={'asset':'','expression':tail,'command':command.split()[0],'editable':True,'nativeSource':source}
    if command=='stop voice':return result
    if command=='voice' and tail=='sustain':
        return {**result,'command':'sustain','editable':False,'reason':'跨句延续语音，请在源码中调整。'}
    token=re.match('('+TOKEN+r'|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)',tail)
    value=literal(token[1],constants) if token else None
    if token:result['expression']=token[1]
    if not isinstance(value,str) or (command=='voice' and tail[token.end():].strip()):
        return {**result,'editable':False,'reason':'动态语音表达式，请在源码中调整。'}
    filename=value
    if command=='voice':
        pattern=constants.get('config.voice_filename_format','{filename}')
        try:filename=pattern.format(filename=value)
        except (AttributeError,KeyError,ValueError,IndexError):
            return {**result,'editable':False,'reason':'动态语音路径规则，请在源码中调整。'}
    asset=resource(filename)
    result.update(asset=asset['id'] if asset and asset['kind']=='audio' else '',filename=filename)
    if command=='queue voice':result.update(editable=False,reason='语音队列，请在源码中调整。')
    return result


def source_index(line, rows, index):
    binding=line.get('voice')
    if not binding:return None
    if not binding.get('editable',False):raise ValueError(binding.get('reason','语音需要在源码中调整。'))
    source=binding.get('nativeSource',{})
    at=source.get('line',0)-1
    if source.get('path')!='game/'+line['source']['file'] or not 0<=at<index or rows[at].rstrip('\r\n')!=source.get('statement'):
        raise ValueError('语音源码位置已变化，请重新选择本句。')
    return at


def edit(project, op, document, index):
    from .renpy_import import SAY
    from .native_stage import split_comment
    from .workspace import read_overlay
    from .native_tracks import literal
    rows=document['content'].splitlines(keepends=True)
    line=next((l for s in project['scenes'] for l in s['lines'] if l['id']==op.get('nodeId')),None)
    if line is None or not SAY.match(rows[index].rstrip('\r\n')):raise ValueError('请重新选择要绑定语音的文字。')
    if line.get('advance') is False:raise ValueError('预填消息不播放语音，请选择可推进的消息。')
    at=source_index(line,rows,index)
    value=op.get('asset')
    if not value:
        if at is not None:del rows[at]
    else:
        asset=next((a for a in project['assets'] if a['id']==value and a['kind']=='audio' and a.get('nativeGamePath') and (a.get('status')=='ready' or a.get('virtual'))),None)
        if not asset:raise ValueError('请选择当前项目的音频或虚拟语音素材。')
        filename=asset['nativeGamePath'];operand=filename
        # Native voice applies the game's filename formatter; do not prefix twice.
        pattern='{filename}'
        for path in project['nativeRenpy']['codeFiles']:
            if not path.endswith('.rpy'):continue
            for raw in read_overlay(op['_root'],path,op.get('documents'))['content'].splitlines():
                if 'voice_filename_format' not in raw:continue
                match=re.match(r'^\s*define\s+config\.voice_filename_format\s*=\s*(.*)',split_comment(raw)[0])
                if match:
                    pattern=literal(match[1],{})
                    if not isinstance(pattern,str):raise ValueError('项目语音路径规则为动态表达式，请从源码绑定语音。')
        if at is None or line['voice']['command']!='play':
            if pattern!='{filename}':
                if pattern.count('{filename}')!=1:raise ValueError('项目语音路径规则无法安全转换，请从源码绑定语音。')
                before,after=pattern.split('{filename}')
                if not filename.startswith(before) or (after and not filename.endswith(after)):
                    raise ValueError('此素材不符合项目语音路径规则，请选择匹配的素材或调整源码。')
                operand=filename[len(before):len(filename)-len(after) if after else None]
            command='voice '+json.dumps(operand,ensure_ascii=False)
        else:
            # Preserve volume/loop options on a pre-existing play voice command.
            code,sep,comment=split_comment(rows[at].rstrip('\r\n'))
            match=re.match(r'(\s*play\s+voice\s+)('+TOKEN+r'|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(.*)',code)
            if match:command=(match[1]+json.dumps(filename,ensure_ascii=False)+match[3]).lstrip()
            else:command='voice '+json.dumps(operand,ensure_ascii=False)
        if at is None:
            at=index
            if index and re.match(r'^\s*\$ creator_native_auto_prepare\(',rows[index-1]):at-=1
            indent=re.match(r'^[ \t]*',rows[index])[0]
            newline=document.get('newline','\n')
            rows.insert(at,indent+command+newline)
        else:
            raw=rows[at].rstrip('\r\n');indent=re.match(r'^[ \t]*',raw)[0]
            _,sep,comment=split_comment(raw)
            rows[at]=indent+command+(' #'+comment if sep else '')+document.get('newline','\n')
    return {'path':document['path'],'hash':document['hash'],'content':''.join(rows)}
