from pathlib import Path
import copy
import tempfile
import unittest
from backend.renpy_import import open_native
from backend.workspace import read_document,commit
from backend.native_stage import edit


class NativeMotionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);game=self.root/'game';(game/'gui/characters/hero').mkdir(parents=True)
        (game/'gui/characters/hero/a.png').write_bytes(b'fixture')
        self.script='''define e = Character("E")
image bg = "#ffffff"
image hero:
    "gui/characters/hero/a.png"
    zoom 0.4
image friend:
    "gui/characters/hero/a.png"
    zoom 0.5
label start:
    scene bg
    show hero as actor:
        xpos 200
        ypos 300
    show friend as friend:
        xpos 500
        ypos 300
    e "A"
    e "B"
    e "C"
    return
'''
        (game/'script.rpy').write_bytes(b'\xef\xbb\xbf'+self.script.replace('\n','\r\n').encode('utf-8'))
        _,self.project=open_native(self.root)

    def tearDown(self):self.temp.cleanup()
    def scene(self):return next(s for s in self.project['scenes'] if s['title']=='start')
    def apply(self,operation,source=None):
        doc=read_document(self.root,'game/script.rpy');line=self.scene()['lines'][1]
        source=source or {'path':doc['path'],'line':line['source']['line'],'nodeId':line['id']}
        changed=edit(self.root,self.project,{**source,**operation,'hash':doc['hash']})
        self.project=commit(self.root,changed.get('edits',[changed]),self.project['revision'])['project']
        return changed.get('content',changed.get('edits',[{}])[0].get('content',''))
    def motion(self,kind='move',**patch):
        settings={'kind':kind,'duration':.6,'easing':'ease','start':[200,300],'end':[400,300],'amplitude':50,'repeat':2,'wait':False,**patch}
        return {'operation':'motion','tag':'actor','motion':settings}

    def test_apply_roundtrip_update_and_remove_preserve_source_text_other_actor_and_encoding(self):
        ids=[l['id'] for l in self.scene()['lines']]
        text=self.apply(self.motion());self.assertIn('ease 0.6 xpos 400 ypos 300 alpha 1.0',text)
        line=self.scene()['lines'][1];self.assertEqual([l['id'] for l in self.scene()['lines']],ids)
        actors=line['visual']['sprites'];self.assertEqual(next(a for a in actors if a['id']=='friend')['x'],500)
        actor=next(a for a in actors if a['id']=='actor');self.assertEqual(actor['x'],400);self.assertEqual(actor['scale'],.4)
        self.assertEqual(actor['nativeMotion']['kind'],'move')
        text=self.apply(self.motion(duration=1));self.assertEqual(text.count('# creator:motion {'),1)
        self.assertIn('ease 1 xpos 400',text)
        self.apply({'operation':'motion','tag':'actor','action':'remove'})
        self.assertEqual((self.root/'game/script.rpy').read_bytes(),b'\xef\xbb\xbf'+self.script.replace('\n','\r\n').encode('utf-8'))

    def test_presets_wait_and_final_positions(self):
        for kind in ('move','enter_left','enter_right','fadein','jump','shake'):
            with self.subTest(kind=kind):
                self.apply(self.motion(kind,wait=True))
                actor=next(a for a in self.scene()['lines'][1]['visual']['sprites'] if a['id']=='actor')
                self.assertEqual((actor['x'],actor['y']),(400,300))
                self.assertIn('hard=True',read_document(self.root,'game/script.rpy')['content'])
                self.assertEqual(actor['id'],'actor')
        self.assertEqual(read_document(self.root,'game/script.rpy')['content'].count('# creator:motion {'),1)

    def test_normal_property_and_expression_controls_keep_owned_motion_editable(self):
        self.apply(self.motion())
        actor=lambda:next(a for a in self.scene()['lines'][1]['visual']['sprites'] if a['id']=='actor')
        self.apply({'operation':'properties','values':{'xpos':450,'ypos':320}},actor()['nativeSource'])
        self.apply({'operation':'property','property':'zoom','value':.8,'effective':True},actor()['nativeSource'])
        self.apply({'operation':'image','value':'friend'},actor()['nativeSource'])
        self.assertEqual((actor()['x'],actor()['y']),(450,320));self.assertAlmostEqual(actor()['scale'],.8)
        self.assertEqual(actor()['nativeMotion']['image'],'friend')
        self.apply({'operation':'motion','tag':'actor','action':'remove'})

    def test_manual_edits_not_overwritten_and_invalid_input_rejected(self):
        self.apply(self.motion());doc=read_document(self.root,'game/script.rpy')
        self.project=commit(self.root,[{**doc,'content':doc['content'].replace('    # creator:motion end','        # hand edited\n    # creator:motion end')}],self.project['revision'])['project']
        with self.assertRaisesRegex(ValueError,'手工修改'):self.apply(self.motion())
        doc=read_document(self.root,'game/script.rpy');self.assertIn('hand edited',doc['content'])
        from backend.native_motion import render
        spec=copy.deepcopy(next(a for a in self.scene()['lines'][1]['visual']['sprites'] if a['id']=='actor')['nativeMotion'])
        for patch in ({'duration':float('nan')},{'kind':'python'},{'easing':'eval'},{'repeat':100},{'start':[float('inf'),0]}):
            with self.assertRaises(ValueError):render({**spec,**patch})

    def test_action_stays_before_auto_prepare_and_does_not_change_clicks(self):
        self.apply({'operation':'auto_wait','value':.7})
        before=[l['text'] for l in self.scene()['lines']]
        text=self.apply(self.motion('jump',wait=True))
        self.assertIn('# creator:motion end\n    $ creator_native_auto_prepare(',text)
        self.assertEqual([l['text'] for l in self.scene()['lines']],before)
        self.assertEqual(self.scene()['lines'][1]['autoWait'],.7)
