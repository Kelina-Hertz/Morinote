"""Pinned engine build, export, and authenticated live preview sessions."""
from __future__ import annotations
import copy
import json
import os
import re
from pathlib import Path
import subprocess
import threading
import time
import uuid


def interactive_desktop():
    if os.name != 'nt':
        return True
    import ctypes
    from ctypes import wintypes
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user.GetThreadDesktop.restype = wintypes.HANDLE
    user.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, ctypes.c_uint, ctypes.POINTER(wintypes.DWORD)]
    name = ctypes.create_unicode_buffer(256)
    needed = wintypes.DWORD()
    return bool(user.GetUserObjectInformationW(user.GetThreadDesktop(kernel.GetCurrentThreadId()), 2, name, ctypes.sizeof(name), ctypes.byref(needed))) and name.value.lower() == 'default'


class Engine:
    def __init__(self, sdk):
        self.sdk = Path(sdk).resolve()
        self.command = [str(self.sdk / 'lib/py3-windows-x86_64/python.exe'), str(self.sdk / 'renpy.py')]
        if not all(Path(p).is_file() for p in self.command):
            raise ValueError('未找到捆绑的 Ren’Py 8.5.3 SDK。')

    def environment(self, output):
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('CREATOR_', 'SW_PREVIEW_')) or key in ('RENPY_SKIP_MAIN_MENU', 'RENPY_PATH_TO_SAVES'):
                env.pop(key)
        env['RENPY_PATH_TO_SAVES'] = str(Path(output) / 'saves')
        env['RENPY_SKIP_SPLASHSCREEN'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        return env

    def run(self, output, command='compile', extra=(), timeout=90, log_dir=None):
        output = Path(output).resolve()
        logs = Path(log_dir).resolve() if log_dir else output
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / (command + '.log')
        env = self.environment(logs)
        started = time.time()
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run(self.command + [str(output), command, *extra],
                    stdout=stream, stderr=subprocess.STDOUT, env=env, cwd=self.sdk,
                    creationflags=flags, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f'Ren’Py {command} 超时；日志：{log}') from exc
        contents = log.read_text(encoding='utf-8', errors='replace')[-40000:]
        errors = output / 'errors.txt'
        if result.returncode or (errors.exists() and errors.stat().st_mtime >= started):
            if errors.exists():
                contents += '\n' + errors.read_text(encoding='utf-8', errors='replace')[-12000:]
            raise ValueError(f'Ren’Py {command} 失败：\n{contents}')
        return contents

    def check_native(self, root, *, lint=False):
        """Check the actual source set without rebuilding it or gating on assets."""
        from backend.project import load_project
        root = Path(root).resolve()
        document = load_project(root)
        logs = root / '.creator/checks/native-source'
        contents = self.run(root, log_dir=logs)
        if lint:
            contents += '\n' + self.run(root, 'lint', log_dir=logs)
        return {'output': str(root), 'revision': document['revision'], 'log': contents, 'diagnostics': []}

    def build(self, root, *, entry=None, preview=False, lint=False, output=None):
        from backend.compiler import generate_project
        from backend.project import load_project
        root = Path(root).resolve()
        document = load_project(root)
        output = Path(output).resolve() if output else root / '.creator/builds' / (str(document['revision']) + '-' + uuid.uuid4().hex[:10])
        output.mkdir(parents=True, exist_ok=True)
        result = generate_project(root, output, entry=entry, preview=preview)
        log = self.run(output)
        if lint:
            log += '\n' + self.run(output, 'lint')
        return {**result, 'output': str(output), 'revision': document['revision'], 'log': log}

    def export(self, root, destination):
        destination = Path(destination).resolve()
        from backend.project import load_project
        if load_project(root).get('nativeRenpy', {}).get('inPlace'):
            raise ValueError('原工程请使用 Ren’Py 启动器的“构建发行版”。IDE 不再重新生成或导出原工程。')
        if destination == Path(root).resolve() or destination.is_relative_to(Path(root).resolve() / 'assets'):
            raise ValueError('导出目录不能覆盖项目或素材目录。')
        destination.mkdir(parents=True, exist_ok=True)
        build = self.build(root, lint=True)
        output = Path(build['output'])
        env = self.environment(output)
        log = output / 'export.log'
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        started = time.time()
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(self.command + [str(self.sdk / 'launcher'), 'distribute', str(output),
                '--destination', str(destination), '--package', 'pc', '--no-update'],
                cwd=self.sdk, env=env, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=flags, timeout=300, check=False)
        contents = log.read_text(encoding='utf-8', errors='replace')[-40000:]
        packages = [p for p in destination.glob('*.zip') if p.stat().st_mtime >= started - 2]
        if result.returncode or not packages:
            raise ValueError('导出失败：' + contents)
        # Export templates must not include development credentials or preview bridges.
        import zipfile
        for package in packages:
            with zipfile.ZipFile(package) as archive:
                if any('creator_bridge' in n or '/.creator/' in n for n in archive.namelist()):
                    raise ValueError('导出检查失败：包含编辑器运行文件。')
        return {'path': str(destination), 'packages': [str(p) for p in packages], 'log': contents}


class PreviewManager:
    def __init__(self, engine, address, token, on_edit):
        self.engine, self.address, self.token, self.on_edit = engine, address, token, on_edit
        self.lock = threading.RLock()
        self.session = None
        self.events = []
        self.sequence = 0

    def event(self, kind, payload=None):
        with self.lock:
            self.sequence += 1
            event = {'seq': self.sequence, 'type': kind, 'time': time.time(), **(payload or {})}
            self.events.append(event)
            self.events = self.events[-500:]
            return event

    def start(self, root, entry=None, mode='play', task_id=None):
        if mode not in ('edit', 'play'):
            raise ValueError('无效预览模式。')
        if not interactive_desktop():
            raise ValueError('当前服务位于隔离桌面，不能显示窗口。请通过制作器桌面程序启动试玩。')
        from backend.project import load_project
        document=load_project(root)
        if document.get('nativeRenpy',{}).get('inPlace'):
            if (entry or {}).get('clean') is True:
                return self.start_original(root,document,task_id)
            return self.start_native_direct(root,document,entry or {},mode,task_id)
        with self.lock:
            build = self.engine.build(root, entry=entry, preview=True)
            output = Path(build['output'])
            bridge = Path(__file__).with_name('creator_bridge.rpy')
            native_clean = bool(build.get('native')) and (entry or {}).get('clean',build.get('nativeLabel')=='start')
            if build.get('native'):
                if not native_clean:
                    bridge = Path(__file__).with_name('creator_native_preview.rpy')
                    (output / 'game/creator_native_preview.rpy').write_text(bridge.read_text(encoding='utf-8'), encoding='utf-8')
                    self.native_index(root,output)
                else: mode = 'play'
            else:
                (output / 'game/creator_bridge.rpy').write_text(bridge.read_text(encoding='utf-8'), encoding='utf-8')
            self.engine.run(output)
            sid = uuid.uuid4().hex
            env = self.engine.environment(output)
            env.update(CREATOR_BRIDGE_URL=self.address, CREATOR_BRIDGE_TOKEN=self.token,
                       CREATOR_PREVIEW_SESSION=sid, CREATOR_PREVIEW_MODE=mode,
                       CREATOR_PREVIEW_REVISION=str(build['revision']))
            if build.get('native'):
                if not native_clean:
                    test={**(entry or {}),'nativeLabel':build['nativeLabel']}
                    if not isinstance(test.get('args',[]),list) or not isinstance(test.get('state',{}),dict) or not isinstance(test.get('initialize',[]),list):
                        raise ValueError('测试参数需要数组，状态需要对象，前置调用需要标签数组。')
                    from backend.project import load_project
                    names={l['name'] for l in load_project(root)['nativeRenpy']['labels']}
                    if any(name not in names for name in test.get('initialize',[])) or any(not re.fullmatch(r'(?:persistent\.)?[A-Za-z_]\w*',key) or key.startswith('_') for key in test.get('state',{})):
                        raise ValueError('测试初始化标签或状态名无效。')
                    env.update(RENPY_SKIP_MAIN_MENU='1', CREATOR_NATIVE_TEST=json.dumps(test,ensure_ascii=False))
                else:
                    env.pop('RENPY_SKIP_SPLASHSCREEN', None)
            # Invalid test setup must not close the last working preview.
            self.stop()
            options = {}
            if os.name == 'nt':
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = 1
                options['startupinfo'] = startup
                options['creationflags'] = subprocess.CREATE_NO_WINDOW
            with (output / 'launch.log').open('w', encoding='utf-8') as stream:
                child = subprocess.Popen(self.engine.command + [str(output)], cwd=self.engine.sdk, env=env,
                    stdout=stream, stderr=subprocess.STDOUT, **options)
            self.session = dict(id=sid, root=str(root), revision=build['revision'], entry=entry or {}, mode=mode,
                taskId=task_id, output=str(output), process=child, commands=[], commandSequence=0,
                runtime={'native': bool(build.get('native')),'clean':native_clean}, status='running' if native_clean else 'starting', lastHeartbeat=time.time(), startedAt=time.time(), native=bool(build.get('native')), clean=native_clean)
            self.event('started', {'sessionId': sid, 'revision': build['revision'], 'pid': child.pid})
            return self.status()

    def start_native_direct(self, root, document, entry, mode, task_id=None):
        """Run the authored root with a session-only external test/observation script."""
        root=Path(root).resolve()
        if document.get('sourceStatus',{}).get('valid') is False:
            raise ValueError('请先修复源码错误，再启动片段预览。')
        names={label['name'] for label in document['nativeRenpy']['labels']}
        test={**entry,'nativeLabel':entry.get('nativeLabel','start')}
        test.setdefault('scope','fragment')
        if test['scope'] not in ('fragment','continue'):raise ValueError('无效片段试玩范围。')
        if test['nativeLabel'] not in names:raise ValueError('测试入口标签不存在。')
        if not isinstance(test.get('args',[]),list) or not isinstance(test.get('state',{}),dict) or not isinstance(test.get('initialize',[]),list):
            raise ValueError('测试参数需要数组，状态需要对象，前置调用需要标签数组。')
        if any(not isinstance(name,str) or name not in names for name in test.get('initialize',[])) or any(not re.fullmatch(r'(?:persistent\.)?[A-Za-z_]\w*',key) or key.startswith('_') for key in test.get('state',{})):
            raise ValueError('测试初始化标签或状态名无效。')
        if any(label.startswith('_cn_') for label in names) or any((root/'game'/('creator_native_preview'+suffix)).exists() for suffix in ('.rpy','.rpyc')):
            raise ValueError('原工程存在与编辑桥冲突的名称，请使用原游戏试玩或调整名称。')
        with self.lock:
            sid=uuid.uuid4().hex
            output=root/'.creator/native-preview'/sid
            support=output/'support'
            support.mkdir(parents=True,exist_ok=True)
            bridge=Path(__file__).with_name('creator_native_preview.rpy')
            (support/bridge.name).write_bytes(bridge.read_bytes())
            if test.get('motionPreview'):
                from backend.native_motion import preview_script
                (support/'creator_motion_clip.rpy').write_text(preview_script(root,document,test['motionPreview']),encoding='utf-8')
            self.native_index(root,output)
            env=self.engine.environment(output.parent)
            # Ren'Py 8.5.3 loads scripts from additional search paths. Keep the
            # authored game first and add only this session's editor support.
            inherited=env.get('RENPY_SEARCHPATH','')
            env['RENPY_SEARCHPATH']='::'.join(value for value in (inherited,str(support)) if value)
            env.update(CREATOR_BRIDGE_URL=self.address,CREATOR_BRIDGE_TOKEN=self.token,
                CREATOR_PREVIEW_SESSION=sid,CREATOR_PREVIEW_MODE=mode,
                CREATOR_PREVIEW_REVISION=str(document['revision']),CREATOR_NATIVE_TEST=json.dumps(test,ensure_ascii=False),
                CREATOR_NATIVE_INDEX=str(output/'.creator-native-index.json'),CREATOR_PREVIEW_OUTPUT=str(output),RENPY_SKIP_MAIN_MENU='1')
            self.stop()
            options={}
            if os.name=='nt':
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=1
                options.update(startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
            launch_log=output/'launch.log'
            with launch_log.open('w',encoding='utf-8') as stream:
                child=subprocess.Popen(self.engine.command+[str(root)],cwd=self.engine.sdk,env=env,stdout=stream,stderr=subprocess.STDOUT,**options)
            self.session=dict(id=sid,root=str(root),revision=document['revision'],entry=test,mode=mode,taskId=task_id,
                output=str(root),launchLog=str(launch_log),process=child,commands=[],commandSequence=0,
                runtime={'native':True,'clean':False,'direct':True,'projectPath':str(root),'scope':test['scope'],'motionPreview':bool(test.get('motionPreview'))},status='starting',
                lastHeartbeat=time.time(),startedAt=time.time(),native=True,clean=False)
            self.event('started',{'sessionId':sid,'revision':document['revision'],'pid':child.pid,'direct':True})
            return self.status()

    def start_original(self, root, document, task_id=None):
        """Launch the authored project as Ren'Py does; no compiler or asset gate."""
        root=Path(root).resolve()
        if not (root/'game').is_dir():raise ValueError('原工程的 game 目录不存在。')
        with self.lock:
            sid=uuid.uuid4().hex
            logs=root/'.creator/original-preview'/sid
            logs.mkdir(parents=True,exist_ok=True)
            # Keep editor test saves separate, but load all code/media directly
            # from the authored project, including its RPA/RPYC and runtime lookup.
            env=self.engine.environment(logs.parent)
            env.pop('RENPY_SKIP_SPLASHSCREEN',None)
            env.pop('RENPY_SKIP_MAIN_MENU',None)
            self.stop()
            options={}
            if os.name=='nt':
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=1
                options.update(startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
            launch_log=logs/'launch.log'
            with launch_log.open('w',encoding='utf-8') as stream:
                child=subprocess.Popen(self.engine.command+[str(root)],cwd=self.engine.sdk,env=env,stdout=stream,stderr=subprocess.STDOUT,**options)
            self.session=dict(id=sid,root=str(root),revision=document['revision'],entry={'clean':True},mode='play',
                taskId=task_id,output=str(root),launchLog=str(launch_log),process=child,commands=[],commandSequence=0,
                runtime={'native':True,'clean':True,'original':True,'projectPath':str(root)},status='running',
                lastHeartbeat=time.time(),startedAt=time.time(),native=True,clean=True,original=True)
            self.event('started',{'sessionId':sid,'revision':document['revision'],'pid':child.pid,'original':True})
            return self.status()

    def native_index(self, root, output):
        from backend.project import load_project
        project=load_project(root)
        commands={}
        for scene in project['scenes']:
            for line in scene['lines']:
                visual=line.get('visual') or {}
                bg=visual.get('nativeBackground',{}).get('source')
                if bg: commands.setdefault(bg['path']+':'+str(bg['line']),{})['clear']=True
                for sprite in visual.get('sprites',[]):
                    source=sprite.get('nativeSource')
                    if source:
                        item=commands.setdefault(source['path']+':'+str(source['line']),{})
                        objects=item.setdefault('objects',[])
                        if not any(s['id']==sprite['id'] for s in objects):objects.append(sprite)
        variables=set()
        for path in (Path(root)/'game').rglob('*.rpy'):
            variables.update(re.findall(r'(?m)^default\s+([\w.]+)\s*=',path.read_text('utf-8-sig')))
        from backend.native_tracks import catalog
        scripts=[(item,(Path(root)/item['projectPath']).read_text('utf-8-sig')) for item in project['nativeRenpy']['files'] if item['gamePath'].endswith('.rpy')]
        _,images,_,_=catalog(project,scripts)
        props={name:image['props'] for name,image in images.items() if image}
        (Path(output)/'.creator-native-index.json').write_text(json.dumps({'commands':commands,'variables':sorted(variables),'images':props,'audioChannels':[c['id'] for c in project['nativeRenpy'].get('audioChannels',[])]},ensure_ascii=False),encoding='utf-8')

    def status(self, after=0):
        with self.lock:
            s = self.session
            if s and s['status'] not in ('stopped', 'exited'):
                for name in ('traceback.txt','errors.txt'):
                    error_file = Path(s['output']) / name
                    seen = s.setdefault('seenErrors',{}).get(name,s.get('startedAt',0))
                    if error_file.exists() and error_file.stat().st_mtime > seen:
                        s['seenErrors'][name] = error_file.stat().st_mtime
                        s['error'] = error_file.read_text(encoding='utf-8', errors='replace')[-12000:]
                        s['status'] = 'error'
                        self.event('error', {'message': s['error']})
            if s and s['process'].poll() is not None and s['status'] not in ('stopped', 'exited', 'error'):
                s['status'] = 'exited' if s['process'].returncode == 0 else 'error'
                if s['status'] == 'error':
                    s['error'] = Path(s.get('launchLog',Path(s['output']) / 'launch.log')).read_text(encoding='utf-8', errors='replace')[-12000:]
                self.event(s['status'], {'error': s.get('error', '')})
            result = {'status': s['status'] if s else 'stopped', 'events': [e for e in self.events if e['seq'] > after]}
            if s:
                result.update(sessionId=s['id'], revision=s['revision'], pid=s['process'].pid, mode=s['mode'],
                    runtime=s['runtime'], taskId=s['taskId'], output=s['output'], error=s.get('error'))
            return result

    def command(self, kind, payload):
        with self.lock:
            if not self.session or self.session['process'].poll() is not None:
                raise ValueError('请先启动预览。')
            if self.session.get('original'):raise ValueError('原游戏试玩不带编辑连接，请使用片段编辑预览。')
            s = self.session
            s['commandSequence'] += 1
            command = {'id': s['commandSequence'], 'type': kind, 'revision': s['revision'], **payload}
            s['commands'].append(command)
            s['commands'] = s['commands'][-200:]
            return self.status()

    def update(self, revision, **payload):
        with self.lock:
            if not self.session:
                raise ValueError('请先启动预览。')
            if self.session.get('original'):raise ValueError('原游戏试玩保持原交互，请另开片段编辑预览。')
            if self.session.get('native'):
                raise ValueError('源码兼容工程的演出由原 RPY 执行；保存后请重新载入。')
            if revision < self.session['revision']:
                raise ValueError('此更新版本已过期。')
            self.session['revision'] = revision
            return self.command('update', payload)

    def set_mode(self, mode):
        if mode not in ('play', 'edit'):
            raise ValueError('无效模式。')
        with self.lock:
            if not self.session:
                raise ValueError('请先启动预览。')
            if self.session.get('original'):raise ValueError('原游戏试玩保持原交互，请另开片段编辑预览。')
            if self.session.get('native') and (mode=='play' and self.session['mode']=='edit' or self.session.get('clean')):
                return self.start(Path(self.session['root']),entry={**self.session['entry'],'clean':False},mode=mode,task_id=self.session['taskId'])
            self.session['mode'] = mode
            return self.command('mode', {'mode': mode})

    def reload(self):
        """Validate a new build before replacing the isolated running scripts."""
        import shutil
        with self.lock:
            s = self.session
            if not s or s['process'].poll() is not None:
                raise ValueError('请先启动预览。')
            if s.get('native'):
                self.event('reloading',{'message':'检查通过后，从配置的测试入口重新执行原剧情。'})
                return self.start(Path(s['root']),entry=s['entry'],mode=s['mode'],task_id=s['taskId'])
            entry = dict(s['entry'])
            context = s['runtime'].get('context', s['runtime'])
            if context.get('scene'):
                entry = {'scene': context['scene']}
            if s['runtime'].get('state'):
                entry['state'] = s['runtime']['state']
            build = self.engine.build(Path(s['root']), entry=entry, preview=True)
            source = Path(build['output']) / 'game'
            target = Path(s['output']) / 'game'
            # All paths here are generated output under this managed preview session.
            expected_root = Path(s['root']).resolve() / '.creator/builds'
            if not target.resolve().is_relative_to(expected_root):
                raise ValueError('预览输出目录不属于当前项目。')
            incoming = {p.relative_to(source) for p in source.rglob('*') if p.is_file() and p.suffix != '.rpyc' and 'cache' not in p.parts}
            for old in target.rglob('*.rpy'):
                if old.name != 'creator_bridge.rpy' and old.relative_to(target) not in incoming:
                    old.unlink()
                    old.with_suffix('.rpyc').unlink(missing_ok=True)
            for relative in incoming:
                out = target / relative
                out.parent.mkdir(parents=True, exist_ok=True)
                # Ren'Py keeps fonts/media open on Windows. Unchanged resources
                # do not need replacing, and must not make a text reload fail.
                if out.exists() and out.read_bytes() == (source / relative).read_bytes():
                    continue
                try:
                    shutil.copy2(source / relative, out)
                except OSError as error:
                    if getattr(error, 'winerror', None) not in (5, 32):
                        raise
                    self.event('restarting', {'message': '运行中的素材被占用，从当前场景测试入口重启'})
                    return self.start(Path(s['root']), entry=entry, mode=s['mode'], task_id=s['taskId'])
            s['revision'] = build['revision']
            s['entry'] = entry
            self.event('reloading', {'message': '从当前场景测试入口重新载入'})
            return self.command('reload', {})

    def poll(self, sid, after):
        with self.lock:
            if not self.session or sid != self.session['id']:
                raise ValueError('预览会话已关闭。')
            self.session['lastHeartbeat'] = time.time()
            return {'commands': [c for c in self.session['commands'] if c['id'] > after]}

    def receive(self, sid, kind, payload):
        with self.lock:
            s = self.session
            if not s or sid != s['id']:
                raise ValueError('预览会话已关闭。')
            if kind == 'ready':
                s['status'] = 'running'
            if kind in ('node', 'line', 'state', 'snapshot', 'ready', 'visual', 'audio'):
                s['runtime'].update(payload)
                if kind in ('snapshot','ready') and s['status']!='error':s['error']=None
            if kind == 'error':
                s['error'] = payload.get('message', '预览更新失败。')
            if kind == 'edit':
                if s['mode'] != 'edit':
                    raise ValueError('试玩模式不允许写回设计。')
                try:
                    result = self.on_edit(s, payload)
                except ValueError as error:
                    s['error'] = str(error)
                    return self.event('error', {'message': str(error), 'command': 'edit'})
                s['revision'] = result['project']['revision']
                s['error'] = None
                self.event('project_changed', result)
                self.command('ack', {})
            return self.event(kind, payload)

    def stop(self):
        with self.lock:
            if self.session and self.session['process'].poll() is None:
                self.session['process'].terminate()
                try:
                    self.session['process'].wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.session['process'].kill()
                self.session['status'] = 'stopped'
                self.event('stopped')
            return self.status()
