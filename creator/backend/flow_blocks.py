"""Whole scene clipboard and removal, prepared against the current draft."""
from collections import Counter, OrderedDict
import io
import re
import tokenize
import uuid
from functools import lru_cache

from .flow_authoring import digest, label_path, PENDING_OUTLET, uncomment
from .scene_metadata import PREFIX, scene_comment
from .story_profile import preferred_labels
from .workspace import read_overlay

_clipboard = OrderedDict()


def _tail(rows):
    code=[row for row in rows if row.strip()]
    indent=min((re.match(r'^[ \t]*',row)[0] for row in code),key=lambda s:len(s.expandtabs(8)),default='    ')
    top=[row.strip() for row in code if len(re.match(r'^[ \t]*',row)[0].expandtabs(8))==len(indent.expandtabs(8))]
    return indent, bool(top and re.match(r'(?:jump\s|return(?:\s|$))',top[-1]))


def _rows(text):
    rows, masked = _scan(text) if len(text)<=512*1024 else _scan.__wrapped__(text)
    return list(rows), masked


@lru_cache(maxsize=32)
def _scan(text):
    """Mask strings/comments so their contents cannot become labels or jumps."""
    rows = text.splitlines(keepends=True)
    masked = [list(row) for row in rows]
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type not in (tokenize.STRING, tokenize.COMMENT):
                continue
            for line in range(token.start[0]-1, token.end[0]):
                begin = token.start[1] if line == token.start[0]-1 else 0
                end = token.end[1] if line == token.end[0]-1 else len(masked[line])
                for col in range(begin, end):
                    if masked[line][col] not in '\r\n': masked[line][col] = ' '
            if token.type == tokenize.STRING and not rows[token.start[0]-1][:token.start[1]].strip():
                # A narration line still has a meaningful indentation level.
                masked[token.start[0]-1][token.start[1]] = '*'
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return tuple(rows), None
    return tuple(rows), tuple(''.join(row) for row in masked)


def describe(project, documents):
    labels = project['nativeRenpy']['labels']
    active = {l['id'] for l in preferred_labels(project)}
    active_counts = Counter(l['name'] for l in preferred_labels(project))
    counts = Counter(l['name'] for l in labels)
    parsed = {p:_rows(doc['content']) for p,doc in documents.items()}
    result = {}
    for label in labels:
        path = label_path(project, label, documents)
        reason = ''
        if label['id'] not in active: reason = '当前采用编号版本，此副本仅供查看。'
        elif active_counts[label['name']] != 1: reason = '标签重复，无法唯一定位剧情。'
        elif '.' in label['name']: reason = '局部标签需要在源码中管理。'
        elif label.get('parameters') not in ('', '()'): reason = '带参数的剧情需要在源码中管理。'
        elif not path: reason = '无法唯一定位剧情源码。'
        if reason:
            result[label['id']] = {'copyReason':reason, 'deleteReason':reason}; continue
        rows, masked = parsed[path]
        start = label['line']-1
        if masked is None or start >= len(rows) or not re.match(r'^label\s+'+re.escape(label['name'])+r'\s*(?:\(\))?\s*:', masked[start]):
            result[label['id']] = {'copyReason':'源码位置无法安全识别，请先修复源码。','deleteReason':'源码位置无法安全识别，请先修复源码。'}; continue
        end = next((i for i in range(start+1,len(rows)) if masked[i].strip() and not masked[i][0].isspace()),len(rows))
        # The following label's display annotation belongs to that label.
        while end > start+1 and (not rows[end-1].strip() or rows[end-1].startswith('#')): end -= 1
        if any(l['name'].startswith(label['name']+'.') for l in labels): reason = '此剧情包含局部标签，请在源码中管理。'
        copy_reason = reason
        if counts[label['name']] != 1: reason = reason or '存在同名剧本版本，请在源码中删除指定版本。'
        if label['name'] == 'start' or not any(l['name']=='start' for l in labels) and any(g['id']==project['entryGraph'] and g.get('entry')==label['id'] for g in project['graphs']):
            reason = '游戏入口不能删除，可以编辑其中的内容。'
        annotation = start-1 if start and rows[start-1].startswith(PREFIX) else start
        result[label['id']] = {'copyReason':copy_reason,'deleteReason':reason,'path':path,'start':annotation,'labelRow':start,'end':end}
    return result


def capabilities(project, documents):
    return {key:{field:value[field] for field in ('copyReason','deleteReason')} for key,value in describe(project,documents).items()}


def prepare(root, project, operation):
    from pathlib import Path
    from .workspace import projection
    from .native_flow import edit
    documents = operation.get('documents', [])
    expected = operation.get('hashes', {})
    paths = project['nativeRenpy']['codeFiles']
    docs = {p:read_overlay(root,p,documents) for p in paths if p.endswith('.rpy')}
    for path, doc in docs.items():
        if expected.get(path) != {'hash':doc['hash'],'contentHash':digest(doc['content'])}:
            raise ValueError('相关源码已变化，请重新执行：'+path)
    descriptions = describe(project, docs)
    mode = operation['operation']
    if mode in ('copy_block','delete_block'):
        label = next((l for l in project['nativeRenpy']['labels'] if l['id']==operation.get('node')),None)
        spec = descriptions.get(operation.get('node'))
        if not label or not spec: raise ValueError('剧情块已变化，请重新选择。')
        reason = spec['copyReason' if mode=='copy_block' else 'deleteReason']
        if reason: raise ValueError(reason)
        doc = docs[spec['path']]; rows, masked = _rows(doc['content'])
    if mode == 'copy_block':
        title, group = operation.get('title'), operation.get('group')
        scene_comment(title,group,label.get('blockKind'))
        token = uuid.uuid4().hex
        body = ''.join(rows[spec['labelRow']+1:spec['end']])
        following = next((l for l in sorted(project['nativeRenpy']['labels'],key=lambda l:l['line']) if l['file']==label['file'] and l['line']>label['line']),None)
        _clipboard[token] = {'root':str(Path(root).resolve()),'body':body,'name':label['name'],'path':spec['path'],
                             'title':title,'group':group,'kind':label.get('blockKind'),'cut':operation.get('cut') is True,
                             'ending':'jump '+following['name'] if following else 'return'+PENDING_OUTLET}
        while len(_clipboard)>20: _clipboard.popitem(last=False)
        return {'clipboard':{'token':token,'title':title,'cut':operation.get('cut') is True,'name':label['name'],'path':spec['path']}}
    if mode == 'paste_block':
        saved = _clipboard.get(operation.get('clipboard'))
        if not saved or saved['root'] != str(Path(root).resolve()): raise ValueError('剪贴内容已失效，请重新复制。')
        cut = saved['cut']
        if cut and any(l['name']==saved['name'] for l in project['nativeRenpy']['labels']):
            raise ValueError('剪切的剧情已恢复，请重新复制或剪切。')
        scene = dict(operation.get('scene') or {})
        if cut: scene.update(name=saved['name'],path=saved['path'],title=saved['title'])
        scene.setdefault('group',saved['group'])
        destination = scene.get('path','game/creator_scenes.rpy')
        dest = read_overlay(root,destination,documents)
        if expected.get(destination) != {'hash':dest['hash'],'contentHash':digest(dest['content'])}:
            raise ValueError('目标源码已变化，请重新粘贴。')
        scene_comment(scene.get('title'),scene['group'],saved['kind'])
        # Reuse the normal creation path for label/path collision protection.
        created = edit(root,project,{**scene,'operation':'scene','blockKind':saved['kind'],'documents':documents})
        name = re.findall(r'^label\s+(\w+):',created['content'],re.M)[-1]
        body_rows, plain = _rows(saved['body'])
        if plain is None: raise ValueError('剪贴内容无法安全识别。')
        for i,line in enumerate(plain):
            match = re.match(r'^(\s*(?:jump|call)\s+)'+re.escape(saved['name'])+r'(?=\s|\(|$)',line)
            if match:
                begin = len(match[1]);body_rows[i]=body_rows[i][:begin]+name+body_rows[i][begin+len(saved['name']):]
            # Explicit return-site labels must remain unique in a copied body.
            if not cut:
                site = re.search(r'\bfrom\s+([A-Za-z_]\w*)\s*$',uncomment(body_rows[i])[0]) if line.lstrip().startswith('call ') else None
                if site:
                    begin,end = site.span(1);body_rows[i]=body_rows[i][:begin]+site[1]+'_'+uuid.uuid4().hex[:10]+body_rows[i][end:]
        body = ''.join(body_rows)
        # An implicit fall-through must not acquire a different next label.
        if not body.endswith('\n'): body += '\n'
        indent, terminal = _tail(plain)
        if not terminal: body += indent+saved['ending']+'\n'
        header='\nlabel '+name+':\n'
        created['content']=created['content'].rsplit(header,1)[0]+header+body
        edits=[created]
    elif mode == 'delete_block':
        # New disk scripts must be indexed before their references can be edited.
        from .renpy_import import OMIT_DIRS
        disk={p.relative_to(root).as_posix() for p in (Path(root)/'game').rglob('*.rpy') if not any(part in OMIT_DIRS for part in p.relative_to(root).parts)}
        if disk-set(docs): raise ValueError('发现新增源码文件，请重新扫描工程后删除。')
        replacements = {path:[] for path in docs}
        names={label['name']}
        # Reject string-based references rather than guessing Python/Screen edits.
        for path,current in docs.items():
            source_rows, source_mask = _rows(current['content'])
            if source_mask is None: raise ValueError('源码无法安全识别，请修复后删除：'+path)
            for i,plain in enumerate(source_mask):
                if path==spec['path'] and spec['start']<=i<spec['end']: continue
                raw=source_rows[i]
                ref=re.match(r'^(\s*)(jump|call)\s+([\w.]+)(?=\s|\(|$)',plain)
                if ref and ref[3] in names:
                    command='return'+PENDING_OUTLET if ref[2]=='jump' else 'pass'
                    _,comment=uncomment(raw.rstrip('\r\n'))
                    replacements[path].append((i,i+1,ref[1]+command+comment+'\n'))
                elif re.search(r'''["']'''+re.escape(label['name'])+r'''["']''',uncomment(raw)[0]):
                    # Plain narration is not a runtime label reference.
                    from .renpy_import import SAY
                    if not SAY.match(raw.rstrip('\r\n')):
                        raise ValueError('此剧情被动态逻辑或系统配置引用，请先在源码处理：'+path+':'+str(i+1))
        # Prevent the preceding scene from silently falling into a different scene.
        prefix=''
        before=[l for l in project['nativeRenpy']['labels'] if l['file']==label['file'] and l['line']<label['line']]
        if before:
            previous=max(before,key=lambda l:l['line'])
            between=masked[previous['line']:spec['start']]
            indent,terminal=_tail(between)
            if not terminal and not any(row.strip() and not row[0].isspace() for row in between): prefix=indent+'return'+PENDING_OUTLET+'\n'
        replacements[spec['path']].append((spec['start'],spec['end'],prefix))
        edits=[]
        for path,changes in replacements.items():
            if not changes: continue
            edited=docs[path].copy();parts=edited['content'].splitlines(keepends=True)
            for begin,end,text in sorted(changes,reverse=True): parts[begin:end]=[text]
            edited['content']=''.join(parts);edits.append(edited)
    else:
        raise ValueError('不支持的剧情块操作。')
    overlays={d['path']:d for d in documents};overlays.update({d['path']:d for d in edits})
    projection(root,project,list(overlays.values()))
    return {'edits':edits}
