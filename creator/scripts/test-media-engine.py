"""Run real Ren'Py testcases against a saved fixture, without cloud requests."""
from pathlib import Path
import argparse
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.compiler import sdk_path
from backend.preview import Engine
from backend.project import atomic_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    project=Path(args.project).resolve()
    if not project.is_relative_to(ROOT/'.test-projects/media-fragment') or not re.fullmatch(r'creator_fragment_[a-z0-9_]+',args.label):raise ValueError('Only isolated media fixtures are supported.')
    from backend.renpy_import import open_native
    _,document=open_native(project)
    first=next(l for s in document['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')['text']
    text=f'''# Local fixture test specification; not generated story or production content.
testsuite media_fragment_fixture:
    teardown:
        exit
    before testcase:
        run Start({json.dumps(args.label)})
    testcase escort:
        advance until {json.dumps(first,ensure_ascii=False)}
        pause 0.05
        assert eval (renpy.music.get_playing(channel="voice") is not None) timeout 0.3
        screenshot "media_voice.png"
        advance until screen "choice"
        screenshot "media_choice.png"
        click "送她回家"
        advance until "谢谢，我们一起走吧。"
        screenshot "media_escort.png"
        advance until "雨声渐渐远去。"
        advance until screen "main_menu"
    testcase lend:
        advance until screen "choice"
        click "把伞借给她"
        advance until "明天我会把伞还给你。"
        screenshot "media_lend.png"
        advance until "雨声渐渐远去。"
        advance until screen "main_menu"
'''
    target=project/'game/creator_media_fixture_tests.rpy'
    if target.exists() and not target.read_text('utf-8').startswith('# Local fixture test specification;'):raise ValueError('Existing tests are not the managed local fixture.')
    target.write_text(text,encoding='utf-8')
    engine=Engine(sdk_path());log=engine.run(project,'test',('media_fragment_fixture','--report-detailed','--overwrite-screenshots'),timeout=120,log_dir=project/'.creator/media-engine-tests')
    report={'mode':'fixture-offline','project':str(project),'realApiRequests':0,'log':log,'passed':bool(re.search(r'\[rpytest\] Status:\s+PASSED',log))}
    atomic_json(project/'.creator/media-engine-tests/report.json',report)
    print(log)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
