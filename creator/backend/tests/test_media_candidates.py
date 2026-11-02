"""Candidate storage/preview are isolated; acceptance uses normal source transactions."""
import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from backend.generated_media import GeneratedMedia
from backend.ai_tasks import AITasks
from backend.ai_files import source_files
from backend.renpy_import import open_native
from backend.project import load_project
from backend.workspace import commit, read_document, restore
from backend.media_authoring import prepare
from backend.fragment_authoring import text_hash
from backend.tests.test_media_fragment import PNG, WAV, fixture_plan


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name).resolve()
        (self.root/'game').mkdir()
        (self.root/'game/script.rpy').write_text('define girl = Character("同学")\nlabel start:\n    girl "我忘记带伞了。"\n    return\n',encoding='utf-8')
        _,self.project=open_native(self.root)
        self.original=source_files(self.root)
        self.media=GeneratedMedia()
        self.session='a'*32

    def tearDown(self):self.tmp.cleanup()

    def publish(self,job,kind,data,destination='candidate'):
        artifact={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        receipt=self.media.register(self.root,self.session,{'jobId':job,'kind':kind,'artifact':artifact,'destination':destination})['receipt']
        return self.media.publish(self.root,self.session,{'receipt':receipt,'data':base64.b64encode(data).decode()})

    def items(self):
        self.publish('candidate-bg','image',PNG)
        self.publish('candidate-voice','voice',WAV)
        return [{'key':'background','kind':'image','jobId':'candidate-bg','sha256':hashlib.sha256(PNG).hexdigest()},
                {'key':'first','kind':'voice','jobId':'candidate-voice','sha256':hashlib.sha256(WAV).hexdigest(),'ttsHash':text_hash('fixture synthesis'),'candidateId':'candidate-voice'}]

    def test_unaccepted_candidates_never_enter_game_or_source_inventory(self):
        result=self.publish('candidate-bg','image',PNG)
        self.assertTrue(result['path'].startswith('.creator/media/candidates/'))
        self.assertEqual(source_files(self.root),self.original)
        self.assertFalse((self.root/'game/images/creator_generated').exists())
        self.assertEqual(load_project(self.root)['revision'],self.project['revision'])

    def test_preview_installs_only_in_snapshot_and_rebuilds_immutable_baseline(self):
        items=self.items()
        tasks=AITasks(self.root,Mock())
        body={'creativeId':'creative_fixture','fragmentId':'fragment_fixture','kind':'fragment','title':'候选雨夜',
              'plan':fixture_plan(),'imports':items,'state':{'documents':[]},'candidateVersion':'version-1'}
        result=self.media.preview(self.root,self.session,body,tasks)
        snapshot=Path(result['task']['root'])
        self.assertEqual(source_files(self.root),self.original)
        self.assertFalse((self.root/'game/creator_assets/asset_bindings.rpy').exists())
        self.assertTrue((snapshot/'game/images/creator_generated/candidate-bg/output.png').exists())
        source=snapshot/'game/creator_fragments/fragment_fixture.rpy'
        self.assertEqual(source.read_text('utf-8').count('label '),1)
        self.assertIn('送她回家',source.read_text('utf-8'))
        meta=tasks.meta(result['task']['id'])
        self.assertEqual(meta['mediaCandidateVersion'],'version-1')
        self.assertEqual(meta['baselineSnapshot'],source_files(snapshot))
        tasks.guard(meta)

    def test_candidate_receipt_is_scoped_and_modified_bytes_cannot_preview(self):
        items=self.items()
        path=self.root/'.creator/media/candidates/candidate-bg/output.png'
        path.write_bytes(PNG+b'changed')
        with self.assertRaisesRegex(ValueError,'摘要'):
            self.media.preview(self.root,self.session,{'imports':items},AITasks(self.root,Mock()))
        with self.assertRaises(ValueError):
            self.media.register(self.root,self.session,{'jobId':'x','kind':'image','artifact':{'sha256':'0'*64,'bytes':1},'destination':'../game'})

    def test_accepted_media_prepares_one_batch_and_undo_keeps_paid_artifacts(self):
        items=self.items()
        for item,data in zip(items,[PNG,WAV]):
            item.update(self.publish(item['jobId'],item['kind'],data,'project'))
        project=load_project(self.root)
        result=prepare(self.root,project,{'kind':'fragment','fragmentId':'fragment_fixture','title':'候选雨夜','plan':fixture_plan(),'imports':items})
        self.assertEqual(len(result['edits']),2)
        self.assertFalse((self.root/result['path']).exists())
        saved=commit(self.root,result['edits'],project['revision'])
        restored=restore(self.root,saved['transaction'],saved['project']['revision'])
        self.assertFalse((self.root/result['path']).exists())
        self.assertTrue((self.root/items[0]['path']).exists())
        self.assertTrue((self.root/'.creator/media/candidates/candidate-bg/output.png').exists())

    def test_standalone_voice_is_attached_to_the_original_say_and_becomes_stale(self):
        item={'key':'voice','kind':'voice','jobId':'candidate-voice','sha256':hashlib.sha256(WAV).hexdigest(),'ttsHash':text_hash('synthesis'),'candidateId':'candidate-voice'}
        item.update(self.publish('candidate-voice','voice',WAV,'project'))
        _,project=open_native(self.root)
        line=next(l for s in project['scenes'] for l in s['lines'])
        target={'nodeId':line['id'],'textHash':text_hash('我忘记带伞了。')}
        result=prepare(self.root,project,{'kind':'voice','title':'同学配音','target':target,'imports':[item]})
        saved=commit(self.root,result['edits'],project['revision'])
        voice=next(l for s in saved['project']['scenes'] for l in s['lines'])['voice']
        self.assertFalse(voice['generation']['stale'])
        self.assertEqual(voice['generation']['candidateId'],'candidate-voice')
        file=self.root/'game/script.rpy'
        file.write_text(file.read_text('utf-8').replace('我忘记带伞了。','雨好大。'),encoding='utf-8')
        _,changed=open_native(self.root)
        self.assertTrue(next(l for s in changed['scenes'] for l in s['lines'])['voice']['generation']['stale'])

    def test_standalone_candidate_preview_needs_no_formal_binding(self):
        items=self.items()[:1]
        tasks=AITasks(self.root,Mock())
        result=self.media.preview(self.root,self.session,{'creativeId':'creative_image','kind':'image','title':'图片候选','imports':items,'state':{'documents':[]},'candidateVersion':'v1'},tasks)
        self.assertTrue(result['label'].startswith('creator_candidate_'))
        self.assertEqual(source_files(self.root),self.original)
        tasks.guard(tasks.meta(result['task']['id']))

    def test_new_fragment_revision_does_not_overwrite_manual_changes_without_expected_hash(self):
        items=self.items()
        for item,data in zip(items,[PNG,WAV]):item.update(self.publish(item['jobId'],item['kind'],data,'project'))
        project=load_project(self.root)
        body={'kind':'fragment','fragmentId':'fragment_fixture','title':'候选雨夜','plan':fixture_plan(),'imports':items}
        result=prepare(self.root,project,body)
        saved=commit(self.root,result['edits'],project['revision'])
        with self.assertRaises(ValueError):prepare(self.root,saved['project'],body)
        updated=prepare(self.root,saved['project'],{**body,'entryIds':result['entryIds'],'replaceHash':text_hash((self.root/result['path']).read_text('utf-8'))})
        self.assertEqual(updated['label'],result['label'])


if __name__=='__main__':unittest.main()
