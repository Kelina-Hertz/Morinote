"""Pinned-engine check: unbound visual/audio entries and label reuse remain playable."""
from pathlib import Path
import json,struct,sys,time,wave,zlib
CREATOR=Path(__file__).resolve().parents[2];sys.path.insert(0,str(CREATOR))
from backend.renpy_import import open_native
from backend.native_assets import edit
from backend.workspace import commit
from backend.preview import Engine
from backend.compiler import sdk_path

root=CREATOR/'.test-projects'/('virtual-assets-'+str(time.time_ns()));game=root/'game';game.mkdir(parents=True)
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
(game/'hero.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',80,160,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes([90,190,150,255])*80)*160))+chunk(b'IEND',b''))
with wave.open(str(game/'tone.wav'),'w') as sound:sound.setparams((1,2,22050,0,'NONE',''));sound.writeframes(b'\0\0'*22050)
(game/'script.rpy').write_text('''define e = Character("E")
image hero:
    "hero.png"
    zoom 0.5
image absent = "missing.png"
image borrowed = "missing2.png"
define audio.theme = "missing.ogg"
screen main_menu():
    textbutton "Start" action Start()
screen say(who, what):
    text what id "what"
label main_menu:
    call screen main_menu
    return
label start:
    show absent
    play music "missing.ogg"
    e "PLACEHOLDER"
    hide absent
    show borrowed
    play music audio.theme
    $ renpy.log("VIRTUAL AUDIO VALUE: " + repr(audio.theme))
    e "TEMPORARY"
    return
''',encoding='utf-8')
_,project=open_native(root)
def apply(operation):
    global project
    change=edit(root,project,operation);project=commit(root,[change],project['revision'])['project']
def entry(kind,key):return next(e for e in project['nativeAssetLibrary']['entries'] if e['runtime']=={'kind':kind,'key':key})
apply({'operation':'unbind','id':entry('image','absent')['id']})
apply({'operation':'bind','id':entry('image','borrowed')['id'],'binding':{'kind':'label','key':'hero'},'temporary':True})
apply({'operation':'unbind','id':entry('file','missing.ogg')['id']})
apply({'operation':'bind','id':entry('audio-variable','audio.theme')['id'],'binding':{'kind':'file','key':'tone.wav'}})
(game/'checks.rpy').write_text('''testsuite virtual_assets:
    before testcase:
        $ _test.timeout = 20
        advance until screen "main_menu"
    teardown:
        exit
testcase virtual_assets.placeholder_and_reuse:
    $ preferences.text_cps = 0
    click "Start"
    pause until eval (_last_say_what == "PLACEHOLDER")
    assert eval (renpy.showing("absent"))
    assert eval (renpy.music.get_playing() == "missing.ogg")
    assert eval (renpy.loadable("missing.ogg"))
    click
    pause until eval (_last_say_what == "TEMPORARY")
    assert eval (renpy.showing("borrowed"))
    assert eval (renpy.get_registered_image("borrowed") is renpy.get_registered_image("hero"))
    pause .2
    assert eval (renpy.music.get_playing().startswith("_creator_virtual/audio/"))
    assert eval (renpy.loadable(renpy.music.get_playing()))
''',encoding='utf-8')
engine=Engine(sdk_path());report={'output':str(root)}
try:
    report['compile']=engine.run(root);report['lint']=engine.run(root,'lint')
    report['test']=engine.run(root,'test',['virtual_assets','--overwrite-screenshots']);report['ok']=True
except Exception as error:report.update(ok=False,error=str(error))
output=CREATOR/'.checks/virtual-assets-engine.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':report['ok'],'report':str(output),'error':report.get('error')},ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)
