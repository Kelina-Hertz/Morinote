import copy
import json
from pathlib import Path
import tempfile
import unittest

from backend.project import load_project, save_project, validate_project, atomic_json
from backend.renpy_import import import_renpy, rendered_sources, reindex_project
from backend.compiler import generate_project

SCRIPT = '''define e = Character("Hero")
define small = 0.4
image bg = "bg.png"
image hero normal:
    "characters/normal.png"
    zoom small
    xanchor 0.5
    yanchor 0.5
    xpos 400
    ypos 400
image hero smile:
    "characters/smile.png"
    zoom small
    xanchor 0.5
    yanchor 0.5
    xpos 400
    ypos 400
label start:
    scene bg
    play music "music.wav" volume 0.4
    show hero normal as hero:
        xpos 250
    show screen legacy_phone
    e "One"
    e "Two"
    show hero smile as hero
    e "Three"
    hide hero
    stop music fadeout 0.5
    e "Four"
    hide screen legacy_phone
    return
screen legacy_phone():
    text "PHONE" xpos 5 ypos 5
'''


class NativeTrackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        game = self.source / 'game'
        (game / 'characters').mkdir(parents=True)
        for name in ('bg.png', 'characters/normal.png', 'characters/smile.png', 'music.wav'):
            (game / name).write_bytes(b'fixture')
        (game / 'script.rpy').write_text(SCRIPT, encoding='utf-8')
        self.root = self.base / 'project'
        self.doc = import_renpy(self.root, self.source)

    def tearDown(self): self.temp.cleanup()

    @property
    def lines(self): return self.doc['scenes'][0]['lines']

    def test_static_tracks_and_expression_keep_outer_position(self):
        a, b, c, d = self.lines
        self.assertEqual(a['visual']['sprites'][0]['scale'], .4)
        self.assertEqual(a['visual']['sprites'][0]['x'], 250)
        self.assertEqual(c['visual']['sprites'][0]['x'], 250)
        self.assertNotEqual(a['visual']['sprites'][0]['asset'], c['visual']['sprites'][0]['asset'])
        self.assertEqual(a['visual']['sprites'][0]['id'], c['visual']['sprites'][0]['id'])
        self.assertIsNone(b['visual']); self.assertIsNone(b['audio'])
        self.assertEqual(a['audio']['music']['volume'], .4)
        self.assertEqual(d['visual']['sprites'], [])
        self.assertEqual(d['audio']['music']['asset'], '')
        self.assertFalse([d for d in validate_project(self.doc, self.root) if d['severity'] == 'error'])

    def test_no_edits_preserve_exact_source_and_opaque_screen(self):
        self.assertEqual(rendered_sources(self.root, self.doc)['extensions/renpy/script.rpy'], SCRIPT)





    def test_old_native_project_upgrades_without_reimporting_assets(self):
        self.doc['nativeRenpy'].pop('trackVersion')
        for line in self.lines: line.update(visual=None, audio=None)
        index = json.loads((self.root / 'sources/renpy-index.json').read_text(encoding='utf-8'))
        index['scenes'] = copy.deepcopy(self.doc['scenes'])
        atomic_json(self.root / 'sources/renpy-index.json', index)
        atomic_json(self.root / 'project.json', self.doc)
        upgraded = load_project(self.root)
        self.assertEqual(upgraded['nativeRenpy']['trackVersion'], 2)
        self.assertIsNotNone(upgraded['scenes'][0]['lines'][0]['visual'])
        self.assertTrue((self.root / '.creator/migrations/native-tracks-v2/project.json').exists())
        self.assertEqual(load_project(self.root)['revision'], upgraded['revision'])

    def test_unknown_expression_is_visible_and_source_kept(self):
        path = self.root / 'extensions/renpy/script.rpy'
        path.write_text(SCRIPT.replace('scene bg', 'scene expression choose_background()'), encoding='utf-8')
        self.doc = reindex_project(self.root, self.doc)
        self.assertIn('未解析', self.lines[0]['visual']['nativeUnknown'][0])
        self.assertIn('scene expression choose_background()', rendered_sources(self.root, self.doc)['extensions/renpy/script.rpy'])

    def test_entrance_preview_uses_settled_offset_not_initial_offset(self):
        path = self.root / 'extensions/renpy/script.rpy'
        path.write_text('transform enter:\n    xoffset -150\n    parallel:\n        easein 0.6 xoffset 0\n' + SCRIPT.replace('show hero normal as hero:', 'show hero normal as hero at enter:'), encoding='utf-8')
        self.doc = reindex_project(self.root, self.doc)
        self.assertEqual(self.lines[0]['visual']['sprites'][0]['x'], 250)
        self.assertTrue(self.lines[0]['source']['trackNotes'])


    def test_tracks_cannot_silently_replace_source_staging(self):
        self.lines[0]['visual']['sprites'][0]['x'] = 300
        with self.assertRaisesRegex(ValueError, '原 RPY'):
            save_project(self.root, self.doc, 1)
        self.assertEqual((self.root / 'extensions/renpy/script.rpy').read_text(encoding='utf-8'), SCRIPT)

    def test_text_save_updates_rpy_and_projection_ids_stay_stable(self):
        ids = [line['id'] for line in self.lines]
        self.lines[1]['text'] = 'Saved to source'
        self.doc = save_project(self.root, self.doc, 1)
        self.assertIn('e "Saved to source"', (self.root / 'extensions/renpy/script.rpy').read_text(encoding='utf-8'))
        self.assertEqual(ids, [line['id'] for line in self.lines])
        self.assertEqual((self.source / 'game/script.rpy').read_text(encoding='utf-8'), SCRIPT)

    def test_unedited_game_code_is_byte_identical_and_no_staging_runtime(self):
        path = self.root / 'extensions/renpy/script.rpy'
        path.write_bytes(b'\xef\xbb\xbf' + SCRIPT.replace('\n', '\r\n').encode('utf-8'))
        result = generate_project(self.root, self.base / 'build', preview=True)
        game = self.base / 'build/game'
        self.assertEqual((game / 'script.rpy').read_bytes(), path.read_bytes())
        self.assertFalse((game / 'creator_native_tracks.rpy').exists())
        self.assertFalse((game / 'creator_native_preview.rpy').exists())
        self.assertNotIn('config.developer', (game / 'creator_native_config.rpy').read_text(encoding='utf-8'))
        self.assertTrue(result['native'])

    def test_full_preview_keeps_original_menu_and_splash_without_bridge(self):
        from types import SimpleNamespace
        from unittest.mock import patch, Mock
        from backend.preview import PreviewManager
        output = self.base / 'preview'
        (output / 'game').mkdir(parents=True)
        engine = SimpleNamespace(build=lambda *a, **kw: {'output':str(output), 'revision':1, 'native':True, 'nativeLabel':'start'},
            run=lambda *a, **kw:None, environment=lambda *a:{'RENPY_SKIP_SPLASHSCREEN':'1'}, command=['fake-python'], sdk=self.base)
        process = Mock();process.poll.return_value=None;process.pid=123
        manager = PreviewManager(engine, 'http://127.0.0.1:1', 'test', lambda *a:None)
        with patch('backend.preview.interactive_desktop', return_value=True), patch('backend.preview.subprocess.Popen', return_value=process) as launch:
            result = manager.start(self.root)
        env = launch.call_args.kwargs['env']
        self.assertNotIn('RENPY_SKIP_SPLASHSCREEN',env)
        self.assertNotIn('RENPY_SKIP_MAIN_MENU',env)
        self.assertFalse((output / 'game/creator_native_preview.rpy').exists())
        self.assertEqual(result['status'],'running')


if __name__ == '__main__': unittest.main()
