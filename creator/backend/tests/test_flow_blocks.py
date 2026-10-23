import copy
from pathlib import Path
import tempfile
import unittest

from backend.renpy_import import open_native
from backend.native_flow import graph, edit
from backend.workspace import projection, commit, restore
from backend.flow_authoring import digest, PENDING_OUTLET


class FlowBlocksTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'game').mkdir()
        self.text='label start:\n    jump a\n# morinote-scene: {"title":"邀请","group":"剧情"}\nlabel a:\n    "原有正文"\n    jump b\nlabel b:\n    "后续"\n    return\n'
        (self.root/'game/story.rpy').write_text(self.text,encoding='utf-8',newline='\n')
        _,self.project=open_native(self.root);self.documents=[]

    def tearDown(self): self.temp.cleanup()

    def op(self,kind,name=None,**data):
        flow=graph(self.root,self.project,self.documents)
        hashes=copy.deepcopy(flow['authoring']['documents'])
        hashes.setdefault('game/creator_scenes.rpy',{'hash':digest(''),'contentHash':digest('')})
        node=next((l['id'] for l in self.project['nativeRenpy']['labels'] if l['name']==name),None)
        return edit(self.root,self.project,{'operation':kind,'node':node,'hashes':hashes,'documents':self.documents,**data})

    def apply(self,result):
        docs={d['path']:d for d in self.documents};docs.update({d['path']:d for d in result['edits']})
        self.documents=list(docs.values());self.project=projection(self.root,self.project,self.documents)

    def paste(self,clipboard,name='scene_copy'):
        return self.op('paste_block',clipboard=clipboard['token'],scene={'name':name,'title':'邀请 副本','group':'剧情','path':'game/creator_scenes.rpy'})

    def test_copy_pastes_full_body_with_new_identity_and_preserves_draft(self):
        draft=self.text.replace('原有正文','尚未保存的正文')
        self.documents=[{'path':'game/story.rpy','hash':digest(self.text),'content':draft}]
        self.project=projection(self.root,self.project,self.documents)
        clipboard=self.op('copy_block','a',title='邀请',group='剧情')['clipboard']
        pasted=self.paste(clipboard);self.apply(pasted)
        clone=next(s for s in self.project['scenes'] if s['title']=='scene_copy')
        self.assertEqual(clone['lines'][0]['text'],'尚未保存的正文')
        self.assertIn('jump b',pasted['edits'][0]['content'])
        self.assertNotIn('"新场景"',pasted['edits'][0]['content'])
        self.assertEqual((self.root/'game/story.rpy').read_text('utf-8'),self.text)
        self.assertFalse((self.root/'game/creator_scenes.rpy').exists())

    def test_delete_disconnects_cross_file_refs_and_undo_restores_once(self):
        caller=self.root/'game/caller.rpy';caller.write_text('label caller:\n    call a\n    "继续"\n    jump a # retain\n',encoding='utf-8',newline='\n')
        _,self.project=open_native(self.root)
        result=self.op('delete_block','a')
        self.assertEqual(len(result['edits']),2)
        values={d['path']:d['content'] for d in result['edits']}
        self.assertNotIn('label a:',values['game/story.rpy'])
        self.assertNotIn('"title":"邀请"',values['game/story.rpy'])
        self.assertIn('pass\n    "继续"',values['game/caller.rpy'])
        self.assertIn('return'+PENDING_OUTLET+' # retain',values['game/caller.rpy'])
        saved=commit(self.root,result['edits'],self.project['revision'])
        self.assertNotIn('a',{l['name'] for l in saved['project']['nativeRenpy']['labels']})
        restored=restore(self.root,saved['transaction'],saved['project']['revision'])
        self.assertEqual((self.root/'game/story.rpy').read_text('utf-8'),self.text)
        restore(self.root,saved['transaction'],restored['project']['revision'],redo=True)
        self.assertNotIn('label a:',(self.root/'game/story.rpy').read_text('utf-8'))

    def test_cut_paste_and_implicit_connections_are_preserved(self):
        self.text=self.text.replace('    jump a\n','        "顺序进入"\n',1).replace('    jump b\n','',1)
        (self.root/'game/story.rpy').write_text(self.text,encoding='utf-8',newline='\n');_,self.project=open_native(self.root)
        clipboard=self.op('copy_block','a',title='邀请',group='剧情',cut=True)['clipboard']
        self.apply(self.op('delete_block','a'))
        content=self.documents[0]['content']
        self.assertIn('"顺序进入"\n        return'+PENDING_OUTLET,content)
        self.apply(self.paste(clipboard))
        content=self.documents[0]['content'];self.assertIn('label a:',content)
        self.assertIn('"原有正文"\n    jump b',content)
        with self.assertRaisesRegex(ValueError,'已恢复'): self.paste(clipboard)

    def test_copy_choice_self_loop_and_return_sites(self):
        self.text='label start:\n    return\n# morinote-scene: {"title":"分支","group":"剧情","kind":"choice"}\nlabel a:\n    call helper from original_site\n    menu:\n        "重试":\n            jump a\n        "结束":\n            return\nlabel helper:\n    return\n'
        (self.root/'game/story.rpy').write_text(self.text,encoding='utf-8',newline='\n');_,self.project=open_native(self.root)
        clipboard=self.op('copy_block','a',title='分支',group='剧情')['clipboard']
        result=self.paste(clipboard);text=result['edits'][0]['content']
        self.assertIn('jump scene_copy',text);self.assertIn('"kind": "choice"',text)
        self.assertIn('from original_site_',text)

    def test_reject_entry_duplicates_dynamic_reference_and_external_change(self):
        with self.assertRaisesRegex(ValueError,'入口'):self.op('delete_block','start')
        other=self.root/'game/config.rpy';other.write_text('define test_entry = "a"\n',encoding='utf-8',newline='\n');_,self.project=open_native(self.root)
        with self.assertRaisesRegex(ValueError,'引用'):self.op('delete_block','a')
        other.write_text('label a:\n    return\n',encoding='utf-8',newline='\n');_,self.project=open_native(self.root)
        with self.assertRaisesRegex(ValueError,'重复'):self.op('delete_block','a')
        other.unlink();_,self.project=open_native(self.root)
        copied=self.op('copy_block','a',title='邀请',group='剧情')['clipboard']
        self.assertTrue(copied['token'])
        hashes=graph(self.root,self.project)['authoring']['documents'];node=next(l['id'] for l in self.project['nativeRenpy']['labels'] if l['name']=='a')
        (self.root/'game/story.rpy').write_text(self.text+'# external\n',encoding='utf-8',newline='\n')
        with self.assertRaisesRegex(ValueError,'变化'):edit(self.root,self.project,{'operation':'delete_block','node':node,'hashes':hashes})


if __name__=='__main__':unittest.main()
