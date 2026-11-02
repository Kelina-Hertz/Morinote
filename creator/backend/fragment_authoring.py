"""Validated short fragments become authored RPY, with normal source transactions."""
from __future__ import annotations
import copy
import hashlib
import json
import re

from .workspace import read_overlay, projection
from .compiler import renpy_text


def text_hash(value):
    # Same canonical string representation as electron/media/common.cjs.
    text = str(value).replace('\r\n', '\n').replace('\r', '\n')
    return hashlib.sha256(json.dumps(text, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def string(value, name, maximum=1500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError(name + '为空、过长或包含无效字符。')
    return value


def validate(plan, project):
    if not isinstance(plan, dict) or plan.get('version') != 1:
        raise ValueError('不支持的片段计划版本。')
    string(plan.get('title'), '片段标题', 100)
    chars = plan.get('characters', [])
    if not isinstance(chars, list) or not 1 <= len(chars) <= 2:
        raise ValueError('片段需要 1–2 个角色。')
    ids = set()
    for char in chars:
        if not isinstance(char, dict):
            raise ValueError('角色条目必须是对象。')
        key = char.get('id')
        if not isinstance(key, str) or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,40}', key) or key in ids:
            raise ValueError('角色编号无效或重复。')
        ids.add(key)
        string(char.get('name'), '角色名', 40)
        if 'x' in char and (not isinstance(char['x'], (int, float)) or not 0 <= char['x'] <= 1):
            raise ValueError('人物位置应在 0–1 之间。')
    choice = plan.get('choice')
    if not isinstance(choice, dict) or not isinstance(choice.get('options'), list) or len(choice['options']) != 2:
        raise ValueError('片段须有一个二选一分支。')
    lines = plan.get('lines', [])
    ending = plan.get('ending', [])
    if not isinstance(lines, list) or not lines or not isinstance(ending, list):
        raise ValueError('开场文字或收尾格式无效。')
    all_lines = list(lines)
    option_ids = set()
    for option in choice['options']:
        if not isinstance(option, dict):
            raise ValueError('选项条目必须是对象。')
        string(option.get('text'), '选项文字', 150)
        oid = option.get('id')
        if not isinstance(oid, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', oid) or oid in option_ids:
            raise ValueError('选项编号无效或重复。')
        option_ids.add(oid)
        if not isinstance(option.get('lines'), list) or not option['lines']:
            raise ValueError('每条路线都需要回应。')
        all_lines.extend(option['lines'])
    all_lines.extend(ending)
    if not 6 <= len(all_lines) <= 12:
        raise ValueError('首版片段须包含 6–12 句文字。')
    node_ids = set()
    for line in all_lines:
        if not isinstance(line, dict):
            raise ValueError('文字条目必须是对象。')
        nid = line.get('id')
        if not isinstance(nid, str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}', nid) or nid in node_ids:
            raise ValueError('文字节点编号无效或重复。')
        node_ids.add(nid)
        if line.get('kind') not in ('narration', 'dialogue') or line.get('kind') == 'dialogue' and line.get('speaker') not in ids:
            raise ValueError('文字类型或说话人引用无效。')
        string(line.get('text'), '文字')
        if line.get('voice') is not None:
            voice = line['voice']
            if not isinstance(voice, dict) or line['kind'] != 'dialogue':
                raise ValueError('配音应关联明确的角色对白。')
            if voice.get('text') is not None:
                string(voice['text'], '合成文字', 2000)
    background = plan.get('background')
    if not isinstance(background, dict) or background.get('mode') not in ('generate', 'existing'):
        raise ValueError('须明确选择生成或已有背景。')
    if background['mode'] == 'generate':
        string(background.get('prompt'), '背景说明', 8000)
    assets = {a['id']: a for a in project.get('assets', [])}
    def require_asset(key, kinds):
        if key and (key not in assets or assets[key].get('kind') not in kinds or assets[key].get('status') == 'missing'):
            raise ValueError('引用的素材不存在或类型不匹配：' + str(key))
    if background['mode'] == 'existing':
        if not background.get('assetId'):
            raise ValueError('未选择已有背景。')
        require_asset(background['assetId'], ('image', 'background', 'sprite'))
    for key in background.get('referenceAssetIds', []):
        require_asset(key, ('image', 'background', 'sprite'))
    for char in chars:
        require_asset(char.get('spriteAssetId'), ('sprite', 'image'))
    require_asset(plan.get('bgmAssetId'), ('audio',))
    if plan.get('transition', 'dissolve') not in ('none', 'fade', 'dissolve'):
        raise ValueError('首版支持 fade、dissolve 或无转场。')
    return all_lines


def quote(value):
    return renpy_text(value)


def prepare(root, project, body):
    plan = body['plan']
    documents = body.get('documents', [])
    candidate = projection(root, project, documents, ide=body.get('ide'))
    all_lines = validate(plan, candidate)
    fragment_id = body['fragmentId']
    if not re.fullmatch(r'[a-z0-9_]{1,60}', fragment_id):
        raise ValueError('片段编号无效。')
    name = 'creator_' + fragment_id
    path = 'game/creator_fragments/' + fragment_id + '.rpy'
    doc = read_overlay(root, path, documents)
    replacing = bool(doc['exists'] or doc['content'].strip())
    if replacing and text_hash(doc['content']) != body.get('replaceHash'):
        raise ValueError('片段源码已经存在或被手工修改；请比较后再应用，不覆盖后续修改。')
    if not replacing and any(l['name'] == name for l in candidate['nativeRenpy']['labels']):
        raise ValueError('片段标签已被使用。')
    resources = {a['id']: a for a in candidate['assets']}
    bindings = body.get('bindings', {})
    lines = ['# Authored from a validated fragment plan. Edit normally in this IDE.']
    chars = {c['id']: c for c in plan['characters']}
    for key, char in chars.items():
        lines.append('define ' + name + '_' + key + ' = Character(' + quote(char['name']) + ')')
    def image_reference(asset_id, suffix):
        asset = resources.get(asset_id)
        if not asset:
            raise ValueError('生成片段的图片绑定失效。')
        aliases = asset.get('nativeAliases') or []
        if aliases and re.fullmatch(r'[A-Za-z_]\w*(?:\s+\w+)*', aliases[0]):
            return aliases[0]
        own = name + '_' + suffix
        filename = asset.get('nativeGamePath')
        if not filename or asset.get('status') == 'missing':
            raise ValueError('生成片段图片未绑定。')
        lines.append('image ' + own + ' = ' + json.dumps(filename, ensure_ascii=False))
        return own
    bg_id = bindings.get('background') or plan['background'].get('assetId')
    background = image_reference(bg_id, 'background')
    sprites = [(c, image_reference(c['spriteAssetId'], 'sprite_' + c['id'])) for c in chars.values() if c.get('spriteAssetId')]
    lines += ['', '# morinote-scene: ' + json.dumps({'title': plan['title'], 'group': '生成片段'}, ensure_ascii=False), 'label ' + name + ':', '    scene ' + background]
    for char, image in sprites:
        lines.append('    show ' + image + ' at Position(xalign=' + str(char.get('x', .5)) + ', yalign=1.0)')
    transition = plan.get('transition', 'dissolve')
    if transition != 'none':
        lines.append('    with ' + transition)
    if plan.get('bgmAssetId'):
        asset = resources[plan['bgmAssetId']]
        filename = asset.get('nativeGamePath')
        if not filename:
            raise ValueError('背景音乐路径不能静态确定。')
        lines.append('    play music ' + json.dumps(filename, ensure_ascii=False) + ' fadeout 0.5 fadein 0.8')
    node_map = {}
    def emit_line(line, indent='    '):
        lines.append(indent + '# creator-node: ' + json.dumps({'fragmentId': fragment_id, 'nodeId': line['id']}, ensure_ascii=False))
        voice = bindings.get('voices', {}).get(line['id'])
        if line.get('voice') is not None:
            if not voice or voice.get('assetId') not in resources:
                raise ValueError('配音已生成但目标绑定不完整。')
            metadata = {'jobId': voice['jobId'], 'nodeId': line['id'], 'textHash': text_hash(line['text']),
                        'speaker': line.get('speaker'), 'speakerName': chars[line['speaker']]['name'],
                        'ttsHash': voice['ttsHash'], 'artifactHash': voice['artifactHash']}
            metadata.update({key: voice[key] for key in ('candidateId', 'promptRevision') if key in voice})
            lines.append(indent + '# creator-voice: ' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':')))
            # The existing adapter will insert the correct voice operand below.
        alias = name + '_' + line['speaker'] + ' ' if line['kind'] == 'dialogue' else ''
        lines.append(indent + alias + quote(line['text']))
        node_map[line['id']] = {'line': len(lines), 'textHash': text_hash(line['text']), 'speaker': line.get('speaker')}
    for line in plan['lines']:
        emit_line(line)
    lines.append('    menu:')
    for option in plan['choice']['options']:
        lines.append('        ' + quote(option['text']) + ':')
        for line in option['lines']:
            emit_line(line, '            ')
    for line in plan.get('ending', []):
        emit_line(line)
    lines += ['    stop voice', '    stop music fadeout 0.5', '    scene black', '    return', '']
    content = '\n'.join(lines)
    overlay = [d for d in documents if d['path'] != path] + [{'path': path, 'hash': doc['hash'], 'content': content}]
    from . import native_stage
    for line in all_lines:
        if line.get('voice') is None:
            continue
        parsed = projection(root, project, overlay, ide=body.get('ide'))
        source_lines = content.splitlines()
        marker = next(i for i, raw in enumerate(source_lines) if '# creator-node:' in raw and json.loads(raw.split('# creator-node:', 1)[1])['nodeId'] == line['id'])
        number = next(i + 1 for i in range(marker + 1, len(source_lines)) if re.match(r'^\s*(?:' + re.escape(name) + r'_\w+\s+)?"', source_lines[i]))
        target = next((l for s in parsed['scenes'] for l in s['lines'] if l.get('source', {}).get('file') == path[5:] and l['source']['line'] == number), None)
        if target is None or text_hash(target['text']) != text_hash(line['text']):
            # Parsed text contains Ren'Py escaping; compare decoded rendering too.
            if target is None or target['text'].replace('[[', '[').replace('{{', '{') != line['text']:
                raise ValueError('配音目标重新定位失败，保留产物而不绑定到错误台词。')
        prepared = native_stage.edit(root, parsed, {'operation': 'voice', 'nodeId': target['id'], 'asset': bindings['voices'][line['id']]['assetId'], 'documents': overlay, 'hash': doc['hash']})
        content = prepared['content']
        overlay[-1] = {'path': path, 'hash': doc['hash'], 'content': content}
    final = projection(root, project, overlay, ide=body.get('ide'))
    scene = next(s for s in final['scenes'] if s['id'] == next(l['id'] for l in final['nativeRenpy']['labels'] if l['name'] == name))
    mapping = {l.get('generatedNode', {}).get('nodeId'): {'nodeId': l['id'], 'line': l['source']['line']} for l in scene['lines'] if l.get('generatedNode')}
    return {'path': path, 'hash': doc['hash'], 'content': content, 'label': name, 'sceneId': scene['id'], 'nodeMap': mapping}
