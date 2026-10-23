import copy
from pathlib import Path
import tempfile
import unittest

from backend import native_flow, workspace
from backend.project import load_project
from backend.renpy_import import open_native
from backend.scene_metadata import display_hints


class SceneCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'game').mkdir()
        (self.root/'game/story.rpy').write_text('label start:\n    "开始"\n    jump route_a\nlabel route_a:\n    "接受"\n    return\nlabel route_b:\n    "拒绝"\n    return\n', encoding='utf-8')
        _, self.project = open_native(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def create(self, project=None, **values):
        return native_flow.edit(self.root, project or self.project, {'operation':'scene','title':'接受邀请','group':'第一章',**values})

    def test_scene_is_buffered_named_grouped_and_independent(self):
        original = (self.root/'game/story.rpy').read_bytes()
        edit = self.create()
        self.assertFalse((self.root/edit['path']).exists())
        candidate = workspace.projection(self.root, self.project, [edit])
        label = next(l for l in candidate['nativeRenpy']['labels'] if l.get('displayTitle'))
        self.assertRegex(label['name'], r'^scene_[0-9a-f]{12}$')
        self.assertEqual(label['displayTitle'], '接受邀请')
        flow = native_flow.graph(self.root, candidate, [edit])
        node = next(n for n in flow['story']['nodes'] if n['id']==label['id'])
        self.assertEqual(node['group'], '第一章')
        self.assertFalse(any(e['target']==node['id'] for e in flow['edges']))
        self.assertEqual((self.root/'game/story.rpy').read_bytes(), original)
        candidate['ide']={'flowGroups':{label['name']:'自定义章节'}}
        self.assertEqual(next(n for n in native_flow.graph(self.root,candidate,[edit])['nodes'] if n['id']==label['id'])['group'],'自定义章节')

    def test_save_undo_redo_and_reopen_preserve_comment(self):
        edit = self.create()
        saved = workspace.commit(self.root, [edit], self.project['revision'])
        self.assertEqual(next(l for l in saved['project']['nativeRenpy']['labels'] if l.get('displayTitle'))['displayTitle'],'接受邀请')
        reverted = workspace.restore(self.root, saved['transaction'], saved['project']['revision'])
        self.assertFalse((self.root/edit['path']).exists())
        redone = workspace.restore(self.root, saved['transaction'], reverted['project']['revision'], redo=True)
        _, reopened = open_native(self.root)
        self.assertEqual(next(l for l in reopened['nativeRenpy']['labels'] if l.get('displayTitle'))['displayGroup'],'第一章')
        self.assertTrue(redone['project']['sourceStatus']['valid'])

    def test_repeated_creation_and_unsaved_name_collision(self):
        first = self.create(name='scene_fixed')
        candidate = workspace.projection(self.root, self.project, [first])
        with self.assertRaisesRegex(ValueError,'已存在'):
            self.create(candidate, name='scene_fixed', documents=[first])
        second = self.create(candidate, documents=[first])
        next_project = workspace.projection(self.root, candidate, [second])
        created = [l for l in next_project['nativeRenpy']['labels'] if l.get('displayTitle')]
        self.assertEqual(len(created),2)
        self.assertEqual(len({l['name'] for l in created}),2)

    def test_new_disk_declaration_and_external_change_are_checked(self):
        (self.root/'game/new.rpy').write_text('label scene_disk:\n    return\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'已存在'):
            self.create(name='scene_disk')
        doc = workspace.read_document(self.root,'game/story.rpy')
        (self.root/'game/story.rpy').write_text('label start:\n    return\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'已有修改'):
            self.create(path=doc['path'],hash=doc['hash'])

    def test_paths_and_titles_are_validated_and_legacy_calls_work(self):
        for path in ('../outside.rpy','game/../outside.rpy','other/a.rpy','game/a.py','game/cache/a.rpy','game/.creator/a.rpy','C:/x.rpy'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.create(path=path)
        for title in ('','  ','a'*121,42):
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.create(title=title)
        legacy = native_flow.edit(self.root,self.project,{'operation':'scene','name':'legacy_scene','path':'game/legacy.rpy'})
        self.assertIn('label legacy_scene:',legacy['content'])
        self.assertNotIn('morinote-scene',legacy['content'])

    def test_comment_is_inert_and_malformed_hints_are_ignored(self):
        edit = self.create(title='邀请 "你好"\n第二行',group='章节')
        candidate = workspace.projection(self.root,self.project,[edit])
        label = next(l for l in candidate['nativeRenpy']['labels'] if l.get('displayTitle'))
        self.assertEqual(label['displayTitle'],'邀请 "你好"\n第二行')
        self.assertEqual(len(candidate['nativeRenpy']['labels']),4)
        for line in ('# morinote-scene: {bad}', '# morinote-scene: []', '# morinote-scene: {"title":3,"group":"x"}'):
            self.assertEqual(display_hints(line),{})

    def test_choices_preserve_order_and_reject_bad_targets(self):
        flow = native_flow.graph(self.root,self.project)
        node = next(n for n in flow['nodes'] if n['type']=='scene' and n['title']=='start')
        operation = {'operation':'choice','node':node['id'],'hash':node['source']['hash'],'options':[{'text':'接受邀请','target':'route_a'},{'text':'拒绝邀请','target':'route_b'}]}
        edit = native_flow.edit(self.root,self.project,operation)
        self.assertLess(edit['content'].index("'接受邀请'"), edit['content'].index("'拒绝邀请'"))
        self.assertIn('jump route_a',edit['content'])
        for options in ([],[{'text':'','target':'route_a'}],[{'text':'a','target':'absent'}],[{'text':'a'}],{}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                native_flow.edit(self.root,self.project,{**operation,'options':options})
        duplicated = copy.deepcopy(self.project)
        duplicated['nativeRenpy']['labels'].append({**duplicated['nativeRenpy']['labels'][1],'id':'duplicate'})
        with self.assertRaisesRegex(ValueError,'唯一'):
            native_flow.edit(self.root,duplicated,operation)


if __name__=='__main__':
    unittest.main()
