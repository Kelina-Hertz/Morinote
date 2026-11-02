"""Zero-cost fixtures exercise publication, authored RPY, Voice and recovery."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.generated_media import GeneratedMedia
from backend.fragment_authoring import prepare, validate, text_hash
from backend.renpy_import import open_native
from backend.workspace import commit, read_document, projection, restore
from backend.native_stage import edit
from backend.native_assets import edit as asset_edit, REGISTRY
from backend.server import Service
from backend.native_flow import graph

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
WAV=b'RIFF'+(36+3200).to_bytes(4,'little')+b'WAVEfmt '+(16).to_bytes(4,'little')+(1).to_bytes(2,'little')*2+(16000).to_bytes(4,'little')+(32000).to_bytes(4,'little')+(2).to_bytes(2,'little')+(16).to_bytes(2,'little')+b'data'+(3200).to_bytes(4,'little')+bytes(3200)


def fixture_plan():
    return {'version':1,'title':'雨夜校门 · fixture','characters':[{'id':'girl','name':'同学'}],
            'background':{'mode':'generate','prompt':'fixture campus gate in rain'},
            'lines':[{'id':'arrival','kind':'narration','text':'雨点落在校门外。'},
                     {'id':'first','kind':'dialogue','speaker':'girl','text':'我忘记带伞了。','voice':{}},
                     {'id':'reply','kind':'dialogue','speaker':'girl','text':'你也刚放学吗？'}],
            'choice':{'options':[{'id':'escort','text':'送她回家','lines':[{'id':'escort_reply','kind':'dialogue','speaker':'girl','text':'谢谢，我们一起走吧。'}]},
                                 {'id':'lend','text':'把伞借给她','lines':[{'id':'lend_reply','kind':'dialogue','speaker':'girl','text':'明天我会把伞还给你。'}]}]},
            'ending':[{'id':'end','kind':'narration','text':'雨声渐渐远去。'}]}


class MediaFragmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();(self.root/'game').mkdir()
        self.original='label start:\n    "原工程入口"\n    return\n'
        (self.root/'game/script.rpy').write_text(self.original,encoding='utf-8')
        _,self.project=open_native(self.root);self.media=GeneratedMedia();self.session='a'*32

    def tearDown(self):self.temp.cleanup()

    def publish(self,job,kind,data):
        record=self.media.register(self.root,self.session,{'jobId':job,'kind':kind,'artifact':{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}})
        result=self.media.publish(self.root,self.session,{'receipt':record['receipt'],'data':base64.b64encode(data).decode()})
        _,self.project=open_native(self.root)
        return result

    def make_virtual(self,asset,name,kind,documents):
        create=asset_edit(self.root,projection(self.root,self.project,documents),{'operation':'create','name':name,'type':kind,'documents':documents})
        documents[:]=[d for d in documents if d['path']!=REGISTRY]+[create]
        bind=asset_edit(self.root,projection(self.root,self.project,documents),{'operation':'bind','id':create['entryId'],'binding':{'kind':'file','key':asset['gamePath']},'documents':documents})
        documents[:]=[d for d in documents if d['path']!=REGISTRY]+[bind]
        return create['entryId']

    def ready(self,plan=None):
        plan=plan or fixture_plan();bg=self.publish('fixture-background','image',PNG);voice=self.publish('fixture-voice','voice',WAV)
        documents=[];bgid=self.make_virtual(bg,'fixture 背景','background',documents);vid=self.make_virtual(voice,'fixture 配音','voice',documents)
        body={'fragmentId':'fixture_rain','plan':plan,'documents':documents,'bindings':{'background':bgid,'voices':{'first':{'assetId':vid,'jobId':'fixture-voice','ttsHash':text_hash('我忘记带伞了。'),'artifactHash':hashlib.sha256(WAV).hexdigest()}}}}
        result=prepare(self.root,self.project,body)
        return result,documents

    def test_publication_is_registered_project_scoped_and_non_overwriting(self):
        image=self.publish('fixture-background','image',PNG)
        self.assertEqual(image['gamePath'],'images/creator_generated/fixture-background/output.png')
        self.assertEqual((self.root/image['path']).read_bytes(),PNG)
        again=self.publish('fixture-background','image',PNG)
        self.assertEqual(again['assetId'],image['assetId'])
        with self.assertRaises(ValueError):self.media.publish(self.root,'b'*32,{'receipt':'invalid','data':''})
        with self.assertRaises(ValueError):self.media.register(self.root,self.session,{'jobId':'../escape','kind':'image','artifact':{'sha256':'0'*64,'bytes':30}})
        self.assertEqual((self.root/'game/script.rpy').read_text('utf-8'),self.original)

    def test_bad_payload_and_hash_do_not_create_assets(self):
        data=b'{"success":true}'
        receipt=self.media.register(self.root,self.session,{'jobId':'bad','kind':'voice','artifact':{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}})['receipt']
        with self.assertRaises(ValueError):self.media.publish(self.root,self.session,{'receipt':receipt,'data':base64.b64encode(data).decode()})
        with self.assertRaises(ValueError):self.media.publish(self.root,self.session,{'receipt':receipt,'data':base64.b64encode(WAV).decode()})
        self.assertFalse((self.root/'game/audio/creator_generated/bad').exists())

    def test_plan_rejects_duplicates_missing_assets_and_incomplete_routes_before_generation(self):
        for modify in [lambda p:p['ending'][0].update(id='arrival'),lambda p:p['choice']['options'][0].update(lines=[]),lambda p:p['characters'][0].update(spriteAssetId='missing'),lambda p:p['lines'][1].update(speaker='unknown')]:
            p=fixture_plan();modify(p)
            with self.assertRaises(ValueError):validate(p,self.project)

    def test_fragment_is_one_label_with_both_routes_and_one_voice_in_same_transaction(self):
        result,documents=self.ready();self.assertEqual(result['content'].count('label '),1)
        self.assertIn('送她回家',result['content']);self.assertIn('把伞借给她',result['content'])
        self.assertEqual(sum(bool(line.strip().startswith('voice ')) for line in result['content'].splitlines()),1)
        self.assertEqual(len(result['nodeMap']),6)
        self.assertFalse((self.root/result['path']).exists())
        saved=commit(self.root,documents+[result],self.project['revision'])
        self.project=saved['project'];_,reopened=open_native(self.root)
        scene=next(s for s in reopened['scenes'] if s['id']==result['sceneId'])
        self.assertEqual(len(scene['lines']),6)
        line=next(l for l in scene['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
        self.assertFalse(line['voice']['generation']['stale'])
        story=graph(self.root,reopened)['story']
        self.assertTrue(any(n['id']==result['sceneId'] for n in story['nodes']))
        self.assertTrue(any(g['title']=='生成片段' for g in story['groups']))
        self.assertEqual((self.root/'game/script.rpy').read_text('utf-8'),self.original)
        self.assertIn('fixture-background',json.dumps(reopened['nativeAssetLibrary'],ensure_ascii=False))

    def test_fragment_batch_undo_redo_keeps_generated_files(self):
        result,documents=self.ready()
        saved=commit(self.root,documents+[result],self.project['revision'])
        undone=restore(self.root,saved['transaction'],saved['project']['revision'])
        self.assertFalse((self.root/result['path']).exists())
        self.assertFalse((self.root/REGISTRY).exists())
        self.assertEqual((self.root/'game/audio/creator_generated/fixture-voice/output.wav').read_bytes(),WAV)
        self.assertEqual((self.root/'game/images/creator_generated/fixture-background/output.png').read_bytes(),PNG)
        redone=restore(self.root,saved['transaction'],undone['project']['revision'],redo=True)
        self.assertTrue(any(s['id']==result['sceneId'] for s in redone['project']['scenes']))
        self.assertTrue((self.root/REGISTRY).exists())

    def test_editing_text_marks_voice_stale_without_changing_audio(self):
        result,documents=self.ready();self.project=commit(self.root,documents+[result],self.project['revision'])['project']
        line=next(l for s in self.project['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
        change=edit(self.root,self.project,{'operation':'text','nodeId':line['id'],'value':'雨好大呀。','hash':read_document(self.root,result['path'])['hash']})
        self.project=commit(self.root,[change],self.project['revision'])['project']
        after=next(l for s in self.project['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
        self.assertTrue(after['voice']['generation']['stale'])
        self.assertEqual((self.root/'game/audio/creator_generated/fixture-voice/output.wav').read_bytes(),WAV)

    def test_inserting_source_before_voice_does_not_bind_by_stale_line_number(self):
        result,documents=self.ready();self.project=commit(self.root,documents+[result],self.project['revision'])['project']
        path=self.root/result['path'];path.write_text('# comment inserted externally\n'+path.read_text('utf-8'),encoding='utf-8')
        _,reopened=open_native(self.root)
        line=next(l for s in reopened['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
        self.assertFalse(line['voice']['generation']['stale'])

    def test_natural_text_is_escaped_and_no_main_entry_is_added(self):
        plan=fixture_plan();plan['lines'][0]['text']='[__import__("os")] {b}文字{/b}'
        result,_=self.ready(plan)
        self.assertIn('[[__import__',result['content']);self.assertIn('{{b}',result['content'])
        self.assertNotIn('jump start',result['content']);self.assertNotIn('$ __import__',result['content'])

    def test_voice_formatter_is_preserved_without_double_prefix(self):
        (self.root/'game/script.rpy').write_text('define config.voice_filename_format = "audio/voice/{filename}.ogg"\n'+self.original,encoding='utf-8')
        _,self.project=open_native(self.root)
        result,documents=self.ready()
        self.project=commit(self.root,documents+[result],self.project['revision'])['project']
        line=next(l for s in self.project['scenes'] for l in s['lines'] if l.get('generatedNode',{}).get('nodeId')=='first')
        self.assertTrue(line['voice']['filename'].startswith('audio/voice/_creator_virtual/'))
        self.assertNotIn('audio/voice/audio/voice/',line['voice']['filename'])
        self.assertIn('voice "_creator_virtual/',result['content'])

    def test_generated_entry_requires_privileged_host_and_explicit_session(self):
        with patch('backend.server.Engine'):
            service=Service(self.root,'fixture-backend',media_token='fixture-media')
        service.select_project(self.root)
        payload={'projectSession':service.project_session,'projectRoot':str(self.root),'jobId':'x','kind':'image','artifact':{'sha256':hashlib.sha256(PNG).hexdigest(),'bytes':len(PNG)}}
        with self.assertRaises(ValueError):service.dispatch('/api/generated-media/register',payload)
        self.assertIn('receipt',service.dispatch('/api/generated-media/register',payload,media_token='fixture-media'))
        payload.pop('projectSession')
        with self.assertRaises(ValueError):service.dispatch('/api/generated-media/register',payload,media_token='fixture-media')


if __name__=='__main__':unittest.main()
