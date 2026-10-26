import hashlib
from pathlib import Path
import tempfile
import unittest

from backend.ai_tasks import AITasks
from backend.renpy_import import open_native
from backend import workspace


class AITaskTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'game').mkdir()
        self.raw=b'\xef\xbb\xbfdefine e = Character("Test")\r\nlabel start:\r\n    e "Alpha"\r\n    return\r\n'
        (self.root/'game/script.rpy').write_bytes(self.raw)
        (self.root/'game/picture.png').write_bytes(b'original-media')
        open_native(self.root);self.tasks=AITasks(self.root,None)
        self.document=workspace.read_document(self.root,'game/script.rpy')
        self.state={'documents':[{'base':self.document,'value':self.document['content'].replace('Alpha','Unsaved'),'origin':'code'}]}
        self.task=self.tasks.new('test',self.state,{'line':'start'})
        self.tid=self.task['id'];self.copy=Path(self.task['root'])

    def write(self,text,call='edit'):
        doc=self.tasks.tool(self.tid,'read',{'path':'game/script.rpy'},'read-'+call)
        return self.tasks.tool(self.tid,'write',{'path':doc['path'],'hash':doc['hash'],'content':text},call)

    def test_unsaved_snapshot_and_media_are_independent(self):
        self.assertIn('Unsaved',(self.copy/'game/script.rpy').read_text('utf-8-sig'))
        self.assertEqual((self.root/'game/script.rpy').read_bytes(),self.raw)
        (self.copy/'game/picture.png').write_bytes(b'changed-copy')
        self.assertEqual((self.root/'game/picture.png').read_bytes(),b'original-media')
        with self.assertRaisesRegex(ValueError,'只读素材'):self.tasks.diff(self.tid,self.state)

    def test_review_prepares_buffers_without_writing_original(self):
        self.write(self.state['documents'][0]['value'].replace('Unsaved','AI'))
        diff=self.tasks.diff(self.tid,self.state)
        prepared=self.tasks.prepare_apply(self.tid,diff['reviewHash'],self.state)
        self.assertEqual((self.root/'game/script.rpy').read_bytes(),self.raw)
        self.assertTrue(prepared['documents'][0]['base']['bom'])
        self.assertEqual(prepared['documents'][0]['base']['newline'],'\r\n')
        self.assertIn('"AI"',prepared['documents'][0]['value'])

    def test_editor_and_disk_changes_block_apply(self):
        self.write(self.state['documents'][0]['value'].replace('Unsaved','AI'))
        reviewed=self.tasks.diff(self.tid,self.state)['reviewHash']
        changed={'documents':[{**self.state['documents'][0],'value':'# manual\n'+self.state['documents'][0]['value']}]}
        with self.assertRaisesRegex(ValueError,'合并'):self.tasks.prepare_apply(self.tid,reviewed,changed)
        (self.root/'game/script.rpy').write_text('# external\n'+self.document['content'],encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'合并'):self.tasks.prepare_apply(self.tid,reviewed,self.state)

    def test_rebase_preserves_manual_change_and_requires_fresh_review(self):
        self.write(self.state['documents'][0]['value'].replace('Unsaved','AI'))
        changed={'documents':[{**self.state['documents'][0],'value':'# manual\r\n'+self.state['documents'][0]['value']}]}
        result=self.tasks.rebase(self.tid,changed)
        self.assertFalse(result['conflicts']);self.assertFalse(result['diff']['conflict'])
        prepared=self.tasks.prepare_apply(self.tid,result['diff']['reviewHash'],changed)
        self.assertIn('# manual',prepared['documents'][0]['value']);self.assertIn('"AI"',prepared['documents'][0]['value'])

    def test_new_and_deleted_files_are_explicit_pending_changes(self):
        self.tasks.tool(self.tid,'write',{'path':'game/new.rpy','content':'# New\n'},'new')
        self.tasks.tool(self.tid,'delete',{'path':'game/script.rpy','hash':workspace.read_document(self.copy,'game/script.rpy')['hash']},'delete')
        diff=self.tasks.diff(self.tid,self.state);prepared=self.tasks.prepare_apply(self.tid,diff['reviewHash'],self.state)
        by={d['base']['path']:d for d in prepared['documents']}
        self.assertTrue(by['game/script.rpy']['deleted']);self.assertFalse(by['game/new.rpy']['base']['exists'])
        self.assertTrue((self.root/'game/script.rpy').exists());self.assertFalse((self.root/'game/new.rpy').exists())

    def test_path_escape_and_media_writes_are_refused(self):
        for path in ('../outside.rpy','game/../../outside.rpy','game/picture.png','.creator/editor/project.json'):
            with self.assertRaises(ValueError):self.tasks.tool(self.tid,'write',{'path':path,'content':'bad'},'bad-'+hashlib.sha256(path.encode()).hexdigest())

    def test_terminal_recovery_does_not_replay_uncertain_or_completed_calls(self):
        payload={'callId':'terminal-1','command':'Write-Output OK','purpose':'test','stage':'begin'}
        self.assertTrue(self.tasks.terminal(self.tid,payload)['accepted'])
        self.assertFalse(self.tasks.terminal(self.tid,payload)['accepted'])
        result={'status':'passed','exitCode':0,'log':'OK'}
        self.tasks.terminal(self.tid,{**payload,'stage':'finish','result':result})
        self.assertEqual(self.tasks.terminal(self.tid,payload)['result'],result)
        with self.assertRaises(ValueError):self.tasks.terminal(self.tid,{**payload,'command':'Write-Output CHANGED'})

    def test_duplicate_write_uses_ledger_and_changed_arguments_are_refused(self):
        args={'path':'game/new.rpy','content':'# first\n'}
        self.tasks.tool(self.tid,'write',args,'same')
        (self.copy/'game/new.rpy').write_text('# later\n',encoding='utf-8')
        self.tasks.tool(self.tid,'write',args,'same')
        self.assertEqual((self.copy/'game/new.rpy').read_text('utf-8'),'# later\n')
        with self.assertRaises(ValueError):self.tasks.tool(self.tid,'write',{**args,'content':'# other\n'},'same')
