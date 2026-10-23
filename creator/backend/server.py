"""Creator local API. Authenticated loopback only; no arbitrary command endpoint."""
from __future__ import annotations
import argparse
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import sys
import threading
import uuid
from urllib.parse import parse_qs, urlsplit

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.project import new_project, load_project, save_project, validate_project, review_digest, project_file
from backend.preview import Engine, PreviewManager
from backend.project import atomic_json, safe_path

MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg', '.gif', '.ogg', '.opus', '.mp3', '.wav', '.flac'}


class Service:
    def __init__(self, sdk, token, ui=None):
        os.environ['CREATOR_RENPY_SDK'] = str(Path(sdk).resolve())
        self.engine = Engine(sdk)
        self.token = token
        self.ui = Path(ui).resolve() if ui else None
        self.root = None
        self.lock = threading.RLock()
        self.preview = PreviewManager(self.engine, '', token, self.runtime_edit)
        self.project_session = uuid.uuid4().hex
        self._read_cache = None

    def read_snapshot(self):
        """Read-only consumers share one descriptor parse, keyed by disk identity."""
        root = self.current()
        descriptor = project_file(root)
        stat = descriptor.stat()
        key = (str(root), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        if self._read_cache is None or self._read_cache[0] != key:
            project = load_project(root)
            self._read_cache = (key, project, {a['id']: a for a in project['assets']})
        return self._read_cache[1:]

    def current(self):
        if self.root is None:
            raise ValueError('请先新建或打开项目。')
        return self.root

    def response(self):
        return {'project': load_project(self.root) if self.root else None, 'root': str(self.root) if self.root else None, 'session': self.project_session}

    def check_session(self, value):
        if value is not None and value != self.project_session:
            raise ValueError('项目已切换，请刷新当前项目。旧请求未执行。')

    def select_project(self, root):
        self.preview.stop()
        self.preview.session=None
        self.preview.events=[]
        self.preview.sequence=0
        self.root=Path(root)
        self.project_session=uuid.uuid4().hex
        self._read_cache=None

    def effective(self, project, scene_id, line_id, key):
        scene = next((s for s in project['scenes'] if s['id'] == scene_id), None)
        if not scene:
            raise ValueError('预览场景已被删除，请重新启动预览。')
        value, owner = None, None
        for line in scene['lines']:
            if line.get(key) is not None:
                value, owner = copy.deepcopy(line[key]), line
            if line['id'] == line_id:
                return value, owner, line
        raise ValueError('预览文字节点已被删除，请重新启动预览。')

    def runtime_edit(self, session, payload):
        root = Path(session['root'])
        project = load_project(root)
        if payload.get('revision') != project['revision']:
            raise ValueError('项目已有新修改，请同步预览后再拖动。')
        scene = payload.get('scene') or session['runtime'].get('scene') or session['entry'].get('scene')
        line = payload.get('line') or session['runtime'].get('line') or session['entry'].get('line')
        visual, owner, selected = self.effective(project, scene, line, 'visual')
        if not visual or not owner:
            raise ValueError('当前场景没有可编辑画面。')
        target = next((s for s in visual.get('sprites', []) if s['id'] == payload.get('spriteId')), None)
        mapping = {'x':'x','y':'y'}
        if payload.get('componentId'):
            instance = next((c for c in visual.get('components', []) if c['id'] == payload['componentId']), None)
            if instance:
                spec = next((c for c in project['components'] if c['id'] == instance['component']), {})
                element = next((e for e in spec.get('elements', []) if e['id'] == payload.get('elementId')), {})
                if not element.get('xProp') or not element.get('yProp'):
                    raise ValueError('该组件元素没有声明可编辑坐标。')
                mapping = {'x':element['xProp'],'y':element['yProp']}
                target = instance.setdefault('params', {})
        if target is None:
            raise ValueError('选中的元素已不在此画面。')
        for key in ('x', 'y'):
            value = payload[key]
            if not isinstance(value, (int, float)) or not (-100000 <= value <= 100000):
                raise ValueError('无效坐标。')
            target[mapping[key]] = value
        owner['visual'] = visual
        project = save_project(root, project, project['revision'])
        return {'project': project, 'root': str(root), 'taskId': session['taskId']}

    def save(self, body):
        root = self.current()
        value = copy.deepcopy(body['project'])
        review = value.get('review')
        if review and review.get('required') and review.get('confirmedHash') != review_digest(value):
            review['confirmedHash'] = None
        save_project(root, value, body['revision'])
        return self.response()

    def dispatch(self, route, body):
        self.check_session(body.get('projectSession'))
        if route == '/api/workspace/barrier':
            # POST dispatch already holds service.lock, including the entire
            # source save. This is only a completion barrier, never a save.
            return {'idle': True}
        if route.startswith('/api/workspace/'):
            from backend import workspace, native_config, native_flow, native_stage, native_assets
            root = self.current()
            project = load_project(root)
            if route.endswith('/merge'):
                from backend.source_merge import merge
                disk = workspace.read_document(root, body['path'])
                if disk['hash'] != body['diskHash'] or disk['exists'] != body.get('diskExists', True):
                    raise ValueError('磁盘文件又发生了变化，请重新比较。')
                return {**merge(body['base'], body['local'], disk['content']), 'disk': disk}
            if route.endswith('/save-recovery-ack'):
                from backend.source_transactions import acknowledge
                acknowledge(root, body['ids'])
                return {'ok': True}
            if route.endswith('/motion-source'):
                from backend.native_motion import actor_source
                candidate=workspace.projection(root,project,body.get('documents',[]),ide=body.get('ide'))
                return actor_source(root,candidate,body.get('nodeId'),body.get('tag'),body.get('documents'))
            if route.endswith('/analyze'):
                candidate=workspace.projection(root,project,body.get('documents',[]),ide=body.get('ide'))
                return {'config':native_config.catalog(root,candidate,body.get('documents')), 'flow':native_flow.graph(root,candidate,body.get('documents')), 'project':candidate}
            if route.endswith('/prepare'):
                adapter = {'config':native_config, 'flow':native_flow, 'stage':native_stage, 'assets':native_assets}.get(body['adapter'])
                if not adapter:raise ValueError('未知原生编辑器。')
                candidate=workspace.projection(root,project,body.get('documents',[]),ide=body.get('ide'))
                return adapter.edit(root,candidate,{**body['operation'],'documents':body.get('documents',[])})
            if route.endswith('/save'):
                result = workspace.commit(root, body['edits'], body['revision'], engine=self.engine, strict=body.get('strict', False))
            elif route.endswith('/restore'):
                result = workspace.restore(root, body['transaction'], body['revision'], redo=body.get('redo',False), engine=self.engine)
            elif route.endswith('/rename'):
                result = workspace.rename(root, body['path'], body['newPath'], body['hash'], body['revision'])
            elif route.endswith('/operation'):
                adapter = {'config':native_config, 'flow':native_flow, 'stage':native_stage, 'assets':native_assets}.get(body['adapter'])
                if not adapter: raise ValueError('未知原生编辑器。')
                edit = adapter.edit(root, project, body['operation'])
                result = workspace.commit(root, edit.get('edits',[edit]), body['revision'], engine=self.engine, strict=True)
            elif route.endswith('/metadata'):
                if project['revision'] != body['revision']: raise ValueError('项目已变化。')
                workspace.validate_metadata(body['ide'])
                project['ide'] = body['ide']
                if 'assets' in body:
                    updates={a['id']:a for a in body['assets']}
                    if len(updates)!=len(project['assets']) or set(updates)!={a['id'] for a in project['assets']}:raise ValueError('素材属性编辑不能更换登记 ID。')
                    for asset in project['assets']:
                        update=updates[asset['id']]
                        if any(update.get(k)!=asset.get(k) for k in ('path','nativeGamePath')):raise ValueError('更换素材请使用导入／更新文件操作。')
                        asset.update({k:update[k] for k in ('name','kind','character','costume','expression','requirement','status') if k in update})
                save_project(root, project, body['revision'])
                return self.response()
            else: raise ValueError('未知工作区操作。')
            result['session'] = self.project_session
            s = self.preview.session
            if s and not s.get('original') and Path(s['root']).resolve() == Path(root).resolve() and s['process'].poll() is None and result['project'].get('sourceStatus',{}).get('valid', True):
                try: result['preview'] = self.preview.reload()
                except ValueError as exc: result['diagnostics'] = result.get('diagnostics',[]) + [{'severity':'error','message':str(exc)}]
            return result
        if route == '/api/project/inspect':
            path = Path(body['path']).expanduser().resolve()
            if path.is_file() and path.name == 'project.json':
                path = path.parent
            descriptor_candidate = path / 'project.json'
            if descriptor_candidate.is_file():
                try:
                    data = json.loads(descriptor_candidate.read_text(encoding='utf-8-sig'))
                    if isinstance(data, dict) and data.get('schemaVersion') == 1:
                        return {'kind': 'creator', 'path': str(path)}
                except (ValueError, OSError):
                    pass
            from backend.renpy_import import game_directory
            try:
                source, _ = game_directory(path)
                return {'kind': 'renpy', 'path': str(source)}
            except ValueError:
                return {'kind': 'unknown', 'path': str(path)}
        if route == '/api/project/new':
            path = Path(body['path']).expanduser().resolve()
            new_project(path, body.get('title', '新的故事'), bool(body.get('demo')))
            self.select_project(path)
            return self.response()
        if route == '/api/project/open':
            path = Path(body['path']).expanduser().resolve()
            if path.is_file() and path.name == 'project.json':
                path = path.parent
            # Native games attach in place. Their packaging project.json is
            # never interpreted or overwritten as an editor document.
            from backend.renpy_import import game_directory, open_native
            try:
                native_root, _ = game_directory(path)
            except ValueError:
                load_project(path)
            else:
                path, _ = open_native(native_root)
            self.select_project(path)
            return self.response()
        if route == '/api/project/save':
            return self.save(body)
        if route == '/api/project/source':
            root = self.current()
            project = load_project(root)
            if body['revision'] != project['revision']:
                raise ValueError('项目已变化，请重新加载源码。')
            path = safe_path(root, body['path'])
            allowed = body['path'].startswith('extensions/') or project.get('nativeRenpy', {}).get('inPlace') and body['path'].startswith('game/')
            if not allowed or path.suffix not in ('.rpy', '.py'):
                raise ValueError('只允许编辑当前工程的 Ren’Py/Python 源码。')
            content = body['content']
            if not isinstance(content, str) or len(content.encode()) > 4 * 1024 * 1024:
                raise ValueError('源码必须小于 4 MiB。')
            path.parent.mkdir(parents=True, exist_ok=True)
            stage = path.with_name(path.name + '.tmp')
            stage.write_text(content, encoding='utf-8')
            os.replace(stage, path)
            save_project(root, project, project['revision'])
            return self.response()
        if route == '/api/project/validate':
            return {'diagnostics': validate_project(load_project(self.current()), self.current())}
        if route == '/api/assets/need':
            project=load_project(self.current())
            if body.get('revision')!=project['revision']:raise ValueError('项目已变化。')
            name=body.get('name','').strip();kind=body.get('kind','sprite')
            if not name or kind not in ('sprite','background','audio','image'):raise ValueError('请填写素材需求及类型。')
            project['assets'].append({'id':'asset_'+uuid.uuid4().hex[:12],'name':name,'kind':kind,'path':'','status':'missing','requirement':name})
            save_project(self.current(),project,project['revision'])
            return self.response()
        if route == '/api/project/confirm':
            project = load_project(self.current())
            if project['revision'] != body['revision']:
                raise ValueError('版本已变化，请先保存并重新审核。')
            missing = [a for a in project['assets'] if a.get('status') == 'missing']
            if missing:
                raise ValueError('请先处理所有缺失素材。')
            if not project.get('review', {}).get('required'):
                raise ValueError('此项目无需导入确认。')
            project['review']['confirmedHash'] = review_digest(project)
            save_project(self.current(), project, body['revision'])
            return self.response()
        if route == '/api/project/migrate':
            from backend.migration import import_timeline
            target = Path(body['path']).resolve()
            if body.get('kind') == 'renpy':
                from backend.renpy_import import import_renpy
                import_renpy(target, Path(body['sourceProject']), body.get('title'))
            else:
                import_timeline(target, Path(body['sourceDraft']), Path(body['sourceProject']))
            self.select_project(target)
            return self.response()
        if route == '/api/project/reindex':
            from backend.renpy_import import reindex_project
            root = self.current()
            project = load_project(root)
            if not project.get('nativeRenpy') or body.get('revision') != project['revision']:
                raise ValueError('请先保存当前源码工程，再重新扫描。')
            project = reindex_project(root, project)
            project['revision'] += 1
            atomic_json(project_file(root), project)
            return self.response()
        if route in ('/api/assets/import', '/api/assets/scan'):
            root = self.current()
            project = load_project(root)
            if project.get('nativeRenpy', {}).get('inPlace'):
                if route.endswith('import'):
                    raise ValueError('原工程素材文件为只读。请将素材放入 game，再使用“重新扫描”或“选择已有资源”建立映射。')
                from backend.renpy_import import refresh_native_files, index_sources
                index_path = safe_path(root, project['nativeRenpy']['indexPath'])
                previous = json.loads(index_path.read_text('utf-8')) if index_path.exists() else None
                refresh_native_files(root, project)
                baseline = index_sources(root, project, previous=previous)
                project['revision'] += 1
                atomic_json(index_path, baseline)
                atomic_json(project_file(root), project)
                return self.response()
            if route.endswith('import'):
                paths = body.get('paths', [])
                if not isinstance(paths, list) or len(paths) > 1000:
                    raise ValueError('单次最多导入 1000 个素材。')
                for source in paths:
                    source = Path(source).resolve()
                    if source.suffix.lower() not in MEDIA or not source.is_file():
                        raise ValueError('不支持的素材文件：' + source.name)
                    aid = body.get('replaceId') if len(paths) == 1 else None
                    asset = next((a for a in project['assets'] if a['id'] == aid), None)
                    aid = asset['id'] if asset else 'asset_' + uuid.uuid4().hex[:12]
                    in_place = project.get('nativeRenpy', {}).get('inPlace')
                    relative = ('game/creator_assets/' if in_place else 'assets/') + aid + source.suffix.lower()
                    if in_place and asset and asset.get('path', '').startswith('game/'):
                        if Path(asset['path']).suffix.lower() != source.suffix.lower():
                            raise ValueError('更新原素材需保持文件格式；改变引用方式请修改 RPY。')
                        relative = asset['path']
                    destination = safe_path(root, relative)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination != source:
                        shutil.copy2(source, destination)
                    values = dict(id=aid, kind=body.get('kind', 'image'), name=source.stem,
                        path=relative, status='ready')
                    if in_place:
                        values['nativeGamePath'] = relative.removeprefix('game/')
                    for field in ('character', 'costume', 'expression'):
                        values[field] = body.get(field) or (asset or {}).get(field, '')
                    if asset:
                        asset.update(values)
                    else:
                        project['assets'].append(values)
            else:
                registered = {a.get('path') for a in project['assets']}
                for asset in project['assets']:
                    path = asset.get('path', '')
                    if path and not path.startswith('builtin:') and asset.get('status') != 'placeholder':
                        asset['status'] = 'ready' if safe_path(root, path).is_file() else 'missing'
                for file in sorted((root / 'assets').rglob('*')) if not project.get('nativeRenpy', {}).get('inPlace') else []:
                    if file.is_file() and file.suffix.lower() in MEDIA:
                        relative = file.relative_to(root).as_posix()
                        if relative not in registered:
                            project['assets'].append(dict(id='asset_' + uuid.uuid4().hex[:12],name=file.stem,
                                path=relative, kind='audio' if file.suffix.lower() in ('.ogg','.opus','.wav','.mp3','.flac') else 'image',status='ready'))
            save_project(root, project, project['revision'])
            return self.response()
        if route == '/api/preview/motion':
            root=self.current();project=load_project(root)
            if not project.get('nativeRenpy',{}).get('inPlace'):raise ValueError('动作单独预览需要直接打开原 Ren’Py 工程。')
            if body.get('revision')!=project['revision']:raise ValueError('项目已变化，请保存后播放动作。')
            from backend.native_motion import actor_source
            actor=actor_source(root,project,body.get('nodeId'),body.get('tag'))
            return self.preview.start(root,{'nativeLabel':actor['label'],'motionPreview':{'nodeId':body.get('nodeId'),'tag':body.get('tag')},'scope':'continue'},'play')
        if route == '/api/preview/start':
            root = self.current()
            return self.preview.start(root, body.get('entry'), body.get('mode', 'play'))
        if route == '/api/preview/update':
            session = self.preview.session
            if not session:
                raise ValueError('请先启动预览。')
            project = load_project(session['root'])
            if body.get('revision') != project['revision']:
                raise ValueError('预览更新必须对应已保存版本。')
            return self.preview.update(body['revision'], **{k: body[k] for k in ('visual','audio','selection','replayAnimations') if k in body})
        if route == '/api/preview/native':
            session=self.preview.session
            if not session or not session.get('native') or session.get('clean') or session['mode']!='edit':
                raise ValueError('请先启动原工程编辑预览。')
            if session.get('taskId') or Path(session['root']).resolve()!=self.current().resolve():raise ValueError('预览不属于当前编辑工程。')
            return self.preview.command('native', {'command':body['command']})
        if route == '/api/preview/mode':
            return self.preview.set_mode(body['mode'])
        if route == '/api/preview/reload':
            return self.preview.reload()
        if route == '/api/preview/screenshot':
            return self.preview.command('screenshot', {})
        if route == '/api/preview/stop':
            return self.preview.stop()
        if route == '/api/build':
            root = self.current()
            if load_project(root).get('nativeRenpy',{}).get('inPlace'):
                return self.engine.check_native(root, lint=bool(body.get('lint', True)))
            return self.engine.build(root, lint=bool(body.get('lint', True)))
        if route == '/api/export':
            return self.engine.export(self.current(), body['path'])
        raise ValueError('未知操作：' + route)


def create_server(service, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, value, status=200, mime='application/json; charset=utf-8', cookie=False, headers=None):
            try:self.write_response(value,status,mime,cookie,headers)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

        def write_response(self, value, status=200, mime='application/json; charset=utf-8', cookie=False, headers=None):
            content = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, default=str).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', (headers or {}).get('Cache-Control', 'no-store'))
            for key, value in (headers or {}).items():
                if key != 'Cache-Control': self.send_header(key, value)
            self.send_header('X-Content-Type-Options', 'nosniff')
            if mime.startswith('image/svg'):
                self.send_header('Content-Security-Policy', "sandbox; default-src 'none'; style-src 'unsafe-inline'")
            if cookie:
                self.send_header('Set-Cookie', f'creator_session={service.token}; HttpOnly; SameSite=Strict; Path=/')
            self.end_headers()
            self.wfile.write(content)

        def trusted(self, allow_bootstrap=False):
            route = urlsplit(self.path)
            host = self.headers.get('Host', '')
            expected = f'127.0.0.1:{self.server.server_port}'
            if host != expected:
                return False
            # Electron's file:// renderer requests registered media cross-site.
            # Only this read-only route accepts an unguessable session token in
            # its URL; project APIs and bootstrap retain the origin check.
            if self.command == 'GET' and route.path == '/api/media':
                candidate = parse_qs(route.query).get('token', [''])[0]
                if secrets.compare_digest(candidate, service.token):
                    return True
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + expected:
                return False
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return False
            if allow_bootstrap:
                return True
            token = self.headers.get('Authorization', '').removeprefix('Bearer ')
            if secrets.compare_digest(token, service.token):
                return True
            from http.cookies import SimpleCookie
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
            except Exception:
                return False
            return 'creator_session' in cookie and secrets.compare_digest(cookie['creator_session'].value, service.token)

        def do_GET(self):
            if urlsplit(self.path).path == '/api/media':
                return self.read_media()
            if urlsplit(self.path).path=='/bridge/poll':return self.read_request()
            # Scope check and resource lookup must observe the same project.
            with service.lock:
                self.read_request()

        def read_media(self):
            if not self.trusted():
                return self.send({'error': '未授权的本机请求。'}, 401)
            try:
                query = parse_qs(urlsplit(self.path).query)
                with service.lock:
                    service.check_session(query.get('projectSession', [None])[0])
                    session, root = service.project_session, service.current()
                    project, assets = service.read_snapshot()
                    asset = assets.get(query.get('id', [''])[0])
                    if asset and asset.get('virtual'): asset = assets.get(asset.get('mediaAssetId'))
                    if not asset or not asset.get('path') or asset['path'].startswith('builtin:'):
                        return self.send({'error': '无可读取的素材文件。'}, 404)
                    path = safe_path(root, asset['path'])
                    version = query.get('version', [None])[0]
                    if version and version != str(project['revision']):
                        return self.send({'error': '素材版本已变化，请刷新。'}, 409)
                    if path.suffix.lower() not in MEDIA: raise ValueError('不支持的媒体类型。')
                # Image decoding, disk IO and sending bytes never hold the edit lock.
                stat = path.stat()
                stamp = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
                size = min(512, max(64, int(query.get('thumbnail', ['0'])[0]))) if 'thumbnail' in query else 0
                etag = '"' + hashlib.sha256((session + str(path) + repr(stamp) + str(size)).encode()).hexdigest() + '"'
                headers = {'Cache-Control': 'private, max-age=0, must-revalidate', 'ETag': etag}
                if self.headers.get('If-None-Match') == etag:
                    return self.send(b'', 304, headers=headers)
                if size:
                    from backend.media_cache import thumbnail
                    path = thumbnail(path, safe_path(root, '.creator/editor/cache/thumbnails'), size, stamp)
                data = path.read_bytes()
                with service.lock:
                    service.check_session(session)
                return self.send(data, mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream', headers=headers)
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.send({'error': str(error)}, 400)

        def read_request(self):
            route = urlsplit(self.path)
            query = parse_qs(route.query)
            if not self.trusted(allow_bootstrap=route.path == '/api/bootstrap' or not route.path.startswith(('/api/', '/bridge/'))):
                return self.send({'error': '未授权的本机请求。'}, 401)
            try:
                if route.path == '/api/bootstrap':
                    return self.send({'baseUrl': service.preview.address, 'desktop': False}, cookie=True)
                if route.path == '/api/project':
                    return self.send(service.response())
                service.check_session(query.get('projectSession', [None])[0])
                if route.path == '/api/workspace':
                    from backend.workspace import file_tree
                    from backend.native_config import catalog
                    from backend.native_flow import graph
                    project = load_project(service.current())
                    overlays=None
                    if project.get('sourceStatus',{}).get('valid') is False:
                        from backend.workspace import read_document
                        path=service.current()/'.creator/editor/last-valid-source.json'
                        if path.exists():overlays=[{**d,'hash':read_document(service.current(),d['path'])['hash']} for d in json.loads(path.read_text('utf-8'))]
                    return self.send({'tree': file_tree(service.current()), 'config': catalog(service.current(),project,overlays), 'flow': graph(service.current(),project,overlays), 'session':service.project_session})
                if route.path == '/api/workspace/document':
                    from backend.workspace import read_document
                    return self.send(read_document(service.current(),query.get('path',[''])[0]))
                if route.path == '/api/workspace/save-recovery':
                    from backend.source_transactions import notices
                    load_project(service.current())
                    return self.send(notices(service.current()))
                if route.path == '/api/project/source':
                    relative = query.get('path', [''])[0]
                    path = safe_path(service.current(), relative)
                    project = load_project(service.current())
                    allowed = relative.startswith('extensions/') or project.get('nativeRenpy', {}).get('inPlace') and relative in project['nativeRenpy']['codeFiles']
                    if not allowed or path.suffix not in ('.rpy', '.py'):
                        raise ValueError('只允许读取组件源码。')
                    return self.send({'content': path.read_text(encoding='utf-8') if path.exists() else ''})
                if route.path == '/api/preview/status':
                    status=service.preview.status(int(query.get('after', [0])[0]))
                    if service.root:status['projectRevision']=service.read_snapshot()[0]['revision']
                    return self.send(status)
                if route.path == '/bridge/poll':
                    return self.send(service.preview.poll(query.get('session', [''])[0], int(query.get('after',[0])[0])))
                if service.ui and not route.path.startswith(('/api/', '/bridge/')):
                    relative = route.path.lstrip('/') or 'index.html'
                    path = (service.ui / relative).resolve()
                    if not path.is_relative_to(service.ui):
                        raise ValueError('无效资源路径。')
                    if not path.is_file():
                        path = service.ui / 'index.html'
                    return self.send(path.read_bytes(), mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
                self.send({'error': '不存在此接口。'}, 404)
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.send({'error': str(error)}, 400)

        def do_POST(self):
            if not self.trusted():
                return self.send({'error': '未授权的本机请求。'}, 401)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not (0 < size <= 16 * 1024 * 1024):
                    raise ValueError('请求体必须小于 16 MiB。')
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError('请求体必须是 JSON 对象。')
                route = urlsplit(self.path).path
                if route == '/bridge/event':
                    return self.send(service.preview.receive(body['sessionId'], body['type'], body.get('payload', {})))
                with service.lock:
                    result = service.dispatch(route, body)
                self.send(result)
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.send({'error': str(error)}, 400)
            except Exception as error:
                self.send({'error': type(error).__name__ + ': ' + str(error)}, 500)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    service.preview.address = f'http://127.0.0.1:{server.server_port}'
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--token', default=None)
    parser.add_argument('--sdk', required=True)
    parser.add_argument('--ready-file')
    parser.add_argument('--ui')
    parser.add_argument('--project')
    args = parser.parse_args()
    service = Service(args.sdk, args.token or secrets.token_urlsafe(32), args.ui)
    if args.project:
        service.dispatch('/api/project/open', {'path': args.project})
    server = create_server(service, args.port)
    if args.ready_file:
        atomic_json(Path(args.ready_file), {'port': server.server_port})
    print(json.dumps({'port': server.server_port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.preview.stop()
        server.server_close()


if __name__ == '__main__':
    main()
