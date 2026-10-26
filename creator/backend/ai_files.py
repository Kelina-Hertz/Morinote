"""Versioned task copies. No hardlinks, shell execution, or shared mutable assets."""
from __future__ import annotations

import hashlib
import copy
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid

EDITOR_FILES = {'.creator/editor/project.json', '.creator/editor/renpy-index.json'}


def direct_project(root):
    root = Path(root).resolve()
    descriptor = root / '.creator/editor/project.json'
    return descriptor.resolve().is_relative_to(root) and descriptor.is_file()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def safe_path(root, relative, *, writable=False):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('路径必须是项目内相对路径，使用 / 分隔。')
    rel = Path(relative)
    if rel.is_absolute() or ':' in relative or '..' in rel.parts:
        raise ValueError('不能访问项目目录之外的文件。')
    path = (Path(root) / rel).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('符号链接不能指向项目目录外。')
    direct = direct_project(root)
    allowed = rel.parts[0] in ('project.json', 'assets', 'extensions', 'sources') or relative in EDITOR_FILES or direct and rel.parts[0] == 'game'
    if not allowed:
        raise ValueError('仅允许访问 project.json、assets、extensions 和只读 sources。')
    if rel.parts[0] == 'project.json' and len(rel.parts) != 1:
        raise ValueError('project.json 必须是项目文件。')
    writable_roots = ('assets', 'extensions', 'game') if direct else ('assets', 'extensions')
    if writable and (rel.parts[0] not in writable_roots or
                     path.relative_to(Path(root).resolve()).parts[0] not in writable_roots):
        raise ValueError('仅允许写入 assets 和 extensions；项目数据请使用 update_project，sources 原稿只读。')
    return path


def source_files(root):
    root = Path(root)
    result = {}
    if direct_project(root):
        from backend.renpy_import import native_files
        entries = sorted(EDITOR_FILES) + (['project.json'] if (root / 'project.json').is_file() else [])
        native, _ = native_files(root)
        entries += [i['projectPath'] for i in native]
        # Metadata precedes game paths, so independent copies immediately
        # retain the same source layout and path permissions.
        for relative in entries:
            path = safe_path(root, relative)
            if path.is_file(): result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result
    for name in ('project.json', 'assets', 'extensions', 'sources'):
        path = root / name
        if path.is_symlink():
            raise ValueError('项目来源包含符号链接；请先将素材复制到项目。')
        files = [path] if path.is_file() else sorted(path.rglob('*')) if path.exists() else []
        for file in files:
            if file.is_symlink():
                raise ValueError('项目来源包含符号链接；请先将素材复制到项目。')
            if file.is_file() and '__pycache__' not in file.parts and file.suffix not in ('.pyc', '.rpyc'):
                relative = file.relative_to(root).as_posix()
                safe_path(root, relative)
                result[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def copy_sources(source, target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for relative in source_files(source):
        out = safe_path(target, relative)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(safe_path(source, relative), out)


def review_hash(files):
    """Bind a review to the exact authored file paths and their byte hashes."""
    return hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


