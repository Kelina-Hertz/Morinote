"""Pinned-engine regression: stop only after the selected scene and its calls."""
from pathlib import Path
import json,sys,time,threading
CREATOR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CREATOR))
from backend.server import Service,create_server
from backend.renpy_import import open_native
from backend.compiler import sdk_path
from backend.project import atomic_json

root=CREATOR/'.test-projects'/('native-fragment-'+str(time.time_ns()))
game=root/'game';game.mkdir(parents=True)
support=root/'support';support.mkdir()
(support/'creator_native_preview.rpy').write_bytes((CREATOR/'backend/creator_native_preview.rpy').read_bytes())
(game/'script.rpy').write_text('''screen main_menu():
    tag menu
    textbutton "Start" action Start()
screen say(who, what):
    text what id "what"
default hits = []
label start:
    $ hits.append("wrong_start")
    "Fixture ready"
    return
label bounded:
    $ hits.append("scene")
    call phone from _call_phone_in_bounded
    $ hits.append("after_phone")
    jump .local
label .local:
    $ hits.append("local")
    jump next_scene
label next_scene(required):
    $ hits.append("leaked")
    return
label phone:
    $ hits.append("phone")
    call nested
    return
label nested:
    $ hits.append("nested")
    return
label falling:
    $ hits.append("falling")
label next_falling:
    $ hits.append("leaked")
    return
label returning:
    $ hits.append("returning")
    return
label flowing:
    $ hits.append("flowing")
    jump flow_tail
label flow_tail:
    $ hits.append("tail")
    "Continuous mode tail"
    return
''',encoding='utf-8')
open_native(root)
service=Service(sdk_path(),'local-fragment-test')
service.select_project(root)
server=create_server(service,0)
threading.Thread(target=server.serve_forever,daemon=True).start()
report={'root':str(root),'checks':[]}
def wait_for(predicate):
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        state=service.preview.status()
        if state.get('status')=='error':raise AssertionError(state.get('error'))
        if predicate(state):return state
        time.sleep(.1)
    raise AssertionError('Timed out: '+json.dumps(state,ensure_ascii=False,default=str))
try:
    for label,expected in [('bounded',['scene','phone','nested','after_phone','local']),('falling',['falling']),('returning',['returning'])]:
        service.preview.start(root,{'nativeLabel':label,'scope':'fragment'})
        state=wait_for(lambda s:s.get('runtime',{}).get('fragmentDone') and s['runtime'].get('state',{}).get('hits')==expected)
        assert state['status']=='running'
        report['checks'].append(label+' completed without leaking into next scene')
        if label=='bounded':
            previous=sum(e['type']=='fragment_finished' for e in service.preview.events)
            service.preview.command('fragment_replay',{})
            state=wait_for(lambda s:sum(e['type']=='fragment_finished' for e in service.preview.events)>previous and s['runtime'].get('state',{}).get('hits')==expected)
            report['checks'].append('replay restarts defaults and preserves scene boundary')
            service.preview.command('screenshot',{})
            image=Path(service.preview.session['launchLog']).parent/'screenshots/editor-preview.png'
            wait_for(lambda s:image.exists())
            report['screenshot']=str(image)
    service.preview.start(root,{'nativeLabel':'flowing','scope':'continue'})
    state=wait_for(lambda s:s.get('runtime',{}).get('state',{}).get('hits')==['flowing','tail'])
    assert not state['runtime'].get('fragmentDone')
    report['checks'].append('continue scope follows original jump into next scene')
    report['ok']=True
except Exception as exc:report.update(ok=False,error=str(exc))
finally:
    service.preview.stop();server.shutdown();server.server_close()
atomic_json(CREATOR/'.checks/native-fragment-engine.json',report)
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
