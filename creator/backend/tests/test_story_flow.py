import os
from pathlib import Path
import tempfile
import unittest
from backend.renpy_import import open_native
from backend.native_flow import graph


class StoryFlowTests(unittest.TestCase):
    def flow(self,script,helper='label helper:\n    "手机"\n    return\n'):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'game').mkdir()
            (root/'game/script.rpy').write_text(script,encoding='utf-8')
            (root/'game/message.rpy').write_text(helper,encoding='utf-8')
            _,project=open_native(root)
            return graph(root,project)

    def test_main_chain_compresses_jumps_without_reordering(self):
        flow=self.flow('label C1a:\n    "甲"\n    jump C1b1\nlabel C1b1:\n    "乙"\n    jump C1b2\nlabel C1b2:\n    return\n')
        story=flow['story'];by_id={n['id']:n for n in story['nodes']}
        self.assertFalse(any(n['type']=='jump' for n in story['nodes']))
        self.assertIn(('C1a','C1b1'),[(by_id[e['source']]['title'],by_id[e['target']]['title']) for e in story['edges']])
        self.assertIn(('C1b1','C1b2'),[(by_id[e['source']]['title'],by_id[e['target']]['title']) for e in story['edges']])

    def test_calls_stay_in_scene_and_resume_at_their_own_menu(self):
        flow=self.flow('label C1a:\n    call helper\n    "之后"\n    menu:\n        "A":\n            jump C1b\n        "B":\n            return\nlabel C1b:\n    call helper\n    return\n')
        story=flow['story'];nodes={n['id']:n for n in story['nodes']}
        scene=next(n for n in story['nodes'] if n['title']=='C1a')
        self.assertEqual(len(scene['calls']),1)
        target=next(nodes[e['target']] for e in story['edges'] if e['source']==scene['id'])
        self.assertEqual(target['type'],'choice')
        self.assertFalse(any(e['kind']=='return' for e in story['edges']))
        self.assertEqual(len([e for e in story['edges'] if e['kind']=='option']),2)
        self.assertTrue(any(n['type']=='call' for n in flow['nodes']))

    def test_dynamic_target_is_not_invented(self):
        story=self.flow('label C1a:\n    jump expression destination\n')['story']
        dynamic=next(n for n in story['nodes'] if n.get('unresolved'))
        self.assertEqual(dynamic['title'],'运行时确定')
        self.assertFalse(any(e['source']==dynamic['id'] for e in story['edges']))

    def test_nonreturning_call_does_not_invent_a_return_path(self):
        flow=self.flow('label C1a:\n    call helper\n    menu:\n        "Unreachable":\n            return\n',helper='label helper:\n    jump expression destination\n')
        story=flow['story'];call=next(n for n in story['nodes'] if n['type']=='call')
        # Runtime-dependent helpers stay explicit, rather than being silently
        # treated as a completed phone interaction.
        self.assertTrue(call['title'].startswith('call helper'))

    def test_conversation_is_embedded_and_system_labels_are_not_story_modules(self):
        flow=self.flow('label splashscreen:\n    return\nlabel start:\n    "序章"\n    jump C1a\nlabel C1a:\n    call helper\n    "继续"\n    return\n',helper='label helper:\n    "聊天"\n    return\n')
        for key in ('story','storyDetail'):
            view=flow[key]
            self.assertNotIn('splashscreen',[n['title'] for n in view['nodes']])
            self.assertNotIn('helper',[n['title'] for n in view['nodes'] if n['type']=='scene'])
            self.assertEqual({g['title'] for g in view['groups']},{'序章','第1章'})
            ids={n['id'] for n in view['nodes']}
            self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in view['edges']))
        first=next(n for n in flow['story']['nodes'] if n['title']=='C1a')
        self.assertEqual(len(first['calls']),1)
        self.assertIn(first['calls'][0]['target'],{n['id'] for n in flow['nodes']})
        self.assertTrue(any(n['title']=='splashscreen' for n in flow['nodes']))

    def test_direct_conversation_route_stays_in_story(self):
        flow=self.flow('label C1a:\n    "开始"\n    jump helper\n')
        story=flow['story'];nodes={n['id']:n for n in story['nodes']}
        self.assertIn('helper',[n['title'] for n in story['nodes']])
        self.assertIn(('C1a','helper'),[(nodes[e['source']]['title'],nodes[e['target']]['title']) for e in story['edges']])

    def test_full_morinote_keeps_story_and_ova_but_excludes_components_and_qa(self):
        source=Path(os.environ['CREATOR_TEST_GAME']) if os.environ.get('CREATOR_TEST_GAME') else next((p for p in (Path(__file__).resolve().parents[3]/'game',Path(__file__).resolve().parents[3]/'Morinote/game') if p.exists()),Path('missing-fixture'))
        if not source.exists():self.skipTest('Morinote fixture unavailable')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'game').mkdir()
            for file in source.rglob('*.rpy'):
                target=root/'game'/file.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(file.read_bytes())
            _,project=open_native(root);flow=graph(root,project)
            for view in (flow['story'],flow['storyDetail']):
                labels={n['title'] for n in view['nodes'] if n['type']=='scene'}
                self.assertTrue({'start','C1a','C1b1','C1b2','C1b3','C1c1','C1c2','C1c3','test_OVA'}<=labels)
                self.assertFalse({'splashscreen','contact_friend_request','contact_empty_chat','contact_system_demo','_ui_qa_scene'}&labels)
                self.assertEqual({g['title'] for g in view['groups']},{'序章','第一章 · 百团大会','番外'})
            self.assertGreater(len(flow['nodes']),len(flow['storyDetail']['nodes']))

    def test_chapter_layout_metadata_does_not_promote_system_code_to_story(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'game').mkdir()
            (root/'game/script.rpy').write_text('label start:\n    return\nlabel splashscreen:\n    return\n',encoding='utf-8')
            _,project=open_native(root);project['ide']={'flowGroups':{'splashscreen':'第1章'}}
            view=graph(root,project)['story'];self.assertNotIn('splashscreen',[n['title'] for n in view['nodes']])

    def test_morinote_chapter_one_matches_source_chain(self):
        source=Path(os.environ['CREATOR_TEST_GAME']) if os.environ.get('CREATOR_TEST_GAME') else next((p for p in (Path(__file__).resolve().parents[3]/'game',Path(__file__).resolve().parents[3]/'Morinote/game') if p.exists()),Path('missing-fixture'))
        if not source.exists():self.skipTest('Morinote fixture unavailable')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'game').mkdir()
            for name in ('script_c1a.rpy','script_c1b.rpy','script_c1c.rpy','message.rpy'):
                (root/'game'/name).write_bytes((source/name).read_bytes())
            _,project=open_native(root);story=graph(root,project)['story']
            nodes={n['id']:n for n in story['nodes']}
            pairs={(nodes[e['source']]['title'],nodes[e['target']]['title']) for e in story['edges']}
            chain=['C1a','C1b1','C1b2','C1b3','C1c1','C1c2','C1c3']
            for a,b in zip(chain,chain[1:]):self.assertIn((a,b),pairs)
            final=next(n for n in story['nodes'] if n['title']=='C1c3')
            self.assertEqual(len(final['calls']),4)
            self.assertEqual(next(nodes[e['target']]['type'] for e in story['edges'] if e['source']==final['id']),'choice')
