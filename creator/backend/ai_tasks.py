"""AI snapshots and tools. No method here applies AI edits to the real project."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
import uuid

from .ai_files import source_files, copy_sources, safe_path, review_hash
from .project import load_project, atomic_json, project_file
from . import workspace

TOOL_NAMES = ('catalog','project', 'files', 'read', 'write', 'delete', 'workspace', 'operate',
              'assets', 'analyze', 'validate', 'lint', 'test', 'preview',
              'preview_status', 'screenshot', 'stop_preview', 'read_image')
TEXT = workspace.TEXT - {'.svg'}
MEDIA = {'.png','.jpg','.jpeg','.webp','.avif','.gif','.svg','.ogg','.wav','.mp3','.opus','.flac','.rpa','.rpyc'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def editor_identity(state):
    return fingerprint({'documents': sorted([
        {'path': d['base']['path'], 'hash': d['base']['hash'], 'exists': d['base'].get('exists',True),
         'value': d['value'], 'deleted': bool(d.get('deleted'))}
        for d in state.get('documents',[]) if d.get('deleted') or not d['base'].get('exists',True) or d['value']!=d['base']['content']],key=lambda d:d['path']), 'metadata':state.get('metadata')})


class PendingProcess:
    """A preview whose process is owned by the confined DSH runtime."""
    def __init__(self, identity):
        self.id=identity; self.pid=0; self.code=None; self.stop_requested=False
    def poll(self): return self.code
    def terminate(self): self.stop_requested=True;self.code=130
    def kill(self): self.terminate()
    def wait(self, timeout=None): return self.code or 0


class AITasks:
    def __init__(self, root, engine):
        self.root=Path(root).resolve(); self.engine=engine
        self.base=self.root/'.creator/ai/tasks';self.lock=threading.RLock()
        self.previews={};self.executions={}

    def directory(self, tid):
        if not isinstance(tid,str) or not re.fullmatch(r'[a-f0-9]{32}',tid):raise ValueError('无效 AI 任务编号。')
        directory=self.base/tid
        if not (directory/'task.json').is_file():raise ValueError('当前项目没有此 AI 任务。')
        return directory

    def meta(self,tid):return json.loads((self.directory(tid)/'task.json').read_text('utf-8'))
    def store(self,meta):atomic_json(self.directory(meta['id'])/'task.json',meta)
    def public(self,meta):
        return {**{k:meta.get(k) for k in ('id','prompt','created','status','baseRevision','editorDigest','sessionId','provider','model','usage','error','parentTaskId')},'conversationId':meta.get('conversationId') or meta['id'],**({'hasChanges':meta['hasChanges']} if 'hasChanges' in meta else {})}
    def list(self):
        result=[]
        for path in self.base.glob('*/task.json') if self.base.exists() else []:
            try:result.append(self.public(json.loads(path.read_text('utf-8'))))
            except (OSError,ValueError):continue
        return sorted(result,key=lambda m:m['created'],reverse=True)

    def new(self,prompt,state,context):
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>100000:raise ValueError('请输入制作要求。')
        from .renpy_import import open_native, reindex_project
        document=load_project(self.root)
        if not document.get('nativeRenpy',{}).get('inPlace'):raise ValueError('首版 DSH 工具需要原 Ren’Py 工程。')
        baseline=source_files(self.root)
        documents=state.get('documents',[])
        if not isinstance(documents,list) or len(documents)>200:raise ValueError('编辑稿数量无效。')
        for item in documents:
            base=item['base'];current=workspace.read_document(self.root,base['path'])
            if current['hash']!=base['hash'] or current['exists']!=base.get('exists',True):
                raise ValueError('编辑稿与磁盘存在冲突，请先处理：'+base['path'])
            if not isinstance(item['value'],str) or len(item['value'].encode())>4*1024*1024:raise ValueError('编辑内容过大。')
        tid=uuid.uuid4().hex;directory=self.base/tid;directory.mkdir(parents=True)
        target=directory/'project';copy_sources(self.root,target)
        if baseline!=source_files(self.root):raise ValueError('建立副本时工程发生变化，请重试。')
        for item in documents:
            base=item['base'];path=workspace.source_path(target,base['path'])
            if item.get('deleted'):path.unlink(missing_ok=True);continue
            text=item['value'].replace('\r\n','\n').replace('\r','\n').replace('\n',base.get('newline','\n'))
            workspace.atomic_bytes(path,(b'\xef\xbb\xbf' if base.get('bom') else b'')+text.encode('utf-8'))
        candidate=load_project(target)
        metadata=state.get('metadata')
        if metadata:
            workspace.validate_metadata({**candidate.get('ide',{}),**metadata['ide']})
            candidate['ide']={**candidate.get('ide',{}),**metadata['ide']}
            if metadata.get('assets') is not None:candidate['assets']=metadata['assets']
        atomic_json(project_file(target),candidate)
        # Invalid handwritten code is retained in a snapshot; AI can repair it.
        try:
            candidate=reindex_project(target,candidate)
            atomic_json(project_file(target),candidate)
        except (ValueError,KeyError,TypeError,SyntaxError):pass
        meta={'id':tid,'prompt':prompt,'created':time.time(),'status':'draft','baseRevision':document['revision'],
              'baselineDisk':baseline,'baselineSnapshot':source_files(target),'editorDigest':editor_identity(state),
              'context':context,'ledger':{},'assets':copy.deepcopy(document.get('assets',[])),
              'review':copy.deepcopy(candidate.get('review')),'requirements':copy.deepcopy(candidate.get('nativeAssetLibrary',{}).get('entries',[])),'baseIde':copy.deepcopy(candidate.get('ide',{}))}
        atomic_json(directory/'editor.json',state);atomic_json(directory/'task.json',meta)
        # Keep the captured editable bytes for three-way review, separate from working files.
        originals={}
        for relative in meta['baselineSnapshot']:
            path=safe_path(target,relative)
            if self.text_path(relative):originals[relative]=path.read_text('utf-8-sig')
        atomic_json(directory/'original-text.json',originals)
        return {**self.public(meta),'root':str(target)}

    def text_path(self,relative):
        rel=Path(relative)
        return relative.startswith('game/') and rel.suffix.lower() in TEXT and not ({p.casefold() for p in rel.parts}&{'.creator','.git','cache','saves','__pycache__','node_modules'})

    def write_path(self,target,relative):
        if not isinstance(relative,str) or not self.text_path(relative):raise ValueError('AI 只能修改副本中的 game 文本源码。')
        path=workspace.source_path(target,relative)
        if path.is_symlink():raise ValueError('AI 不能通过链接写入。')
        return path

    def reindex(self,target):
        from .renpy_import import reindex_project
        candidate=reindex_project(target,load_project(target));candidate['revision']+=1
        atomic_json(project_file(target),candidate)
        return candidate

    def guard(self,meta):
        target=self.directory(meta['id'])/'project';current=source_files(target)
        base=meta['baselineSnapshot']
        for relative in set(base)|set(current):
            if relative in ('.creator/editor/project.json','.creator/editor/renpy-index.json'):continue
            if current.get(relative)!=base.get(relative) and not self.text_path(relative):
                raise ValueError('任务修改了只读素材或不允许应用的文件：'+relative)
        project=load_project(target)
        if project.get('review')!=meta.get('review'):raise ValueError('AI 不能伪造或更改正文确认记录。')
        original={a['id']:a for a in meta.get('assets',[]) if not a.get('virtual')}
        for asset in project.get('assets',[]):
            old=original.get(asset['id'])
            if old and any(old.get(k)!=asset.get(k) for k in ('path','nativeGamePath')):raise ValueError('AI 不能更换实际素材路径。')
        current_entries={e['id']:e for e in project.get('nativeAssetLibrary',{}).get('entries',[])}
        for old in meta.get('requirements',[]):
            entry=current_entries.get(old['id'])
            if old.get('status') in ('unbound','broken','temporary'):
                if entry and entry.get('status')=='bound':raise ValueError('缺失素材只能提出临时替代，不能由 AI 标记为已经补齐：'+old['name'])
                if entry and old.get('requirement') and not entry.get('requirement'):raise ValueError('不能清除原有素材需求。')
        return current,project

    def diff(self,tid,state=None):
        meta=self.meta(tid);current,project=self.guard(meta)
        originals=json.loads((self.directory(tid)/'original-text.json').read_text('utf-8'))
        files=[];target=self.directory(tid)/'project'
        for relative in sorted(set(current)|set(meta['baselineSnapshot'])):
            if not self.text_path(relative) or current.get(relative)==meta['baselineSnapshot'].get(relative):continue
            path=self.write_path(target,relative)
            files.append({'path':relative,'before':originals.get(relative),'after':path.read_text('utf-8-sig') if path.is_file() else None,
                          'status':'deleted' if relative not in current else 'added' if relative not in meta['baselineSnapshot'] else 'modified'})
        disk_changed=source_files(self.root)!=meta['baselineDisk']
        editor_changed=state is not None and editor_identity(state)!=meta['editorDigest']
        ide=project.get('ide',{})
        return {'id':tid,'files':files,'reviewHash':review_hash(current),'baseRevision':meta['baseRevision'],
                'conflict':disk_changed or editor_changed,'diskChanged':disk_changed,'editorChanged':editor_changed,
                'metadata':{'before':meta.get('baseIde',{}),'after':ide} if ide!=meta.get('baseIde',{}) else None,
                'status':meta['status']}

    def prepare_apply(self,tid,reviewed,state):
        meta=self.meta(tid)
        if meta['status']=='applied':raise ValueError('此任务已经应用；请在编辑器中撤销，或建立新任务。')
        diff=self.diff(tid,state)
        if diff['reviewHash']!=reviewed:raise ValueError('任务在审核后发生变化，请重新审核。')
        if diff['conflict']:raise ValueError('项目或编辑稿发生变化，请先合并并重新审核。')
        changes=[]
        for item in diff['files']:
            base=workspace.read_document(self.root,item['path'])
            changes.append({'base':base,'value':item['after'] or '', 'deleted':item['after'] is None,'origin':'code'})
        return {'id':tid,'reviewHash':reviewed,'editorDigest':meta['editorDigest'],'documents':changes,'metadata':diff['metadata']}

    def mark(self,tid,values):
        meta=self.meta(tid)
        for key in ('status','sessionId','provider','model','usage','error','conversationId','parentTaskId','context','hasChanges'):
            if key in values:meta[key]=values[key]
        self.store(meta);return self.public(meta)

    def rebase(self,tid,state,resolutions=None):
        """Merge task edits against today's disk+buffers, then require a fresh review."""
        from .source_merge import merge
        meta=self.meta(tid);self.guard(meta);target=self.directory(tid)/'project'
        originals=json.loads((self.directory(tid)/'original-text.json').read_text('utf-8'))
        current_buffers={d['base']['path']:d for d in state.get('documents',[])}
        current_files=source_files(self.root);task_files=source_files(target);conflicts=[];merged={};new_originals={}
        for relative in sorted(set(originals)|set(current_files)|set(task_files)|set(current_buffers)):
            if not self.text_path(relative):continue
            disk=workspace.read_document(self.root,relative);buffer=current_buffers.get(relative)
            if buffer and (disk['hash']!=buffer['base']['hash'] or disk['exists']!=buffer['base'].get('exists',True)):
                raise ValueError('请先处理编辑稿与磁盘冲突：'+relative)
            theirs=None if buffer and buffer.get('deleted') else buffer['value'] if buffer else disk['content'] if disk['exists'] else None
            file=self.write_path(target,relative);ours=file.read_text('utf-8-sig') if file.is_file() else None
            base=originals.get(relative);new_originals[relative]=theirs
            if ours==base:value=theirs
            elif theirs==base or ours==theirs:value=ours
            elif isinstance(ours,str) and isinstance(theirs,str) and isinstance(base,str):
                parts=merge(base,ours,theirs)['parts']
                if any(p['conflict'] for p in parts):
                    if resolutions is None or relative not in resolutions:
                        conflicts.append({'path':relative,'base':base,'local':ours,'disk':theirs,'parts':parts});continue
                    value=resolutions[relative]
                else:value=''.join(p['text'] for p in parts)
            elif resolutions is None or relative not in resolutions:
                conflicts.append({'path':relative,'base':base,'local':ours,'disk':theirs,'parts':[]});continue
            else:value=resolutions[relative]
            if value is not None and (not isinstance(value,str) or len(value.encode())>4*1024*1024):raise ValueError('合并结果必须为文本或删除标记。')
            merged[relative]=value
        before_ide=meta.get('baseIde',{});ours_ide=load_project(target).get('ide',{})
        theirs_ide={**load_project(self.root).get('ide',{}),**(state.get('metadata') or {}).get('ide',{})}
        merged_ide=copy.deepcopy(theirs_ide)
        for key in set(before_ide)|set(ours_ide):
            before=before_ide.get(key);ours=ours_ide.get(key);theirs=theirs_ide.get(key)
            if ours==before:continue
            if theirs!=before and ours!=theirs:
                path='@configuration/'+key
                if resolutions is None or path not in resolutions:
                    conflicts.append({'path':path,'base':json.dumps(before,ensure_ascii=False,indent=2),'local':json.dumps(ours,ensure_ascii=False,indent=2),'disk':json.dumps(theirs,ensure_ascii=False,indent=2),'parts':[]});continue
                ours=json.loads(resolutions[path])
            merged_ide[key]=ours
        if conflicts:return {'conflicts':conflicts}
        workspace.validate_metadata(merged_ide)
        # Refresh immutable assets from the new project version, never silently keep outdated bytes.
        import shutil
        for relative in set(meta['baselineDisk'])|set(current_files):
            if self.text_path(relative) or relative.startswith('.creator/'):continue
            dest=safe_path(target,relative);source=safe_path(self.root,relative)
            if source.is_file():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
            else:dest.unlink(missing_ok=True)
        for relative,value in merged.items():
            path=self.write_path(target,relative)
            if value is None:path.unlink(missing_ok=True)
            else:
                disk=workspace.read_document(self.root,relative);base=current_buffers.get(relative,{}).get('base',disk)
                value=value.replace('\r\n','\n').replace('\r','\n').replace('\n',base.get('newline','\n'))
                workspace.atomic_bytes(path,(b'\xef\xbb\xbf' if base.get('bom') else b'')+value.encode('utf-8'))
        baseline={**current_files}
        for relative,value in new_originals.items():
            if value is None:baseline.pop(relative,None)
            else:
                disk=workspace.read_document(self.root,relative);base=current_buffers.get(relative,{}).get('base',disk)
                raw=value.replace('\r\n','\n').replace('\r','\n').replace('\n',base.get('newline','\n'))
                baseline[relative]=hashlib.sha256((b'\xef\xbb\xbf' if base.get('bom') else b'')+raw.encode()).hexdigest()
        meta.update(baselineDisk=current_files,baselineSnapshot=baseline,editorDigest=editor_identity(state),baseRevision=load_project(self.root)['revision'])
        atomic_json(self.directory(tid)/'original-text.json',{k:v for k,v in new_originals.items() if v is not None})
        meta['baseIde']=theirs_ide
        candidate=load_project(target);candidate['ide']=merged_ide;atomic_json(project_file(target),candidate)
        self.store(meta)
        try:self.reindex(target)
        except (ValueError,SyntaxError):pass
        return {'conflicts':[],'diff':self.diff(tid,state)}

    def tool(self,tid,name,args,call_id):
        if name not in TOOL_NAMES or not isinstance(args,dict):raise ValueError('未知 IDE 工具或无效参数。')
        if not isinstance(call_id,str) or not 1<=len(call_id)<=250:raise ValueError('工具缺少稳定调用编号。')
        meta=self.meta(tid);target=self.directory(tid)/'project'
        if meta['status'] not in ('draft','running','waiting_user','awaiting_review','failed','cancelled'):raise ValueError('任务已经应用。')
        signature=fingerprint([name,args]);previous=meta['ledger'].get(call_id)
        if previous:
            if previous['signature']!=signature:raise ValueError('不能使用同一调用编号执行不同操作。')
            if previous.get('state')=='pending':raise ValueError('前次写入结果待核实，请读取副本核对；不会自动重放。')
            result=previous.get('result')
            if result is None:result=json.loads((self.directory(tid)/'calls'/str(previous['resultRef'])).read_text('utf-8'))
            if result.get('execution'):
                return {'status':'not_replayed','executionId':result['execution']['id'],'contentHash':result['execution']['contentHash'],'reason':'该执行请求已登记，结果待核实；恢复或重试不会自动重放。'}
            if result.get('contentHash'):result['stale']=result['contentHash']!=review_hash(source_files(target))
            return result
        if name in ('lint','test','preview'):
            return self.prepare_execution(tid,name,args,call_id,signature)
        if name in ('write','delete','operate'):
            meta['ledger'][call_id]={'signature':signature,'state':'pending'};self.store(meta)
        project=load_project(target)
        if name=='catalog':
            from .ai_tools import catalog
            result=catalog()
        elif name=='project':result={'project':project,'context':meta['context']}
        elif name=='files':result={'files':sorted(source_files(target))}
        elif name=='read':result=workspace.read_document(target,args['path'])
        elif name in ('write','delete'):
            path=self.write_path(target,args['path'])
            if name=='delete':
                if workspace.read_document(target,args['path'])['hash']!=args.get('hash'):raise ValueError('删除前源码已变化，请重新读取。')
                path.unlink(missing_ok=True)
            else:
                value=args.get('content')
                if not isinstance(value,str) or len(value.encode())>4*1024*1024:raise ValueError('源码内容过大。')
                old=workspace.read_document(target,args['path'])
                if args.get('hash') is not None and args['hash']!=old['hash']:raise ValueError('副本文件已变化，请重新读取。')
                value=value.replace('\r\n','\n').replace('\r','\n').replace('\n',old['newline'])
                workspace.atomic_bytes(path,(b'\xef\xbb\xbf' if old['bom'] else b'')+value.encode())
            try:self.reindex(target);diagnostics=[]
            except (ValueError,SyntaxError,KeyError) as exc:diagnostics=[{'severity':'error','message':str(exc)}]
            result={'path':args['path'],'written':True,'diagnostics':diagnostics}
        elif name=='workspace':
            from .native_config import catalog
            from .native_flow import graph
            result={'config':catalog(target,project),'flow':graph(target,project),'project':project}
        elif name=='operate':
            from . import native_config,native_flow,native_stage,native_assets
            adapter={'config':native_config,'flow':native_flow,'stage':native_stage,'assets':native_assets}.get(args.get('adapter'))
            if not adapter:raise ValueError('未知 IDE 编辑工具。')
            operation={**args.get('operation',{})}
            if args['adapter']=='assets' and operation.get('operation')=='bind':operation['temporary']=True
            if operation.get('nodeId'):
                line=next((l for scene in project['scenes'] for l in scene['lines'] if l['id']==operation['nodeId']),None)
                if not line:raise ValueError('文字节点不存在。')
                operation['path']='game/'+line['source']['file']
            if args['adapter']=='config' and operation.get('binding'):
                from .native_config import catalog
                binding=catalog(target,project).get('bindings',{}).get(operation['binding'])
                if binding:operation['hash']=binding.get('hash')
            if args['adapter']=='flow' and operation.get('node'):
                from .native_flow import graph
                node=next((n for n in graph(target,project)['nodes'] if n['id']==operation['node']),None)
                if node:operation['path']=node['source']['path']
            path=operation.get('path')
            if path:operation['hash']=workspace.read_document(target,path)['hash']
            result=adapter.edit(target,project,operation)
            edits=result.get('edits',[result])
            if 'clipboard' in result:result=result
            else:
                for item in edits:
                    self.write_path(target,item['path'])
                committed=workspace.commit(target,edits,project['revision'],strict=False)
                result={'revision':committed['project']['revision'],'diagnostics':committed.get('diagnostics',[]),'files':[e['path'] for e in edits]}
        elif name=='assets':result={'library':project.get('nativeAssetLibrary'),'assets':project['assets']}
        elif name=='analyze':
            try:result={'project':self.reindex(target),'valid':True}
            except (ValueError,SyntaxError,KeyError) as exc:result={'valid':False,'error':str(exc)}
        elif name=='validate':
            from .project import validate_project
            result={'diagnostics':validate_project(project,target)}
        elif name=='preview_status':result=self.preview(tid).status(args.get('after',0))
        elif name=='stop_preview':result=self.preview(tid).stop()
        elif name=='screenshot':result=self.preview(tid).command('screenshot',{})
        elif name=='read_image':
            import base64
            relative=args['path']
            if relative=='@preview':
                session=self.preview(tid).session
                if not session:raise ValueError('没有副本试玩截图。')
                path=Path(session.get('launchLog',str(Path(session['output'])/'launch.log'))).parent/'screenshots/editor-preview.png'
            elif relative.startswith('.creator/native-preview/'):
                path=(target/relative).resolve();allowed=(target/'.creator/native-preview').resolve()
                if not path.is_relative_to(allowed) or path.is_symlink():raise ValueError('截图位置无效。')
            else:
                allowed={a.get('path') for a in project['assets']}|{'game/'+a['nativeGamePath'] for a in project['assets'] if a.get('nativeGamePath')}
                if relative not in allowed:raise ValueError('只能读取已登记的任务图片。')
                path=safe_path(target,relative)
            if path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.gif'} or not path.is_file() or path.stat().st_size>10*1024*1024:raise ValueError('请选择副本中的图片，最大 10 MiB。')
            import mimetypes
            result={'image':{'data':base64.b64encode(path.read_bytes()).decode(),'mimeType':mimetypes.guess_type(path.name)[0] or 'image/png'},'path':relative}
        else:raise ValueError('此工具暂不可用。')
        self.record(tid,call_id,signature,result);return result

    def record(self,tid,call_id,signature,result):
        cached=copy.deepcopy(result)
        if cached.get('execution'):cached['execution']['env'].pop('CREATOR_BRIDGE_TOKEN',None)
        name=fingerprint(cached)+'.json';path=self.directory(tid)/'calls'/name
        if not path.is_file():atomic_json(path,cached)
        meta=self.meta(tid);meta['ledger'][call_id]={'signature':signature,'state':'complete','resultRef':name};self.store(meta)

    def preview(self,tid):
        if tid not in self.previews:
            from .preview import PreviewManager
            self.previews[tid]=PreviewManager(self.engine,'',secrets.token_hex(32),lambda *_: (_ for _ in ()).throw(ValueError('AI 试玩不写入正式工程。')),
                launcher=lambda argv,**kw:self.capture_preview(tid,argv,kw))
        return self.previews[tid]

    def execution_env(self,env):
        system={'SystemRoot','WINDIR','COMSPEC','PATHEXT','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','ProgramFiles','ProgramFiles(x86)','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','PYTHONIOENCODING','PYTHONUTF8','PYTHONDONTWRITEBYTECODE'}
        return {key:value for key,value in env.items() if key in system or key.startswith(('RENPY_','SDL_','CREATOR_PREVIEW_')) or key in {'CREATOR_BRIDGE_URL','CREATOR_BRIDGE_TOKEN','CREATOR_NATIVE_TEST','CREATOR_NATIVE_INDEX'}}

    def capture_preview(self,tid,argv,options):
        identity=uuid.uuid4().hex;process=PendingProcess(identity)
        self.executions[identity]={'taskId':tid,'process':process,'argv':argv,'cwd':str(options['cwd']),
            'env':self.execution_env(options['env']),'log':options['stdout'].name,'background':True,'timeoutMs':0}
        return process

    def prepare_execution(self,tid,name,args,call_id,signature):
        target=self.directory(tid)/'project';meta=self.meta(tid)
        if name=='preview':
            self.preview(tid).start(target,entry={**{k:v for k,v in args.get('entry',{}).items() if k in ('args','state','initialize')},'nativeLabel':args.get('label','start'),'scope':'fragment'},mode='play',task_id=tid)
            descriptor=next(v for v in reversed(list(self.executions.values())) if v['taskId']==tid)
            identity=descriptor['process'].id
        else:
            if name=='test':
                paths=sorted((target/'game').rglob('*.rpy'))
                if not any(re.search(r'^testsuite\s+',p.read_text('utf-8-sig'),re.M) for p in paths):
                    result={'status':'not_run','reason':'工程未声明 Ren’Py testsuite；没有将 lint 冒充为测试。','contentHash':review_hash(source_files(target))}
                    self.record(tid,call_id,signature,result);return result
            identity=uuid.uuid4().hex;logs=target/'.creator/ai-runs'/identity;logs.mkdir(parents=True)
            descriptor={'taskId':tid,'argv':self.engine.command+[str(target),'lint' if name=='lint' else 'test'],
                        'cwd':str(self.engine.sdk),'env':self.execution_env(self.engine.environment(logs)),'log':str(logs/'engine.log'),
                        'background':False,'timeoutMs':300000,'process':PendingProcess(identity)}
            self.executions[identity]=descriptor
        descriptor.update(contentHash=review_hash(source_files(target)),callId=call_id,signature=signature,name=name)
        result={k:v for k,v in descriptor.items() if k!='process'}
        value={'execution':{**result,'id':identity,'workspace':str(target)}}
        self.record(tid,call_id,signature,value);return value

    def finish_execution(self,tid,identity,code):
        meta=self.meta(tid)
        descriptor=self.executions.get(identity)
        if not descriptor or descriptor['taskId']!=tid:raise ValueError('此执行不属于当前任务。')
        descriptor['process'].code=code
        path=Path(descriptor['log']);log=path.read_text('utf-8',errors='replace')[-40000:] if path.is_file() else ''
        result={'exitCode':code,'log':log,'contentHash':descriptor['contentHash'],'status':'passed' if code==0 else 'failed',
                'stale':descriptor['contentHash']!=review_hash(source_files(self.directory(tid)/'project')),
                'originalChanged':source_files(self.root)!=meta['baselineDisk']}
        self.record(tid,descriptor['callId'],descriptor['signature'],result);return result

    def terminal(self,tid,payload):
        meta=self.meta(tid);key=payload['callId']
        if not isinstance(key,str) or not 1<=len(key)<=250:raise ValueError('终端调用编号无效。')
        signature=fingerprint([payload['command'],payload['purpose']]);ledger=meta.setdefault('terminal',{})
        previous=ledger.get(key)
        if previous and previous['signature']!=signature:raise ValueError('同一调用编号不能重试修改后的命令。')
        if payload['stage']=='begin':
            if previous:return {'accepted':False,'result':previous.get('result',{'status':'not_replayed','reason':'前次终端执行结果待核实，不会自动重放。'})}
            ledger[key]={'signature':signature,'status':'pending'};self.store(meta);return {'accepted':True}
        if payload['stage']=='finish' and previous:
            previous.update(status='complete',result=payload['result']);self.store(meta);return {'saved':True}
        raise ValueError('终端执行台账状态无效。')

    def bridge(self,tid,operation,payload):
        preview=self.preview(tid)
        if operation=='poll':return {**preview.poll(payload['session'],int(payload.get('after',0))),
            'stopExecutions':[key for key,value in self.executions.items() if value['taskId']==tid and value['process'].stop_requested]}
        if operation=='event':return preview.receive(payload['sessionId'],payload['type'],payload.get('payload',{}))
        raise ValueError('未知试玩事件。')

    def stop(self):
        for preview in self.previews.values():preview.stop()
        for descriptor in self.executions.values():descriptor['process'].terminate()
