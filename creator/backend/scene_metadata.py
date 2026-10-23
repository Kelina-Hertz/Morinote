"""Optional, inert scene display hints stored next to author-owned labels."""
import json

PREFIX = '# morinote-scene: '


def display_hints(line):
    if not line.startswith(PREFIX):
        return {}
    try:
        value = json.loads(line[len(PREFIX):])
    except (ValueError, TypeError):
        return {}
    if not isinstance(value, dict):
        return {}
    title, group = value.get('title'), value.get('group')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        return {}
    if not isinstance(group, str) or not 1 <= len(group.strip()) <= 120:
        return {}
    result = {'displayTitle': title.strip(), 'displayGroup': group.strip()}
    if value.get('kind') in ('choice', 'condition'):
        result['blockKind'] = value['kind']
    return result


def scene_comment(title, group, kind=None):
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError('场景名称需为 1 至 120 个非空字符。')
    if not isinstance(group, str) or not 1 <= len(group.strip()) <= 120:
        raise ValueError('章节名称需为 1 至 120 个非空字符。')
    value = {'title': title.strip(), 'group': group.strip()}
    if kind is not None:
        if kind not in ('scene', 'choice', 'condition'):
            raise ValueError('不支持的剧情块类型。')
        value['kind'] = kind
    return PREFIX + json.dumps(value, ensure_ascii=False)
