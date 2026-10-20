"""Literal audio channel catalog and transactional native layer editing."""
from __future__ import annotations
import ast
import math
import re
from .workspace import read_overlay

BUILTINS = {'music': 'BGM 1', 'sound': '音效', 'voice': '语音'}
MANAGED = re.compile(r'(?:ambience|creator_bgm_(?:[2-9]|[1-9][0-9]+))\Z')
IDENTIFIER = r'[A-Za-z_][A-Za-z_0-9]*'
HEADER = '# Creator audio channels v1. Managed registration; keep project declarations unchanged.\n'


def registration(name):
    return ('    if not renpy.music.channel_defined(' + repr(name) + '):\n'
            '        renpy.music.register_channel(' + repr(name) + ', mixer="music", loop=True)\n')


def catalog(scripts):
    channels = {name: {'id': name, 'name': title, 'kind': 'bgm' if name == 'music' else name}
                for name, title in BUILTINS.items()}
    channels['ambience'] = {'id': 'ambience', 'name': '环境音', 'kind': 'ambience'}
    for _, text in scripts:
        for raw in text.splitlines():
            # Parse literal calls without executing project expressions or comments.
            code = raw.strip().removeprefix('$ ').strip()
            if not code.startswith('renpy.music.register_channel('): continue
            try:
                call = ast.parse(code).body[0].value
                name = ast.literal_eval(call.args[0])
                mixer = next((ast.literal_eval(k.value) for k in call.keywords if k.arg == 'mixer'), ast.literal_eval(call.args[1]) if len(call.args)>1 else None)
            except (SyntaxError, ValueError, TypeError, AttributeError, IndexError): continue
            if not isinstance(name, str) or not re.fullmatch(IDENTIFIER, name): continue
            if name in channels:
                channels[name]['declared']=True
                continue
            managed = bool(MANAGED.fullmatch(name))
            channels[name] = {'id': name, 'name': ('BGM ' + name.rsplit('_', 1)[1]) if managed else name,
                              'kind': 'bgm' if mixer == 'music' else 'sound', 'declared':True}
    return list(channels.values())


def valid_channel(project, name):
    return isinstance(name, str) and bool(re.fullmatch(IDENTIFIER, name)) and (
        name in BUILTINS or bool(MANAGED.fullmatch(name)) or
        any(c['id'] == name for c in project['nativeRenpy'].get('audioChannels', [])))


def with_registration(root, project, op, result):
    name = op.get('channel', 'music')
    if not valid_channel(project, name): raise ValueError('未登记的音频声道。')
    if not MANAGED.fullmatch(name): return result
    path = 'game/creator_assets/audio_channels.rpy' if project['nativeRenpy'].get('inPlace') else 'extensions/renpy/creator_assets/audio_channels.rpy'
    helper = read_overlay(root, path, op.get('documents'))
    content = helper['content']
    # A project declaration may run at any init priority; never register ahead
    # of it or replace its mixer/loop policy.
    if not content and any(c['id']==name and c.get('declared') for c in project['nativeRenpy'].get('audioChannels',[])):
        return result
    names = re.findall(r"^    if not renpy.music.channel_defined\('([A-Za-z_0-9]+)'\):$", content, re.M)
    expected = HEADER + 'init 100 python:\n' + ''.join(registration(n) for n in sorted(set(names)))
    if content and (content != expected or any(not MANAGED.fullmatch(n) for n in names)):
        raise ValueError('音频声道辅助文件有手工修改，请先在源码中处理；未覆盖。')
    if name in names: return result
    if any(c['id']==name and c.get('declared') for c in project['nativeRenpy'].get('audioChannels',[])):
        return result
    names.append(name)
    edit = {'path': path, 'hash': helper['hash'], 'content': HEADER + 'init 100 python:\n' + ''.join(registration(n) for n in sorted(set(names)))}
    return {'edits': [*result.get('edits', [result]), edit]}


def layer_edit(root, project, op, document, index):
    """Insert a change at a text anchor; only affect the requested channel."""
    from .native_stage import edit
    channel = op.get('channel', 'music')
    if not valid_channel(project, channel): raise ValueError('未登记的音频声道。')
    action = op.get('action')
    for key, default, maximum in [('volume', 1, 10), ('fadein', .8, 60), ('fadeout', .5, 60)]:
        value = op.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
            raise ValueError('无效音频参数：' + key)
    fadeout, fadein, volume = op.get('fadeout', .5), op.get('fadein', .8), op.get('volume', 1)
    if action == 'play':
        asset = next((a for a in project['assets'] if a['id'] == op.get('asset') and a['kind'] == 'audio' and (a.get('status') == 'ready' or a.get('virtual')) and a.get('nativeGamePath')), None)
        if not asset: raise ValueError('请选择当前项目已补齐的音频。')
        command = '$ renpy.music.set_volume(1.0, delay=0, channel=' + repr(channel) + ')\nplay ' + channel + ' ' + repr(asset['nativeGamePath']) + ' volume ' + str(volume) + ' fadeout ' + str(fadeout) + ' fadein ' + str(fadein)
    elif action == 'stop':
        command = 'stop ' + channel + ' fadeout ' + str(fadeout)
    elif action == 'volume':
        state = None
        for scene in project['scenes']:
            if not any(l['id'] == op.get('nodeId') for l in scene['lines']): continue
            for line in scene['lines']:
                if line.get('audio') is not None: state = line['audio']
                if line['id'] == op['nodeId']: break
        cue = (state or {}).get(channel)
        if not cue or not cue.get('asset'): raise ValueError('此声道尚未播放，请先选择音频。')
        if cue.get('nativeUnknown'): raise ValueError('此声道随路线变化，请先在当前句明确选择音频。')
        base = cue.get('fileVolume', 1)
        if not base: raise ValueError('原播放音量为零，请先在原播放处调整。')
        command = '$ renpy.music.set_volume(' + repr(volume / base) + ', delay=0, channel=' + repr(channel) + ')'
    else: raise ValueError('无效音频层操作。')
    result = edit(root, project, {**op, 'operation': 'insert', 'command': command})
    return with_registration(root, project, op, result)
