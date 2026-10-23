"""Focused guards for cached read paths; all writes use disposable projects."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from backend.project import load_project, project_file
from backend.renpy_import import open_native, index_sources
from backend.workspace import file_tree, projection, read_document
from backend.server import Service, create_server
from backend.source_literals import literal_eval


class PerformancePaths(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'game').mkdir()
        (self.root / 'game/story.rpy').write_text('default score = 0\nlabel start:\n    "开场"\n    return\n', encoding='utf-8')
        _, self.project = open_native(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_projection_matches_full_index_and_retains_conflict_check(self):
        original = copy.deepcopy(self.project)
        doc = read_document(self.root, 'game/story.rpy')
        doc['content'] = doc['content'].replace('score = 0', 'score = 2').replace('return', 'jump next_scene') + '\nlabel next_scene:\n    "新场景"\n    return\n'
        candidate = projection(self.root, self.project, [doc])
        full = copy.deepcopy(self.project)
        previous = json.loads((self.root / self.project['nativeRenpy']['indexPath']).read_text('utf-8'))
        index_sources(self.root, full, previous=previous, source_contents={doc['path']:doc['content']})
        self.assertEqual(candidate, full)
        self.assertEqual(self.project, original)
        (self.root / doc['path']).write_text('# external edit\n' + doc['content'], encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '外部修改'):
            projection(self.root, self.project, [doc])
        value = literal_eval('[{"a":1}]'); value[0]['a'] = 2
        self.assertEqual(literal_eval('[{"a":1}]'), [{'a':1}])

    def test_tree_skips_tools_but_keeps_game_and_author_folders(self):
        for file in ('creator/electron/main.cjs', 'creator/backend/server.py', 'sdk/renpy.py', 'sdk/lib/unused.txt', 'game/creator/story.rpy', 'custom/story.rpy'):
            target = self.root / file; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('')
        names = {item['name'] for item in file_tree(self.root)}
        self.assertNotIn('creator', names); self.assertNotIn('sdk', names)
        self.assertIn('game', names); self.assertIn('custom', names)

    def test_media_reuses_descriptor_revalidates_and_does_not_lock_edits(self):
        from backend.project import atomic_json
        media = self.root / 'game/picture.png'; media.write_bytes(b'first')
        self.project['assets'].append({'id':'photo','name':'picture','path':'game/picture.png','kind':'image','status':'ready'})
        atomic_json(project_file(self.root), self.project)
        with patch('backend.server.Engine'):
            service = Service(self.root, 'test-token')
        service.root = self.root
        server = create_server(service, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def request(path, **headers):
            return urllib.request.urlopen(urllib.request.Request(base+path, headers={'Authorization':'Bearer test-token', **headers}), timeout=3)
        try:
            with patch('backend.server.load_project', wraps=load_project) as loads:
                with request('/api/media?id=photo') as response:
                    etag = response.headers['ETag']; self.assertEqual(response.read(), b'first')
                with request('/api/preview/status') as response: response.read()
                self.assertEqual(loads.call_count, 1)
                with self.assertRaises(urllib.error.HTTPError) as cached:
                    request('/api/media?id=photo', **{'If-None-Match':etag})
                self.assertEqual(cached.exception.code, 304)
                media.write_bytes(b'second version')
                with request('/api/media?id=photo', **{'If-None-Match':etag}) as response:
                    self.assertNotEqual(response.headers['ETag'], etag)
                    self.assertEqual(response.read(), b'second version')
                updated = copy.deepcopy(self.project); updated['revision'] += 1
                atomic_json(project_file(self.root), updated)
                with request('/api/preview/status') as response:
                    self.assertEqual(json.loads(response.read())['projectRevision'], updated['revision'])
                self.assertEqual(loads.call_count, 2)
            entered, release = threading.Event(), threading.Event()
            def slow(source, *_):
                entered.set(); release.wait(2); return source
            results = []
            def download():
                with request('/api/media?id=photo&thumbnail=320') as response: results.append(response.read())
            with patch('backend.media_cache.thumbnail', side_effect=slow):
                worker = threading.Thread(target=download); worker.start()
                self.assertTrue(entered.wait(2))
                try:
                    self.assertTrue(service.lock.acquire(timeout=.1))
                    service.lock.release()
                    with request('/api/preview/status') as response: self.assertEqual(response.status, 200)
                finally:
                    release.set(); worker.join(3)
                self.assertEqual(results, [b'second version'])
        finally:
            server.shutdown(); server.server_close()


if __name__ == '__main__':
    unittest.main()
