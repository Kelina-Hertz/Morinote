"""Exercise local service -> native bridge -> engine -> validated source reload."""
from pathlib import Path
import json,sys,threading,time
from unittest.mock import patch
CREATOR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CREATOR))
from backend.server import Service,create_server
from backend.compiler import sdk_path
from backend.workspace import read_document
from backend.project import atomic_json

fixture=max((CREATOR/'.test-projects').glob('native-ide-*/project'),key=lambda p:p.parent.stat().st_mtime)
service=Service(sdk_path(),'local-native-integration')
service.select_project(fixture)
server=create_server(service,0)
threading.Thread(target=server.serve_forever,daemon=True).start()
report={'root':str(fixture),'checks':[]}
def wait_for(condition):
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        state=service.preview.status()
        if condition(state):return state
        time.sleep(.1)
    raise AssertionError('Native preview timed out: '+json.dumps(state,ensure_ascii=False,default=str))
def request(route,body):return service.dispatch(route,{**body,'projectSession':service.project_session})
original=read_document(fixture,'game/script.rpy')
try:
    with patch('backend.preview.interactive_desktop',return_value=True):
        service.preview.start(fixture,{'nativeLabel':'C1b2','clean':False},mode='edit')
        state=wait_for(lambda s:s['status']=='running' and bool(s['runtime'].get('objects')))
        report['checks'].append('authenticated native observation and edit entry')
        session=service.preview.session
        old_pid=session['process'].pid
        service.preview.command('native',{'command':{'operation':'property','tag':'hero','property':'xpos','value':500,'base':400}})
        state=wait_for(lambda s:any(abs(b.get('x',0)-500)<1 for b in s['runtime'].get('objects',[])))
        report['checks'].append('parameter command executed on native main thread')
        revision=service.response()['project']['revision']
        invalid=request('/api/workspace/save',{'revision':revision,'edits':[{**original,'content':original['content']+'\nlabel broken\n'}]})
        assert invalid['project']['sourceStatus']['valid'] is False
        assert service.preview.session['process'].pid==old_pid and service.preview.session['process'].poll() is None
        assert service.preview.status()['revision']<invalid['project']['revision']
        report['checks'].append('invalid code saved while last working window remains alive')
        damaged=read_document(fixture,'game/script.rpy')
        valid=request('/api/workspace/save',{'revision':invalid['project']['revision'],'edits':[{**damaged,'content':original['content'].replace('e "Ready"','e "Updated ready"')}]})
        assert valid['project']['sourceStatus']['valid']
        state=wait_for(lambda s:s['status']=='running' and s['revision']==valid['project']['revision'] and bool(s['runtime'].get('source')))
        assert service.preview.session['process'].pid!=old_pid
        report['checks'].append('validated save automatically rebuilds and restarts configured native entry')
        report['ok']=True
except Exception as exc:report.update(ok=False,error=str(exc))
finally:
    service.preview.stop();server.shutdown();server.server_close()
    # This is a disposable fixture, but keep it reusable for the engine suite.
    (fixture/'game/script.rpy').write_bytes(original['content'].encode('utf-8'))
    from backend.renpy_import import open_native
    open_native(fixture)
atomic_json(CREATOR/'.cache/native-live-checks.json',report)
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
