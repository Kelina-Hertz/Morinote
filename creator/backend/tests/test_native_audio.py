from pathlib import Path
import tempfile
import unittest
from backend.renpy_import import open_native
from backend.native_stage import edit
from backend.native_audio import catalog,valid_channel
from backend.workspace import read_document,commit,restore
from backend.project import validate_project
from backend.compiler import generate_project


class NativeAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);game=self.root/'game';game.mkdir()
        (game/'one.wav').write_bytes(b'fixture');(game/'two.wav').write_bytes(b'fixture')
        self.script='label start:\n    play music "one.wav" volume 0.5\n    "A"\n    "B"\n    "C"\n    return\n'
        (game/'script.rpy').write_bytes(b'\xef\xbb\xbf'+self.script.replace('\n','\r\n').encode())
        _,self.project=open_native(self.root)
    def tearDown(self):self.temp.cleanup()
    def lines(self):return next(s for s in self.project['scenes'] if s['title']=='start')['lines']
    def apply(self,channel='creator_bgm_2',action='play',index=0,**params):
        line=self.lines()[index];doc=read_document(self.root,'game/script.rpy')
        op={'operation':'audio_layer','channel':channel,'action':action,'asset':self.project['assets'][0]['id'],'path':doc['path'],'hash':doc['hash'],'line':line['source']['line'],'nodeId':line['id'],**params}
        result=edit(self.root,self.project,op)
        saved=commit(self.root,result.get('edits',[result]),self.project['revision'])
        self.project=saved['project'];return saved
    def test_parallel_layers_registration_roundtrip_and_export(self):
        ids=[l['id'] for l in self.lines()]
        self.apply(volume=.3);self.apply(channel='ambience',volume=.2)
        state=self.lines()[0]['audio']
        self.assertEqual([l['id'] for l in self.lines()],ids)
        self.assertEqual([state[c]['volume'] for c in ('music','creator_bgm_2','ambience')],[.5,.3,.2])
        helper=(self.root/'game/creator_assets/audio_channels.rpy').read_text('utf-8')
        self.assertEqual(helper.count('register_channel('),2)
        self.assertIn('channel_defined',helper)
        self.assertFalse([d for d in validate_project(self.project,self.root) if d['severity']=='error'])
        output=self.root/'export';generate_project(self.root,output)
        self.assertEqual((output/'game/creator_assets/audio_channels.rpy').read_text('utf-8'),helper)
        self.assertNotIn('creator_native_preview',(output/'game/creator_assets/audio_channels.rpy').read_text())
    def test_volume_inserts_no_play_and_only_requested_channel_changes(self):
        self.apply(volume=.4);self.apply(action='volume',index=1,volume=.1,boundary='audio')
        source=read_document(self.root,'game/script.rpy')['content']
        self.assertEqual(source.count('play creator_bgm_2'),1)
        state=self.lines()[1]['audio'];self.assertEqual(state['creator_bgm_2']['volume'],.1)
        self.assertEqual(state['music']['volume'],.5)
        self.apply(action='stop',index=2)
        self.assertEqual(self.lines()[2]['audio']['creator_bgm_2']['asset'],'')
        self.assertTrue(self.lines()[2]['audio']['music']['asset'])
    def test_undo_restores_bom_crlf_and_removes_registration_atomically(self):
        saved=self.apply();self.project=restore(self.root,saved['transaction'],self.project['revision'])['project']
        self.assertEqual((self.root/'game/script.rpy').read_bytes(),b'\xef\xbb\xbf'+self.script.replace('\n','\r\n').encode())
        self.assertFalse((self.root/'game/creator_assets/audio_channels.rpy').exists())
    def test_existing_channel_and_dynamic_code_are_not_overwritten(self):
        scripts=[({},'init python:\n    renpy.music.register_channel("rain", mixer="music", loop=True)\n    # renpy.music.register_channel("comment")\n    renpy.music.register_channel(compute_name())\n')]
        channels=catalog(scripts);self.assertIn('rain',[c['id'] for c in channels]);self.assertNotIn('comment',[c['id'] for c in channels])
        project={**self.project,'nativeRenpy':{'audioChannels':channels}}
        self.assertTrue(valid_channel(project,'rain'));self.assertTrue(valid_channel(project,'creator_bgm_10'))
        self.assertFalse(valid_channel(project,'bad; exit'));self.assertFalse(valid_channel(project,'unknown'))
        self.apply();helper=self.root/'game/creator_assets/audio_channels.rpy';helper.write_text(helper.read_text()+'# manual\n')
        with self.assertRaisesRegex(ValueError,'手工修改'):self.apply(channel='creator_bgm_3')
    def test_replace_resets_volume_multiplier_and_fades_are_independent(self):
        self.apply(volume=.5);self.apply(action='volume',index=1,volume=.1)
        self.apply(index=2,volume=.7,fadeout=.3,fadein=.4)
        state=self.lines()[2]['audio'];self.assertEqual(state['creator_bgm_2']['volume'],.7)
        self.assertEqual(state['creator_bgm_2']['fadein'],.4);self.assertEqual(state['music']['volume'],.5)
        with self.assertRaisesRegex(ValueError,'无效音频参数'):self.apply(volume=float('nan'))

    def test_project_registration_is_preserved_and_stop_keeps_configured_fade(self):
        registration='init 999 python:\n    renpy.music.register_channel("ambience", mixer="sfx", loop=False)\n'
        (self.root/'game/custom.rpy').write_text(registration,encoding='utf-8')
        _,self.project=open_native(self.root)
        self.apply();self.apply(channel='ambience',fadeout=.25)
        helper=(self.root/'game/creator_assets/audio_channels.rpy').read_text()
        self.assertNotIn("register_channel('ambience'",helper)
        self.assertEqual((self.root/'game/custom.rpy').read_text(),registration)
        cue=self.lines()[0]['audio']['ambience'];source=cue['nativeSource']
        doc=read_document(self.root,source['path'])
        changed=edit(self.root,self.project,{**source,'hash':doc['hash'],'operation':'audio','channel':'ambience','property':'asset','value':''})
        self.assertIn('stop ambience fadeout 0.25',changed.get('content',''))
