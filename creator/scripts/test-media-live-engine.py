"""Replay only registered real acceptance outputs; never imports a provider or AI client."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.compiler import sdk_path
from backend.preview import Engine
from backend.project import atomic_json
from backend.renpy_import import open_native


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--record',required=True)
    parser.add_argument('--tag',default='original',choices=['original','reopened'])
    args=parser.parse_args()
    record=Path(args.record).resolve()
    if not record.is_relative_to(ROOT/'.checks/media-fragment-live'):
        raise ValueError('Only this project acceptance record is allowed.')
    data=json.loads(record.read_text('utf-8'));fragment=data['fragment'];project=Path(fragment['projectRoot']).resolve()
    if data.get('fixture') is not False or project!=ROOT/'.test-projects/media-fragment/live-rain-campus' or fragment['status']!='bound':
        raise ValueError('Expected a bound real acceptance fragment.')
    hashes={}
    for job in data['jobs']:
        relative=job['import']['path'];file=(project/relative).resolve()
        if not file.is_relative_to(project) or 'creator_generated' not in file.parts:raise ValueError('Unexpected media file.')
        hashes[relative]=hashlib.sha256(file.read_bytes()).hexdigest()
        assert hashes[relative]==job['artifact']['sha256']
    _,document=open_native(project)
    scene=next(s for s in document['scenes'] if s['id']==fragment['sceneId'])
    voices=[l for l in scene['lines'] if (l.get('voice') or {}).get('generation')]
    assert len(voices)==1 and not voices[0]['voice']['generation']['stale']
    plan=data['plan'];options=plan['choice']['options'];end=plan['ending'][-1]['text'];q=lambda s:json.dumps(s,ensure_ascii=False)
    cases=[]
    for i,option in enumerate(options):
        response=option['lines'][-1]['text']
        voice=f'''        advance until {q(voices[0]['text'])}
        pause 0.05
        assert eval (renpy.music.get_playing(channel="voice") is not None) timeout 0.3
        screenshot "media_live_voice.png"
''' if i==0 else ''
        cases.append(f'''    testcase route_{i+1}:
{voice}        advance until screen "choice"
        screenshot "media_live_choice_{i+1}.png"
        click {q(option['text'])}
        advance until {q(response)}
        screenshot "media_live_route_{i+1}.png"
        advance until {q(end)}
        advance until screen "main_menu"
''')
    target=project/'game/creator_media_live_tests.rpy'
    prefix='# Local acceptance tests only; not generated story.\n'
    if target.exists() and not target.read_text('utf-8').startswith(prefix):raise ValueError('Independent test file already exists.')
    target.write_text(prefix+f'''testsuite media_fragment_live:
    teardown:
        exit
    before testcase:
        run Start({q(fragment['label'])})
'''+''.join(cases),encoding='utf-8')
    engine=Engine(sdk_path());engine.check_native(project,lint=True)
    output=record.parent/('engine-'+args.tag)
    log=engine.run(project,'test',('media_fragment_live','--report-detailed','--overwrite-screenshots'),timeout=120,log_dir=output)
    passed=bool(re.search(r'\[rpytest\] Status:\s+PASSED',log))
    atomic_json(output/'report.json',{'mode':'real-media-offline','passed':passed,'project':str(project),'label':fragment['label'],'routes':[o['text'] for o in options],'voiceText':voices[0]['text'],'hashes':hashes,'realApiRequestsDuringReplay':0,'log':log})
    print(log)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
