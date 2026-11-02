"""Privileged publication of registered generation outputs; never a general import."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time

from .project import atomic_json, load_project, project_file


def validate_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('无效的生成任务编号。')
    return value


def no_links(root, target):
    root = Path(root).resolve()
    target = Path(target)
    if not target.is_relative_to(root):
        raise ValueError('生成产物超出工程。')
    current = root
    for part in target.relative_to(root).parts:
        current = current / part
        if current.is_symlink() or current.exists() and hasattr(current, 'is_junction') and current.is_junction():
            raise ValueError('生成目录不能包含链接或联接。')


def header(data, kind):
    if kind == 'image':
        if len(data) > 20 * 1024 * 1024:
            raise ValueError('生成图片超过大小限制。')
        if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
            width, height = int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
            if not width or not height or width * height > 16777216:
                raise ValueError('生成图片尺寸无效。')
            return 'png'
        if data[:3] == b'\xff\xd8\xff' and len(data) > 32:
            return 'jpg'
    elif kind == 'voice' and 32 <= len(data) <= 10 * 1024 * 1024:
        if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
            return 'wav'
        if data[:3] == b'ID3' or data[0] == 255 and data[1] & 224 == 224:
            return 'mp3'
    raise ValueError('生成产物的实际文件格式无效。')


class GeneratedMedia:
    def __init__(self):
        self.receipts = {}

    def register(self, root, session, body):
        job = validate_id(body.get('jobId'))
        artifact = body.get('artifact', {})
        if not re.fullmatch(r'[0-9a-f]{64}', str(artifact.get('sha256', ''))):
            raise ValueError('产物缺少有效摘要。')
        if body.get('kind') not in ('image', 'voice') or not 0 < artifact.get('bytes', 0) <= 20 * 1024 * 1024:
            raise ValueError('产物登记无效。')
        receipt = secrets.token_hex(32)
        destination = body.get('destination', 'project')
        if destination not in ('project', 'candidate'):
            raise ValueError('无效的产物发布范围。')
        self.receipts[receipt] = {'root': str(Path(root).resolve()), 'session': session, 'jobId': job, 'destination': destination,
                                  'kind': body['kind'], 'artifact': artifact, 'created': time.time()}
        return {'receipt': receipt}

    def publish(self, root, session, body):
        record = self.receipts.get(body.get('receipt'))
        if not record or record['root'] != str(Path(root).resolve()) or record['session'] != session:
            raise ValueError('生成产物凭证已失效或项目已切换。')
        if time.time() - record['created'] > 600:
            raise ValueError('生成产物凭证已过期。')
        try:
            data = base64.b64decode(body.get('data', ''), validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError('无效的生成产物数据。') from exc
        sha = hashlib.sha256(data).hexdigest()
        if sha != record['artifact']['sha256'] or len(data) != record['artifact']['bytes']:
            raise ValueError('生成产物与登记摘要不一致。')
        extension = header(data, record['kind'])
        folder = 'images' if record['kind'] == 'image' else 'audio'
        candidate_only = record.get('destination') == 'candidate'
        relative = (f'.creator/media/candidates/{record["jobId"]}/output.{extension}' if candidate_only else
                    f'game/{folder}/creator_generated/{record["jobId"]}/output.{extension}')
        target = Path(root) / relative
        no_links(root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        no_links(root, target)
        if target.exists():
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise ValueError('同名生成产物已存在且摘要不同，未覆盖。')
        else:
            fd, temporary = tempfile.mkstemp(prefix='.creator-', dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Windows rename fails when destination exists; POSIX hard-link
                # publication supplies the same non-overwriting guarantee.
                if os.name == 'nt':
                    os.rename(temporary, target)
                else:
                    os.link(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        if candidate_only:
            manifest = Path(root) / '.creator/media/candidates.json'
            no_links(root, manifest)
            records = json.loads(manifest.read_text('utf-8')) if manifest.exists() else {'version': 1, 'artifacts': {}}
            records['artifacts'][record['jobId']] = {'kind': record['kind'], 'sha256': sha, 'path': relative, 'artifact': record['artifact']}
            atomic_json(manifest, records)
            return {'jobId': record['jobId'], 'path': relative, 'sha256': sha}
        from .renpy_import import refresh_native_files, index_sources
        project = load_project(root)
        index_path = Path(root) / project['nativeRenpy']['indexPath']
        previous = json.loads(index_path.read_text('utf-8')) if index_path.exists() else None
        refresh_native_files(root, project)
        baseline = index_sources(root, project, previous=previous)
        project['revision'] += 1
        atomic_json(index_path, baseline)
        atomic_json(project_file(root), project)
        asset = next(a for a in project['nativeAssetLibrary']['resources'] if a['nativeGamePath'] == relative[5:])
        manifest = Path(root) / '.creator/media/artifacts.json'
        no_links(root, manifest)
        records = json.loads(manifest.read_text('utf-8')) if manifest.exists() else {'version': 1, 'artifacts': {}}
        records['artifacts'][record['jobId']] = {'kind': record['kind'], 'sha256': sha, 'path': relative, 'assetId': asset['id']}
        atomic_json(manifest, records)
        return {'jobId': record['jobId'], 'assetId': asset['id'], 'path': relative, 'gamePath': relative[5:], 'revision': project['revision']}

    def preview(self, root, session, body, tasks):
        """Only the host can install registered candidates into a new execution snapshot."""
        from . import workspace, media_authoring
        from .ai_files import source_files
        from .compiler import renpy_text
        root = Path(root)
        manifest = root / '.creator/media/candidates.json'
        no_links(root, manifest)
        records = json.loads(manifest.read_text('utf-8')) if manifest.exists() else {'artifacts': {}}
        payloads = []
        for item in body.get('imports', []):
            job = validate_id(item.get('jobId'))
            record = records['artifacts'].get(job)
            if not record or record['sha256'] != item.get('sha256') or record['kind'] != item.get('kind'):
                raise ValueError('候选产物未登记或版本不匹配。')
            source = root / record['path']
            no_links(root, source)
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != record['sha256']:
                raise ValueError('候选文件摘要不匹配。')
            extension = header(data, record['kind'])
            folder = 'images' if record['kind'] == 'image' else 'audio'
            payloads.append((item, data, f'game/{folder}/creator_generated/{job}/output.{extension}'))
        task = tasks.new('候选试玩 · ' + body['title'], body['state'], {'candidateVersion': body['candidateVersion']})
        target = Path(task['root'])
        imports = []
        for item, data, relative in payloads:
            filename = target / relative
            no_links(target, filename)
            if filename.exists() and hashlib.sha256(filename.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('临时工程存在冲突的候选产物。')
            workspace.atomic_bytes(filename, data)
            imports.append({**item, 'gamePath': relative[5:]})
        project = tasks.reindex(target)
        prepared = media_authoring.prepare(target, project, {**body, 'documents': [], 'imports': imports})
        for edit in prepared['edits']:
            workspace.atomic_bytes(workspace.source_path(target, edit['path']), edit['content'].encode('utf-8'))
        if body['kind'] != 'fragment':
            key = validate_id(body['creativeId'])
            label = 'creator_candidate_' + key
            rows = ['label ' + label + ':', '    scene black']
            item = imports[0]
            if body['kind'] == 'image':
                rows.append('    show expression ' + renpy_text(item['gamePath']))
                rows.append('    ' + renpy_text(body['title']))
            else:
                rows.append('    play voice ' + renpy_text(item['gamePath']))
                rows.append('    ' + renpy_text(body['request']['displayText']))
                rows.append('    stop voice')
            rows += ['    scene black', '    return', '']
            relative = 'game/creator_fragments/' + label + '.rpy'
            workspace.atomic_bytes(workspace.source_path(target, relative), '\n'.join(rows).encode('utf-8'))
            prepared.update(label=label, path=relative)
        project = tasks.reindex(target)
        meta = tasks.meta(task['id'])
        # These are host-installed immutable inputs, not edits made by an agent.
        meta.update(baselineSnapshot=source_files(target), assets=project.get('assets', []),
                    requirements=project.get('nativeAssetLibrary', {}).get('entries', []), baseIde=project.get('ide', {}),
                    mediaCandidateVersion=body['candidateVersion'])
        tasks.store(meta)
        return {'task': task, 'label': prepared['label'], 'candidateVersion': body['candidateVersion']}
