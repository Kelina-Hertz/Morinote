from pathlib import Path
import tempfile
import unittest

from backend.renpy_import import open_native
from backend.workspace import commit
from backend.native_assets import edit, REGISTRY


class VirtualAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        (self.root/'game').mkdir();(self.root/'game/hero.png').write_bytes(b'unchanged image')
        self.script='image hero:\n    "hero.png"\n    zoom 0.5\nlabel start:\n    show hero\n    "Hello"\n    return\n'
        (self.root/'game/script.rpy').write_text(self.script,encoding='utf-8')
        _,self.project=open_native(self.root)

    def tearDown(self): self.temp.cleanup()

    def entry(self): return next(e for e in self.project['nativeAssetLibrary']['entries'] if e['runtime']['key']=='hero')

    def apply(self, operation):
        change=edit(self.root,self.project,operation)
        self.project=commit(self.root,[change],self.project['revision'])['project']

    def test_scan_and_rename_do_not_change_source_or_material(self):
        self.assertFalse((self.root/REGISTRY).exists())
        self.apply({'operation':'update','id':self.entry()['id'],'values':{'name':'女主 · 日常'}})
        _,self.project=open_native(self.root)
        self.assertEqual(self.entry()['name'],'女主 · 日常')
        self.assertEqual((self.root/'game/script.rpy').read_text('utf-8'),self.script)
        self.assertEqual((self.root/'game/hero.png').read_bytes(),b'unchanged image')

    def test_temporary_replacement_keeps_requirement_and_survives_rescan(self):
        eid=self.entry()['id']
        self.apply({'operation':'update','id':eid,'values':{'requirement':'女仆装 · 害羞'}})
        self.apply({'operation':'bind','id':eid,'binding':{'kind':'file','key':'hero.png'},'temporary':True})
        _,self.project=open_native(self.root)
        self.assertEqual(self.entry()['status'],'temporary')
        self.assertEqual(self.entry()['requirement'],'女仆装 · 害羞')
        self.apply({'operation':'unbind','id':eid})
        self.assertEqual(self.entry()['status'],'unbound')
        self.assertIsNone(self.entry()['binding'])

    def test_referenced_entry_cannot_be_deleted(self):
        with self.assertRaisesRegex(ValueError,'引用'):self.apply({'operation':'delete','id':self.entry()['id']})
        self.assertTrue((self.root/'game/hero.png').exists())

    def test_known_character_directories_seed_roles_without_guessing_costumes(self):
        target=self.root/'game/gui/characters/xiquan/neutral.png';target.parent.mkdir(parents=True);target.write_bytes(b'image')
        (self.root/'game/roles.rpy').write_text('image xiquan = "gui/characters/xiquan/neutral.png"\n')
        _,project=open_native(self.root)
        entry=next(e for e in project['nativeAssetLibrary']['entries'] if e['runtime']['key']=='xiquan')
        self.assertEqual(entry['character'],'汐泉');self.assertEqual(entry['costume'],'');self.assertEqual(entry['expression'],'')

    def test_missing_root_filenames_are_reported_and_can_be_mapped(self):
        (self.root/'game/missing.rpy').write_text('image absent = "missing.png"\nlabel audio_test:\n    play music "missing.ogg"\n    "spoken.png"\n    return\n')
        _,project=open_native(self.root)
        entries=project['nativeAssetLibrary']['entries']
        self.assertTrue(any(e['runtime']=={'kind':'file','key':'missing.ogg'} and e['status']=='broken' for e in entries))
        self.assertFalse(any(e['runtime']['key']=='spoken.png' for e in entries))

    def test_external_binding_rejected_and_two_virtual_entries_can_share_resource(self):
        with self.assertRaises(ValueError):self.apply({'operation':'bind','id':self.entry()['id'],'binding':{'kind':'file','key':'../secret.png'}})
        for name in ('笑脸','哭脸'):
            self.apply({'operation':'create','type':'sprite','name':name})
            entry=next(e for e in self.project['nativeAssetLibrary']['entries'] if e['name']==name)
            self.apply({'operation':'bind','id':entry['id'],'binding':{'kind':'file','key':'hero.png'}})
        entries=[e for e in self.project['nativeAssetLibrary']['entries'] if e['name'] in ('笑脸','哭脸')]
        self.assertEqual(len(entries),2);self.assertEqual({e['targetPath'] for e in entries},{'hero.png'})
        self.assertEqual((self.root/'game/hero.png').read_bytes(),b'unchanged image')
