"""Exercise generated ATL, timing, actor identity and save/rollback in Ren'Py."""
from pathlib import Path
import json,struct,sys,time,zlib
CREATOR=Path(__file__).resolve().parents[2];sys.path.insert(0,str(CREATOR))
from backend.renpy_import import open_native
from backend.workspace import read_document,commit
from backend.native_stage import edit
from backend.preview import Engine
from backend.compiler import sdk_path

root=CREATOR/'.test-projects'/('native-motion-'+str(time.time_ns()));game=root/'game';(game/'gui/characters/hero').mkdir(parents=True)
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
(game/'gui/characters/hero/a.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',100,200,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes([90,190,150,255])*100)*200))+chunk(b'IEND',b''))
(game/'options.rpy').write_text('define config.screen_width = 800\ndefine config.screen_height = 600\n',encoding='utf-8')
(game/'script.rpy').write_text('''define e = Character("E")
image black = "#000000"
image hero:
    "gui/characters/hero/a.png"
    zoom 0.4
label main_menu:
    call screen main_menu
    return
label start:
    scene black
    show hero as actor:
        xpos 200
        ypos 300
    show hero as friend:
        xpos 600
        ypos 300
    e "SETUP"
    e "MOVE"
    e "ENTER_L"
    e "ENTER_R"
    e "FADE"
    e "JUMP"
    e "SHAKE"
    e "WAIT"
    e "END"
    return
screen main_menu():
    textbutton "Start" action Start()
screen say(who,what):
    window:
        text what id "what"
''',encoding='utf-8')
_,project=open_native(root)
cases=[('MOVE','move',[200,300],[420,300],False),('ENTER_L','enter_left',[-100,300],[300,300],False),('ENTER_R','enter_right',[900,300],[450,300],False),('FADE','fadein',[450,300],[450,300],False),('JUMP','jump',[450,300],[450,300],False),('SHAKE','shake',[450,300],[450,300],False),('WAIT','move',[450,300],[500,300],True)]
for text,kind,start,end,wait in cases:
    line=next(l for s in project['scenes'] for l in s['lines'] if l['text']==text)
    document=read_document(root,'game/script.rpy')
    candidate=edit(root,project,{'operation':'motion','path':document['path'],'hash':document['hash'],'line':line['source']['line'],'nodeId':line['id'],'tag':'actor','motion':{'kind':kind,'start':start,'end':end,'duration':.6,'easing':'linear','repeat':1,'amplitude':60,'wait':wait}})
    project=commit(root,[candidate],project['revision'])['project']
engine=Engine(sdk_path());build=engine.build(root,preview=True,lint=True);output=Path(build['output'])
(output/'game/motion_tests.rpy').write_text('''testsuite native_motion:
    teardown:
        exit
testcase native_motion.presets:
    $ _test.timeout = 30
    advance until screen "main_menu"
    $ preferences.text_cps = 0
    click "Start"
    pause until eval (_last_say_what == "SETUP")
    click
    pause until eval (_last_say_what == "MOVE")
    pause .2
    assert eval (210 < renpy.get_image_bounds("actor")[0] < 410)
    pause .6
    assert eval (abs(renpy.get_image_bounds("actor")[0]-420)<2)
    assert eval (abs(renpy.get_image_bounds("actor")[2]-40)<2)
    assert eval (abs(renpy.get_image_bounds("friend")[0]-600)<2)
    click
    pause until eval (_last_say_what == "ENTER_L")
    pause .2
    assert eval (-95 < renpy.get_image_bounds("actor")[0] < 290)
    pause .6
    assert eval (abs(renpy.get_image_bounds("actor")[0]-300)<2)
    click
    pause until eval (_last_say_what == "ENTER_R")
    pause .2
    assert eval (460 < renpy.get_image_bounds("actor")[0] < 890)
    pause .6
    click
    pause until eval (_last_say_what == "FADE")
    pause .2
    assert eval (0.1 < renpy.display.scenelists.scene_lists().get_displayable_by_tag("master","actor").state.alpha < .9)
    pause .6
    click
    pause until eval (_last_say_what == "JUMP")
    pause .15
    assert eval (renpy.get_image_bounds("actor")[1] < 285)
    pause .6
    assert eval (abs(renpy.get_image_bounds("actor")[1]-300)<2)
    click
    pause until eval (_last_say_what == "SHAKE")
    pause .1
    assert eval (abs(renpy.get_image_bounds("actor")[0]-450)>5)
    pause .7
    assert eval (abs(renpy.get_image_bounds("actor")[0]-450)<2)
    $ started = renpy.get_game_runtime()
    click
    pause .1
    assert eval (_last_say_what == "SHAKE")
    pause until eval (_last_say_what == "WAIT")
    assert eval (renpy.get_game_runtime()-started >= .5)
    assert eval (abs(renpy.get_image_bounds("actor")[0]-500)<2)
    assert eval (set(renpy.get_showing_tags()) == {"black","actor","friend"})
    screenshot "native-motion-wait.png"
    $ renpy.save("motion")
    click
    pause until eval (_last_say_what == "END")
    run Function(renpy.load,"motion")
    pause until eval (_last_say_what == "WAIT")
    pause .1
    $ renpy.log("MOTION_LOAD_EARLY " + repr(renpy.get_image_bounds("actor")))
    pause .7
    $ renpy.log("MOTION_LOAD_LATE " + repr(renpy.get_image_bounds("actor")))
    assert eval (abs(renpy.get_image_bounds("actor")[0]-500)<2)
    click
    pause until eval (_last_say_what == "END")
    run Rollback()
    pause until eval (_last_say_what == "WAIT")
    assert eval (renpy.showing("actor") and renpy.showing("friend"))
''',encoding='utf-8')
report={'output':str(output),'lint':build.get('log')}
try:report.update(test=engine.run(output,'test',['native_motion','--overwrite-screenshots'],timeout=90),ok=True)
except Exception as exc:report.update(ok=False,error=str(exc))
path=CREATOR/'.checks/native-motion-engine.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':report['ok'],'report':str(path),'error':report.get('error')},ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)
