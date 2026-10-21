from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from backend.compiler import generate_project
from backend.project import load_project, save_project
from backend.renpy_import import import_renpy, reindex_project, rendered_sources

SCRIPT = '''define e = Character("Eileen")
default visits = 0
label start:
    $ visits += 1
    show screen legacy_phone
    "Before" # original comment
    hide screen legacy_phone
    python:
        secret = "Python string is not dialogue"
    e "A quote: \\"hi\\""
    menu:
        "Left":
            jump left
        "Right":
            jump right
label left:
    e "Left path"
    call helper
    jump finish
label right:
    e "Right path"
    jump finish
label helper:
    e "Helper"
    return
label finish:
    e "Done [visits]"
    return
screen legacy_phone():
    text "PHONE" xpos 5 ypos 5
'''


class RenpyImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / 'old'
        game = self.source / 'game'
        game.mkdir(parents=True)
        (self.source / 'project.json').write_text('{"packages":["pc"]}')
        (game / 'script.rpy').write_text(SCRIPT, encoding='utf-8')
        (game / 'options.rpy').write_text('define config.name = "Native fixture"\n', encoding='utf-8')
        self.target = self.base / 'new'

    def tearDown(self):
        self.temp.cleanup()

    def test_import_is_a_real_independent_copy_and_preserves_opaque_code(self):
        before = (self.source / 'game/script.rpy').read_bytes()
        doc = import_renpy(self.target, self.source)
        self.assertEqual((self.target / 'extensions/renpy/script.rpy').read_bytes(), before)
        self.assertEqual((self.target / 'sources/renpy-original/script.rpy').read_bytes(), before)
        self.assertEqual(len(doc['nativeRenpy']['labels']), 5)
        texts = [l['text'] for s in doc['scenes'] for l in s['lines']]
        self.assertIn('Before', texts)
        self.assertNotIn('Left', texts)
        self.assertNotIn('Python string is not dialogue', texts)
        self.assertNotIn('PHONE', texts)
        self.assertTrue(any(e['kind'] == 'call' and e['targetLabel'] == 'helper' for e in doc['nativeRenpy']['edges']))
        (self.target / 'extensions/renpy/script.rpy').write_text('# changed', encoding='utf-8')
        self.assertEqual((self.source / 'game/script.rpy').read_bytes(), before)

    def test_edit_only_patches_literal_not_execution_or_comments(self):
        doc = import_renpy(self.target, self.source)
        original = (self.target / 'extensions/renpy/script.rpy').read_text(encoding='utf-8')
        line = doc['scenes'][0]['lines'][0]
        line['text'] = 'Edited "quote"\nnext'
        doc = save_project(self.target, doc, 1)
        result = generate_project(self.target, self.base / 'build', preview=True)
        actual = (self.base / 'build/game/script.rpy').read_text(encoding='utf-8')
        expected = original.replace('"Before" # original comment', json.dumps(line['text']) + ' # original comment')
        self.assertEqual(actual, expected)
        self.assertTrue(result['native'])
        self.assertEqual((self.source / 'game/script.rpy').read_text(encoding='utf-8'), original)
        self.assertFalse((self.base / 'build/game/generated/creator_story.rpy').exists())

    def test_structure_cannot_silently_override_original_game(self):
        doc = import_renpy(self.target, self.source)
        doc['scenes'][0]['lines'].append(copy.deepcopy(doc['scenes'][0]['lines'][0]))
        with self.assertRaisesRegex(ValueError, '只回写'):
            save_project(self.target, doc, 1)
        doc = load_project(self.target)
        doc['graphs'][0]['nodes'][0]['next'] = doc['graphs'][0]['nodes'][1]['id']
        with self.assertRaisesRegex(ValueError, '源码索引'):
            save_project(self.target, doc, 1)

    def test_source_and_text_conflict_stops_instead_of_overwriting_code(self):
        doc = import_renpy(self.target, self.source)
        doc['scenes'][0]['lines'][0]['text'] = 'Editor change'
        path = self.target / 'extensions/renpy/script.rpy'
        path.write_text(path.read_text().replace('Before', 'Source change'))
        with self.assertRaisesRegex(ValueError, '冲突'):
            rendered_sources(self.target, doc)
        self.assertIn('Source change', path.read_text())

    def test_reindex_commits_pending_text_and_indexes_new_code(self):
        doc = import_renpy(self.target, self.source)
        doc['scenes'][0]['lines'][0]['text'] = 'Editor change'
        path = self.target / 'extensions/renpy/script.rpy'
        path.write_text(path.read_text() + '\nlabel added:\n    "Added"\n    return\n')
        doc = reindex_project(self.target, doc)
        self.assertIn('Editor change', path.read_text())
        self.assertTrue(any(l['name'] == 'added' for l in doc['nativeRenpy']['labels']))
        self.assertIn('Before', (self.target / 'sources/renpy-original/script.rpy').read_text())

    def test_target_protection_and_unsupported_sources(self):
        for target in (self.source, self.source / 'nested', self.base):
            with self.assertRaises(ValueError): import_renpy(target, self.source)
        self.target.mkdir()
        (self.target / 'keep.txt').write_text('keep')
        with self.assertRaises(ValueError): import_renpy(self.target, self.source)
        self.assertEqual((self.target / 'keep.txt').read_text(), 'keep')

    def test_selecting_game_subfolder_still_protects_whole_original_project(self):
        with self.assertRaisesRegex(ValueError, '原工程之外'):
            import_renpy(self.source / 'new', self.source / 'game')
        doc = import_renpy(self.target, self.source / 'game')
        self.assertEqual(doc['nativeRenpy']['sourceName'], 'old')

    def test_excludes_authoring_psd_and_saves_but_copies_runtime_resources(self):
        game = self.source / 'game'
        (game / 'saves').mkdir()
        (game / 'saves/test.save').write_bytes(b'private save')
        (game / 'art.psd').write_bytes(b'authoring')
        (game / 'font.ttf').write_bytes(b'font')
        doc = import_renpy(self.target, self.source)
        self.assertIn('art.psd', doc['nativeRenpy']['excluded'])
        self.assertIn('saves/test.save', doc['nativeRenpy']['excluded'])
        generate_project(self.target, self.base / 'build')
        self.assertEqual((self.base / 'build/game/font.ttf').read_bytes(), b'font')
        self.assertFalse((self.base / 'build/game/art.psd').exists())

    def test_project_error_explains_native_import(self):
        with self.assertRaisesRegex(ValueError, '打包配置'):
            load_project(self.source)

    def test_new_extension_and_resource_survive_generation_and_reindex(self):
        doc = import_renpy(self.target, self.source)
        code = self.target / 'extensions/added.rpy'
        code.write_text('label new_component:\n    "Added"\n    return\n', encoding='utf-8')
        asset = self.target / 'assets/new.png'
        asset.parent.mkdir(exist_ok=True)
        asset.write_bytes(b'new image')
        doc['assets'].append({'id': 'added', 'kind': 'image', 'name': 'added', 'status': 'ready', 'path': 'assets/new.png'})
        doc = save_project(self.target, doc, 1)
        generate_project(self.target, self.base / 'build')
        self.assertEqual((self.base / 'build/game/extensions/added.rpy').read_text(), code.read_text())
        self.assertEqual((self.base / 'build/game/assets/new.png').read_bytes(), asset.read_bytes())
        doc = reindex_project(self.target, doc)
        self.assertTrue(any(l['name'] == 'new_component' for l in doc['nativeRenpy']['labels']))


if __name__ == '__main__':
    unittest.main()
