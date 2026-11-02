"""Explicit visible-engine fixture replay. No provider imports or cloud access."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.server import Service,create_server
from backend.compiler import sdk_path
from backend.renpy_import import open_native
from backend.project import atomic_json,load_project


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    project=Path(args.project).resolve()
    if not project.is_relative_to(ROOT/'.test-projects/media-fragment'):
        raise ValueError('Replay only accepts the isolated media fixture projects.')
    _,document=open_native(project)
    output=ROOT/'.checks/media-replay'/uuid.uuid4().hex[:12];output.mkdir(parents=True)
    service=Service(sdk_path(),'fixture-replay-'+uuid.uuid4().hex);service.select_project(project)
    server=create_server(service,0);threading.Thread(target=server.serve_forever,daemon=True).start()
    report={'mode':'fixture-offline-replay','project':str(project),'label':args.label,'realApiRequests':0,'observations':[]}
    try:
        service.engine.check_native(project,lint=True);report['lint']='passed'
        service.preview.start(project,{'nativeLabel':args.label,'scope':'fragment'})
        print(json.dumps({'ready':True,'output':str(output),'project':str(project)},ensure_ascii=False),flush=True)
        for line in sys.stdin:
            command=json.loads(line);action=command.get('action');tag=command.get('tag',str(len(report['observations'])))
            if not isinstance(tag,str) or not tag.replace('_','').replace('-','').isalnum() or len(tag)>80:raise ValueError('Invalid observation name')
            if action=='stop':break
            if action=='replay':service.preview.command('fragment_replay',{});time.sleep(.5)
            if action=='screenshot':
                service.preview.command('screenshot',{})
                image=Path(service.preview.session['launchLog']).parent/'screenshots/editor-preview.png'
                deadline=time.monotonic()+8
                while not image.exists() and time.monotonic()<deadline:time.sleep(.05)
                if not image.exists():raise ValueError('Engine screenshot not received')
                time.sleep(.2);shutil.copy2(image,output/(tag+'.png'))
            if action=='roundtrip':
                service.preview.stop()
                from backend.workspace import commit,read_document
                from backend.native_stage import edit
                _,document=open_native(project)
                hashes=lambda:{p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('game/images/creator_generated','game/audio/creator_generated') for p in (project/folder).rglob('*') if p.is_file()}
                before=hashes();target=next(l for s in document['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
                path='game/'+target['source']['file'];change=edit(project,document,{'operation':'text','nodeId':target['id'],'value':'我今天忘记带伞了。','hash':read_document(project,path)['hash']})
                commit(project,[change],document['revision']);_,reopened=open_native(project)
                target=next(l for s in reopened['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
                assert target['text']=='我今天忘记带伞了。' and target['voice']['generation']['stale']
                assert before==hashes();service.engine.check_native(project,lint=True)
                report['saveReopen']={'passed':True,'voiceStale':True,'mediaUnchanged':True,'realApiRequests':0}
            status=service.preview.status();runtime=status.get('runtime',{});source=runtime.get('source',{})
            original=''
            if source.get('path') and source.get('line'):
                file=project/source['path'];rows=file.read_text('utf-8').splitlines() if file.is_file() else []
                if 0<int(source['line'])<=len(rows):original=rows[int(source['line'])-1]
            observation={'tag':tag,'status':status.get('status'),'source':source,'sourceText':original,'audio':runtime.get('audio'), 'fragmentDone':runtime.get('fragmentDone')}
            report['observations'].append(observation);atomic_json(output/'report.json',report)
            print(json.dumps(observation,ensure_ascii=False),flush=True)
    finally:
        service.preview.stop();server.shutdown();server.server_close();atomic_json(output/'report.json',report)


if __name__=='__main__':main()
