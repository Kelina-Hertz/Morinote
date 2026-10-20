"""Static staging projection. Never executes expressions from imported games.

Unknown statements remain in the source and produce visible track annotations.
Only literal resources and numeric constants are evaluated here.
"""
from __future__ import annotations
import ast
import copy
import hashlib
import math
import re

TOKEN = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''


def literal(value, constants):
    value = value.strip()
    if value in constants:
        return constants[value]
    try:
        result = ast.literal_eval(value)
        if isinstance(result, (str, int, float, tuple, bool)):
            return result
    except (ValueError, SyntaxError):
        pass
    return None


def properties(lines, constants):
    result, notes = {}, []
    for raw in lines:
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        key, _, expression = raw.partition(' ')
        if key in {'linear', 'ease', 'easein', 'easeout'}:
            duration, _, target = expression.partition(' ')
            if type(literal(duration, constants)) in (int, float) and target:
                parts = target.split()
                if len(parts) % 2 == 0:
                    final, _ = properties([' '.join(parts[i:i + 2]) for i in range(0, len(parts), 2)], constants)
                    result.update(final)
            notes.append(raw)
            continue
        if key in {'xpos', 'ypos', 'xanchor', 'yanchor', 'zoom', 'xzoom', 'yzoom', 'xoffset', 'yoffset', 'alpha', 'zorder'}:
            value = literal(expression.split('#')[0], constants)
            if type(value) in (float, int) and math.isfinite(value):
                result[key] = value
            else:
                notes.append(raw)
        elif key in {'pos', 'anchor'}:
            value = literal(expression.split('#')[0], constants)
            if isinstance(value, tuple) and len(value) == 2 and all(type(v) in (int, float) for v in value):
                result.update(dict(zip(('xpos', 'ypos') if key == 'pos' else ('xanchor', 'yanchor'), value)))
            else:
                notes.append(raw)
        else:
            notes.append(raw)
    return result, notes


def catalog(document, scripts):
    document['assets'] = [a for a in document['assets'] if not a.get('virtual') and not a.get('nativeGamePath', '').startswith('_creator_virtual/')]
    audio_resources = {}
    constants, images, transforms = {}, {}, {}
    for _, text in scripts:
        gui = re.search(r'(?m)^\s+gui\.init\(\s*(\d+)\s*,\s*(\d+)\s*\)', text)
        if gui: document['resolution'] = [int(gui[1]), int(gui[2])]
        for match in re.finditer(r'(?m)^\s*define\s+([\w.]+)\s*=\s*([^\n]+)', text):
            value = literal(match[2].split('#')[0], constants)
            if value is not None:
                constants[match[1]] = value
        for key, pattern in (('width', 'config.screen_width'), ('height', 'config.screen_height')):
            if type(constants.get(pattern)) is int:
                document['resolution'][0 if key == 'width' else 1] = constants[pattern]
    assets = {a.get('nativeGamePath'): a for a in document['assets'] if a.get('nativeGamePath')}
    for asset in document['assets']:
        asset.pop('nativeAliases',None)
        asset.pop('nativeAliasConflicts',None)

    def resource(value):
        if value in audio_resources:
            return audio_resources[value]
        if re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', value or ''):
            aid = 'native_solid_' + hashlib.sha256(value.encode()).hexdigest()[:12]
            asset = next((a for a in document['assets'] if a['id'] == aid), None)
            if not asset:
                asset = {'id': aid, 'kind': 'background', 'name': value, 'path': 'builtin:solid:' + value, 'status': 'ready'}
                document['assets'].append(asset)
            return asset
        return assets.get((value or '').replace('\\', '/').removeprefix('./'))

    for _, text in scripts:
        rows = text.splitlines()
        for i, row in enumerate(rows):
            match = re.match(r'^image\s+([\w ]+?)\s*(?:=\s*(' + TOKEN + r')|:\s*)(?:#.*)?$', row)
            transform = re.match(r'^transform\s+(\w+)\s*:\s*$', row)
            if not match and not transform:
                continue
            block, j = [], i + 1
            while j < len(rows) and (not rows[j].strip() or rows[j][0].isspace()):
                block.append(rows[j]); j += 1
            if transform:
                transforms[transform[1]] = properties(block, constants)
                continue
            value = literal(match[2], constants) if match[2] else None
            if value is None and block:
                first = next((k for k, b in enumerate(block) if b.strip() and not b.lstrip().startswith('#')), None)
                if first is not None and re.fullmatch(TOKEN, block[first].strip()):
                    value = literal(block[first].strip(), constants)
                    block = block[first + 1:]
            asset = resource(value) if isinstance(value, str) else None
            if asset:
                props, notes = properties(block if not match[2] else [], constants)
                candidate = {'asset': asset['id'], 'props': props, 'notes': notes}
                name = match[1].strip()
                if name in images and images[name] != candidate:
                    images[name] = None  # Conflicting aliases are never guessed.
                else:
                    images[name] = candidate
                aliases = asset.setdefault('nativeAliases', [])
                old_name = ' / '.join(aliases) if aliases else asset['name']
                if name not in aliases:
                    aliases.append(name)
                if asset['name'] == old_name:
                    asset['name'] = ' / '.join(aliases)
    for name, color in (('black', '#000000'), ('white', '#ffffff')):
        if name not in images:
            asset = resource(color)
            asset['name'] = name
            images[name] = {'asset': asset['id'], 'props': {}, 'notes': []}
    for asset in document['assets']:
        conflicts=[name for name in asset.get('nativeAliases',[]) if images.get(name) is None]
        if conflicts:
            asset['nativeAliasConflicts']=conflicts
            asset['nativeAliases']=[name for name in asset['nativeAliases'] if name not in conflicts]
    if document.get('nativeRenpy', {}).get('inPlace'):
        from .native_assets import augment
        audio_resources.update(augment(document, scripts, images, constants) or {})
    return constants, images, transforms, resource


def project_tracks(document, scripts, records):
    from .native_audio import catalog as audio_catalog
    channels=audio_catalog(scripts)
    channel_pattern='(?:'+'|'.join(re.escape(c['id']) for c in channels)+')'
    document['nativeRenpy']['audioChannels']=channels
    constants, images, transforms, resource = catalog(document, scripts)
    by_file = {item['gamePath']: text.splitlines() for item, text in scripts}
    stats = {'visualCues': 0, 'audioCues': 0, 'annotatedLines': 0}
    for scene in document['scenes']:
        label = next(l for l in document['nativeRenpy']['labels'] if l['id'] == scene['id'])
        rows = by_file[label['file']]
        visual = {'background': '', 'sprites': [], 'transition': 'none', 'nativeUnknown': ['由标签入口继承']}
        audio = {'music': {'asset': '', 'volume': 1, 'fadeout': .5, 'fadein': .8}, 'nativeUnknown': ['由标签入口继承']}
        cursor = label['line']
        last_indent = 4
        outer_properties = {}
        channel_volumes = {}
        motion_spec = None
        for index, line in enumerate(scene['lines']):
            record = records[line['id']]
            target = record['line'] - 1
            dirty = {'visual': index == 0, 'audio': index == 0}
            starts = {}
            notes = []
            i = cursor
            while i < target:
                body = rows[i].strip()
                indent = len(rows[i]) - len(rows[i].lstrip())
                if body.startswith('# creator:motion {'):
                    from .native_motion import validate
                    import json
                    try:motion_spec=validate(json.loads(body[len('# creator:motion '):]))
                    except (ValueError,TypeError,KeyError):motion_spec=None
                    i+=1;continue
                if body=='# creator:motion end':motion_spec=None;i+=1;continue
                if not body or body.startswith('#'):
                    i += 1; continue
                if body.startswith('$ creator_native_auto_prepare('):
                    i += 1; continue
                if motion_spec and body.startswith('$ renpy.pause('):i+=1;continue
                setter=re.fullmatch(r'\$ renpy\.music\.set_volume\(([0-9.eE+-]+), delay=0, channel=[\'\"]('+channel_pattern+r')[\'\"]\)',body)
                if setter:
                    multiplier=float(setter[1]);channel=setter[2]
                    if math.isfinite(multiplier) and multiplier>=0:
                        channel_volumes[channel]=multiplier
                        cue=audio.setdefault(channel,{'asset':'','volume':1,'fileVolume':1,'fadeout':.5,'fadein':.8})
                        cue['volume']=cue.get('fileVolume',cue['volume'])*multiplier
                        cue['channelVolume']=multiplier
                        cue['nativeSource']={'path':record['path'],'line':i+1,'endLine':i+1,'statement':rows[i]}
                        dirty['audio']=True
                        i+=1;continue
                # Nested control flow has path-dependent state. Do not let a
                # previous arm leak into a sibling or a merge in the editor.
                if re.match(r'(?:if |elif |else:|menu:|while |for |call\b|jump\b|return\b|python\b|\$)', body) or indent != last_indent:
                    for track, state in (('visual', visual), ('audio', audio)):
                        state['nativeUnknown'] = ['条件／调用或自定义代码影响，实际状态由运行路线决定']
                        if track=='audio':
                            for cue in state.values():
                                if isinstance(cue,dict):cue['nativeUnknown']=state['nativeUnknown'][:]
                        dirty[track] = True
                    last_indent = indent
                if re.match(r'(?:python(?:\s+\w+)*|(?:show|hide)\s+screen)\b', body):
                    if body.endswith(':'):
                        i += 1
                        while i < target and (not rows[i].strip() or len(rows[i]) - len(rows[i].lstrip()) > indent): i += 1
                        continue
                    i += 1; continue
                stage = re.match(r'(scene|show|hide)\s+(?!screen\b)(.+)', body)
                if stage:
                    operation, tail = stage.groups()
                    block, end = [], i + 1
                    if tail.endswith(':'):
                        tail = tail[:-1].rstrip()
                        while end < target and (not rows[end].strip() or len(rows[end]) - len(rows[end].lstrip()) > indent):
                            block.append(rows[end]); end += 1
                    name = re.split(r'\s+(?:as|at|with|onlayer|zorder|behind)\s+', tail)[0].strip()
                    tag_match = re.search(r'\bas\s+(\w+)', tail)
                    tag = tag_match[1] if tag_match else name.split()[0]
                    cue = images.get(name)
                    track_notes = []
                    if ' onlayer ' in tail or ' behind ' in tail:
                        track_notes.append('自定义图层：' + body)
                    if operation == 'hide':
                        visual['sprites'] = [s for s in visual['sprites'] if s['id'] != tag]
                        outer_properties.pop(tag, None)
                    elif cue:
                        props = copy.deepcopy(cue['props'])
                        track_notes.extend(cue['notes'])
                        at = re.search(r'\bat\s+([\w, ]+?)(?=\s+(?:with|as|onlayer|zorder)\s+|$)', tail)
                        if at:
                            outer_properties.pop(tag, None)
                            for transform in at[1].split(','):
                                known = transforms.get(transform.strip())
                                if known:
                                    props.update(known[0]); track_notes.extend(known[1])
                                    outer_properties.setdefault(tag,{}).update(known[0])
                                else:
                                    track_notes.append('原变换：' + transform.strip())
                        props.update(outer_properties.get(tag, {}))
                        overrides, extra = properties(block, constants)
                        props.update(overrides)
                        if not motion_spec:track_notes.extend(extra)
                        # Image ATL is inside the show transform. Its zoom is
                        # multiplied by the outer zoom, not replaced by it.
                        outer_zoom = outer_properties.get(tag, {}).get('zoom', 1)
                        if at:
                            for transform in at[1].split(','):
                                known = transforms.get(transform.strip())
                                if known and 'zoom' in known[0]: outer_zoom = known[0]['zoom']
                        outer_zoom = overrides.get('zoom', outer_zoom)
                        props['zoom'] = cue['props'].get('zoom', 1) * outer_zoom
                        zorder=re.search(r'\bzorder\s+(-?\d+)\b',tail)
                        if zorder:props['zorder']=int(zorder[1])
                        outer_properties[tag] = {**outer_properties.get(tag, {}), **overrides}
                        if operation == 'scene':
                            outer_properties = {}
                            visual = {'background': cue['asset'], 'sprites': [], 'transition': 'none',
                                      'nativeBackground': {'tag': tag, 'props': props, 'source': {'path':record['path'],'line':i+1,'endLine':end,'image':name,'statement':rows[i]}}}
                        else:
                            asset = next(a for a in document['assets'] if a['id'] == cue['asset'])
                            if asset['kind'] == 'background':
                                # A show can be a foreground CG/UI image too.
                                # Keep the source statement but don't mislabel it as a character.
                                track_notes.append('前景图片：' + name)
                            else:
                                if asset['kind'] == 'sprite': asset.setdefault('character', tag)
                                width, height = document['resolution']
                                def position(key, extent):
                                    value = props.get(key, 0)
                                    return value * extent if type(value) is float else value
                                sprite = {'id': tag, 'asset': cue['asset'], 'x': position('xpos', width) + props.get('xoffset', 0),
                                          'y': position('ypos', height) + props.get('yoffset', 0), 'scale': props.get('zoom', 1),
                                          'anchorX': props.get('xanchor', 0), 'anchorY': props.get('yanchor', 0),
                                          'flip': props.get('xzoom', 1) < 0, 'z': props.get('zorder', 0),
                                          'nativeOriginal': {'image': name, 'intrinsicZoom': cue['props'].get('zoom', 1), 'props': copy.deepcopy(outer_properties.get(tag, {}))}}
                                sprite['nativeSource']={'path':record['path'],'line':i+1,'endLine':end,'image':name,'statement':rows[i]}
                                if motion_spec and motion_spec['tag']==tag:sprite['nativeMotion']=copy.deepcopy(motion_spec)
                                previous = next((j for j, s in enumerate(visual['sprites']) if s['id'] == tag), None)
                                if previous is None: visual['sprites'].append(sprite)
                                else: visual['sprites'][previous] = sprite
                        transition = re.search(r'\bwith\s+(\w+)', tail)
                        visual['transition'] = transition[1].lower() if transition and transition[1].lower() in {'dissolve', 'fade'} else 'none'
                    else:
                        track_notes.append('未解析图片表达式：' + name)
                        visual['nativeUnknown'] = [track_notes[-1]]
                    if track_notes:
                        notes.extend(track_notes)
                    dirty['visual'] = True
                    starts.setdefault('visual', i + 1)
                    i = end; continue
                sound = re.match(r'(play|stop|queue)\s+('+channel_pattern+r')\b\s*(.*)', body)
                if sound:
                    op, channel, tail = sound.groups()
                    token = re.match('(' + TOKEN + r'|[\w.]+)', tail)
                    path = literal(token[1], constants) if token else None
                    asset = resource(path) if isinstance(path, str) else None
                    if op == 'stop' or asset and op == 'play':
                        previous = audio.get(channel, {})
                        track = {'asset': asset['id'] if op != 'stop' else '', 'volume': 1, 'fadeout': .5, 'fadein': .8}
                        for key in ('volume', 'fadeout', 'fadein'):
                            value = re.search(r'\b' + key + r'\s+([^\s]+)', tail)
                            if value:
                                parsed = literal(value[1], constants)
                                if type(parsed) in (int, float) and math.isfinite(parsed) and parsed >= 0: track[key] = parsed
                                else: notes.append('动态音频参数：' + body)
                        audio[channel] = track
                        track['fileVolume']=track['volume']
                        track['channelVolume']=channel_volumes.get(channel,1)
                        track['volume']*=channel_volumes.get(channel,1)
                        track['nativeSource']={'path':record['path'],'line':i+1,'endLine':i+1,'statement':rows[i]}
                        if channel == 'music': audio.pop('nativeUnknown', None)
                    else:
                        audio['nativeUnknown'] = ['动态音频／队列：' + body]
                        notes.append(audio['nativeUnknown'][0])
                    dirty['audio'] = True
                    starts.setdefault('audio', i + 1)
                elif re.match(r'(?:camera\b|with\b|pause\b)', body):
                    notes.append('原演出：' + body)
                i += 1
            record['trackStarts'] = starts
            record['trackContextStart'] = cursor
            record['trackContext'] = rows[cursor:target]
            record['trackNotes'] = notes
            for track, state in (('visual', visual), ('audio', audio)):
                line[track] = copy.deepcopy(state) if dirty[track] else None
                if line[track] and any(row.strip()=='# creator:'+track+'-boundary begin' for row in rows[record['trackContextStart']:target]):line[track]['nativeBoundary']=True
                if dirty[track]: stats[track + 'Cues'] += 1
            if notes:
                line['source']['trackNotes'] = notes
                stats['annotatedLines'] += 1
            cursor = target + 1
    document['nativeRenpy'].update(trackVersion=2, trackStats=stats)
