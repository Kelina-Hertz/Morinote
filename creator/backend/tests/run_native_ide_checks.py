"""Exercise native editing against the actual pinned Ren'Py engine."""
from pathlib import Path
import json
import shutil
import struct
import sys
import time
import wave
import zlib

CREATOR=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CREATOR))
from backend.renpy_import import open_native
from backend.preview import Engine,PreviewManager
from backend.compiler import sdk_path
from backend.project import atomic_json

root=CREATOR/'.test-projects'/('native-ide-'+str(time.time_ns()))
game=root/'project/game';game.mkdir(parents=True)
image=game/'gui/characters/hero/neutral.png';image.parent.mkdir(parents=True)
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
image.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',80,160,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes([90,190,150,255])*80)*160))+chunk(b'IEND',b''))
with wave.open(str(game/'tone.wav'),'w') as audio:
    audio.setparams((1,2,22050,0,'NONE',''));audio.writeframes(b'\0\0'*(22050*8))
(game/'script.rpy').write_text('''define e = Character("E")
default score = 0
image black = "#000000"
image hero:
    "gui/characters/hero/neutral.png"
    zoom 0.5
image hero_smile:
    "gui/characters/hero/neutral.png"
    zoom 0.5
label start:
    jump C1b2
label C1b2:
    scene black
    show hero as hero:
        xpos 400
        ypos 500
        xanchor 0.5
        yanchor 1.0
    play music "tone.wav" loop volume 0.5
    e "Ready"
    show screen sample_phone
    e "Phone"
    hide screen sample_phone
    e "After phone"
    return
''',encoding='utf-8')
(game/'screens.rpy').write_text('''label main_menu:
    call screen main_menu
    return
screen main_menu():
    textbutton "Start" action Start()
screen say(who,what):
    window:
        vbox:
            if who:
                text who id "who"
            text what id "what"
screen sample_phone():
    frame:
        xpos 550
        ypos 100
        xysize (200,300)
        text "PHONE OVERLAY"
''',encoding='utf-8')
(game/'options.rpy').write_text('define config.name = "Native IDE checks"\ndefine config.screen_width = 800\ndefine config.screen_height = 600\n',encoding='utf-8')
shutil.copy2(CREATOR/'backend/native_auto.rpy',game/'authored_auto.rpy')
with (game/'script.rpy').open('a',encoding='utf-8') as stream:stream.write('''
label auto_test:
    $ creator_native_auto_prepare("auto_a", .4)
    e "Auto first" (afm=False)
    $ creator_native_auto_prepare("auto_b", .6)
    e "Auto second" (afm=False)
    e "Auto tail"
    return
label auto_menu_pause:
    $ renpy.pause(.7)
    return
''')
_,project=open_native(root/'project')
engine=Engine(sdk_path());build=engine.build(root/'project',preview=True,lint=True)
output=Path(build['output']);shutil.copy2(CREATOR/'backend/creator_native_preview.rpy',output/'game/creator_native_preview.rpy')
PreviewManager(engine,'','',None).native_index(root/'project',output)
(output/'game/native_ide_tests.rpy').write_text('''testsuite native_ide:
    teardown:
        exit

testcase native_ide.properties:
    $ _test.timeout = 25
    advance until screen "main_menu"
    $ preferences.text_cps = 0
    click "Start"
    pause until eval (_last_say_what == "Ready")
    assert eval (_cn_client.source["path"].endswith("script.rpy"))
    assert eval ("hero" in _cn_client.objects)
    $ before_box = renpy.get_image_bounds("hero")
    $ before_position = renpy.music.get_pos("music")
    $ _cn_client.mode = "edit"
    $ _cn_apply({"operation":"property","tag":"hero","property":"xpos","value":500,"base":400})
    pause .2
    assert eval (abs(renpy.get_image_bounds("hero")[0] - before_box[0] - 100) < 2)
    $ _cn_apply({"operation":"property","tag":"hero","property":"zoom","value":1.0,"base":0.5})
    pause .2
    assert eval (abs(renpy.get_image_bounds("hero")[2] - before_box[2]*2) < 2)
    $ _cn_apply({"operation":"volume","channel":"music","value":0.8,"base":0.5})
    assert eval (renpy.music.get_playing("music").endswith("tone.wav"))
    assert eval (renpy.music.get_pos("music") is None or before_position is None or renpy.music.get_pos("music") >= before_position)
    assert eval (abs(renpy.audio.audio.get_channel("music").chan_volume - 1.6) < .01)
    $ swap_bounds = renpy.get_image_bounds("hero")
    $ _cn_apply({"operation":"image","tag":"hero","image":"hero_smile"})
    assert eval ("hero" in renpy.get_showing_tags() and "hero_smile" not in renpy.get_showing_tags())
    pause .2
    assert eval (abs(renpy.get_image_bounds("hero")[0] - swap_bounds[0]) < 2)
    assert eval (abs(renpy.get_image_bounds("hero")[2] - swap_bounds[2]) < 2)
    screenshot "native-ide-composition.png"
    $ _cn_apply({"operation":"reset"})
    pause .2
    assert eval (abs(renpy.get_image_bounds("hero")[0]-before_box[0])<2)
    assert eval (abs(renpy.get_image_bounds("hero")[2]-before_box[2])<2)
    assert eval (abs(renpy.audio.audio.get_channel("music").chan_volume-1.0)<.01)
    $ _cn_client.mode = "play"
    click
    pause until eval (_last_say_what == "Phone")
    assert screen "sample_phone"
    $ _cn_client.label = "called_phone"
    $ _cn_apply({"operation":"property","label":"C1b2","source":_cn_client.objects["hero"]["nativeSource"],"tag":"hero","property":"xpos","value":450,"base":400})
    assert screen "sample_phone"
    $ _cn_client.label = "C1b2"
    $ _cn_apply({"operation":"property","tag":"hero","property":"xpos","value":450,"base":400})
    assert screen "sample_phone"
    screenshot "native-ide-phone.png"
    click
    pause until eval (_last_say_what == "After phone")
    assert not screen "sample_phone"

testcase native_ide.save_rollback:
    $ _test.timeout = 25
    advance until screen "main_menu"
    $ preferences.text_cps = 0
    click "Start"
    pause until eval (_last_say_what == "Ready")
    $ renpy.save("native-ide")
    click
    pause until eval (_last_say_what == "Phone")
    run Function(renpy.load,"native-ide")
    pause until eval (_last_say_what == "Ready")
    assert not screen "sample_phone"
    assert eval (renpy.showing("hero"))
    click
    pause until eval (_last_say_what == "Phone")
    run Rollback()
    pause until eval (_last_say_what == "Ready")
    assert not screen "sample_phone"

testcase native_ide.auto_wait:
    $ _test.timeout = 25
    advance until screen "main_menu"
    $ preferences.text_cps = 8
    $ preferences.afm_time = .01
    $ preferences.afm_enable = True
    run Start("auto_test")
    pause until eval (_last_say_what == "Auto first")
    pause .1
    assert eval (not creator_native_auto_ready)
    pause until eval (creator_native_auto_ready)
    pause .05
    assert eval (_last_say_what == "Auto first")
    pause until eval (_last_say_what == "Auto second")
    $ preferences.afm_enable = False
    $ preferences.text_cps = 0
    pause .9
    assert eval (_last_say_what == "Auto second")
    assert eval (preferences.afm_time == .01)
    $ preferences.afm_enable = True
    run Function(renpy.call_in_new_context,"auto_menu_pause")
    assert eval (_last_say_what == "Auto second")
    $ preferences.afm_enable = False
    pause until eval (creator_native_auto_ready)
    click
    pause until eval (_last_say_what == "Auto tail")
    assert eval (creator_native_auto_id is None)
''',encoding='utf-8')
report={'output':str(output),'checks':[]}
try:
    report['compile']=engine.run(output)
    report['lint']=engine.run(output,'lint')
    report['test']=engine.run(output,'test',['native_ide','--overwrite-screenshots'])
    report['ok']=True
except Exception as exc:report.update(ok=False,error=str(exc))
atomic_json(root/'report.json',report)
print(json.dumps({'ok':report['ok'],'report':str(root/'report.json'),'error':report.get('error'),'test':report.get('test')},ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
