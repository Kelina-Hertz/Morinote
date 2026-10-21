"""Real Ren'Py proof for parallel audio, continuous gain and independent stop."""
from pathlib import Path
import json,math,struct,sys,time,wave
CREATOR=Path(__file__).resolve().parents[2];sys.path.insert(0,str(CREATOR))
from backend.renpy_import import open_native
from backend.workspace import read_document,commit
from backend.native_stage import edit
from backend.preview import Engine
from backend.compiler import sdk_path

root=CREATOR/'.test-projects'/('native-audio-'+str(time.time_ns()));game=root/'game';game.mkdir(parents=True)
for name,hz in [('one',220),('two',330),('rain',440)]:
    with wave.open(str(game/(name+'.wav')),'wb') as out:
        out.setparams((1,2,22050,0,'NONE','not compressed'))
        out.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(2*math.pi*hz*i/22050))) for i in range(22050*12)))
(game/'options.rpy').write_text('define config.screen_width = 800\ndefine config.screen_height = 600\n',encoding='utf-8')
(game/'script.rpy').write_text('''label main_menu:
    call screen main_menu
    return
label start:
    play music "one.wav" volume 0.6
    "PARALLEL"
    "GAIN"
    "STOP"
    "REPLACE"
    "END"
    stop music
    stop creator_bgm_2
    stop ambience
    return
screen main_menu():
    textbutton "Start" action Start()
screen say(who,what):
    window:
        text what id "what"
''',encoding='utf-8')
_,project=open_native(root)
def apply(text,channel,action,**params):
    global project
    line=next(l for s in project['scenes'] for l in s['lines'] if l['text']==text)
    doc=read_document(root,'game/script.rpy')
    candidate=edit(root,project,{'operation':'audio_layer','action':action,'channel':channel,'path':doc['path'],'hash':doc['hash'],'nodeId':line['id'],'line':line['source']['line'],**params})
    project=commit(root,candidate.get('edits',[candidate]),project['revision'])['project']
def asset(name):return next(a['id'] for a in project['assets'] if a.get('nativeGamePath')==name+'.wav')
apply('PARALLEL','creator_bgm_2','play',asset=asset('two'),volume=.4,fadein=0,fadeout=0)
apply('PARALLEL','ambience','play',asset=asset('rain'),volume=.2,fadein=0,fadeout=0)
apply('GAIN','creator_bgm_2','volume',volume=.1)
apply('STOP','creator_bgm_2','stop',fadeout=.1)
apply('REPLACE','creator_bgm_2','play',asset=asset('one'),volume=.7,fadein=.1,fadeout=.1)
engine=Engine(sdk_path());build=engine.build(root,preview=True,lint=True);output=Path(build['output'])
(output/'game/audio_tests.rpy').write_text('''testsuite native_audio:
    teardown:
        exit
testcase native_audio.layers:
    $ _test.timeout = 25
    advance until screen "main_menu"
    $ preferences.text_cps = 0
    $ preferences.set_mixer("music", .7)
    click "Start"
    pause until eval (_last_say_what == "PARALLEL")
    pause .4
    assert eval (renpy.music.get_playing() == "one.wav")
    assert eval (renpy.music.get_playing(channel="creator_bgm_2") == "two.wav")
    assert eval (renpy.music.get_playing(channel="ambience") == "rain.wav")
    assert eval (renpy.music.get_loop(channel="creator_bgm_2"))
    assert eval (abs(preferences.get_mixer("music")-.7)<.01)
    $ position_before = renpy.music.get_pos(channel="creator_bgm_2")
    click
    pause until eval (_last_say_what == "GAIN")
    pause .2
    assert eval (renpy.music.get_pos(channel="creator_bgm_2") > position_before)
    assert eval (abs(renpy.audio.audio.get_channel("creator_bgm_2").context.secondary_volume-.25)<.01)
    assert eval (renpy.music.is_playing(channel="music") and renpy.music.is_playing(channel="ambience"))
    $ renpy.save("layers")
    click
    pause until eval (_last_say_what == "STOP")
    pause .3
    assert eval (not renpy.music.is_playing(channel="creator_bgm_2"))
    assert eval (renpy.music.is_playing(channel="music") and renpy.music.is_playing(channel="ambience"))
    run Function(renpy.load,"layers")
    pause until eval (_last_say_what == "GAIN")
    pause .3
    assert eval (renpy.music.get_playing(channel="creator_bgm_2") == "two.wav")
    assert eval (abs(renpy.audio.audio.get_channel("creator_bgm_2").context.secondary_volume-.25)<.01)
    click
    pause until eval (_last_say_what == "STOP")
    pause .2
    run Rollback()
    pause until eval (_last_say_what == "GAIN")
    pause .2
    assert eval (renpy.music.get_playing(channel="creator_bgm_2") == "two.wav")
    click
    pause until eval (_last_say_what == "STOP")
    click
    pause until eval (_last_say_what == "REPLACE")
    pause .3
    assert eval (renpy.music.get_playing(channel="creator_bgm_2") == "one.wav")
    assert eval (abs(renpy.audio.audio.get_channel("creator_bgm_2").context.secondary_volume-1)<.01)
    assert eval (renpy.music.get_playing(channel="music") == "one.wav")
    assert eval (renpy.music.get_playing(channel="ambience") == "rain.wav")
    screenshot "native-audio-layers.png"
''',encoding='utf-8')
report={'output':str(output),'lint':build.get('log')}
try:report.update(test=engine.run(output,'test',['native_audio','--overwrite-screenshots'],timeout=85),ok=True)
except Exception as exc:report.update(ok=False,error=str(exc))
path=CREATOR/'.checks/native-audio-engine.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':report['ok'],'report':str(path),'error':report.get('error')},ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)
