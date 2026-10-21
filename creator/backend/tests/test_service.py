from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

from backend.project import new_project, load_project, save_project
from backend.server import Service, create_server


class FakeEngine:
    def __init__(self, *_): pass


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'project'
        new_project(self.root, '服务测试', True)
        with patch('backend.server.Engine', FakeEngine):
            self.service = Service(Path(self.temp.name), 'test-token')
        self.service.root = self.root
        self.server = create_server(self.service, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def request(self, path, body=None, token='test-token', headers=None):
        request = urllib.request.Request(self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer ' + token,'Content-Type':'application/json', **(headers or {})})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_auth_host_and_cross_origin(self):
        self.assertEqual(self.request('/api/project', token='wrong')[0], 401)
        self.assertEqual(self.request('/api/project', headers={'Origin':'https://example.org'})[0], 401)
        self.assertEqual(self.request('/api/bootstrap', headers={'Sec-Fetch-Site':'cross-site'})[0], 401)
        self.assertEqual(self.request('/api/project')[0], 200)

    def test_save_stale_revision_and_protected_source(self):
        document = load_project(self.root)
        self.assertEqual(self.request('/api/project/save', {'project':document,'revision':document['revision']})[0], 200)
        self.assertEqual(self.request('/api/project/save', {'project':document,'revision':document['revision']})[0], 400)
        revision = load_project(self.root)['revision']
        self.assertEqual(self.request('/api/project/source', {'path':'../outside','content':'x','revision':revision})[0], 400)
        self.assertEqual(self.request('/api/project/source', {'path':'extensions/test.rpy','content':'# x','revision':revision})[0], 200)
        self.assertGreater(load_project(self.root)['revision'], revision)

    def test_runtime_drag_updates_segment_not_new_boundary(self):
        document = load_project(self.root)
        scene = next(s for s in document['scenes'] if s['lines'][0].get('visual', {}).get('sprites'))
        owner = scene['lines'][0]
        target = scene['lines'][1]
        target['visual'] = None
        document = save_project(self.root, document, document['revision'])
        session = {'root':str(self.root),'runtime':{'scene':scene['id'],'line':target['id']},'entry':{},'taskId':None}
        payload = {'revision':document['revision'],'spriteId':owner['visual']['sprites'][0]['id'],'x':777,'y':600}
        result = self.service.runtime_edit(session, payload)['project']
        updated = next(s for s in result['scenes'] if s['id'] == scene['id'])
        self.assertEqual(updated['lines'][0]['visual']['sprites'][0]['x'], 777)
        self.assertIsNone(updated['lines'][1]['visual'])
        with self.assertRaises(ValueError): self.service.runtime_edit(session, payload)

    def test_media_only_registered_and_missing_files_reported(self):
        self.assertEqual(self.request('/api/media?id=unknown')[0], 404)
        self.assertEqual(self.request('/api/project/source?path=project.json')[0], 400)

    def test_project_media_scope_same_ids_and_old_session_rejection(self):
        from urllib.parse import urlencode
        session=self.service.project_session
        first=load_project(self.root)
        asset={'id':'same','name':'同名','path':'assets/same.png','kind':'image','status':'ready'}
        (self.root/asset['path']).write_bytes(b'project-A')
        first['assets'].append(asset.copy());first=save_project(self.root,first,first['revision'])
        second=self.root.parent/'second';new_project(second,'B')
        (second/asset['path']).write_bytes(b'project-B')
        doc=load_project(second);doc['assets'].append(asset.copy());doc=save_project(second,doc,doc['revision'])
        self.service.preview.events=[{'type':'old-event','seq':1}]
        self.service.select_project(second)
        self.assertFalse(self.service.preview.events)
        query=urlencode({'id':'same','projectSession':session,'version':first['revision']})
        self.assertEqual(self.request('/api/media?'+query)[0],400)
        query=urlencode({'id':'same','projectSession':self.service.project_session,'version':doc['revision']})
        req=urllib.request.Request(self.url+'/api/media?'+query,headers={'Authorization':'Bearer test-token'})
        with urllib.request.urlopen(req) as response:self.assertEqual(response.read(),b'project-B')
        self.assertEqual(self.request('/api/media?'+query.replace('version='+str(doc['revision']),'version=999'))[0],409)
        self.assertEqual(self.request('/api/workspace/metadata',{'projectSession':session,'revision':doc['revision'],'ide':{}})[0],400)

    def test_electron_media_token_is_scoped_to_read_only_media(self):
        headers = {'Origin': 'null', 'Sec-Fetch-Site': 'cross-site'}
        # Valid authentication reaches the registered-assets lookup (404),
        # whereas a wrong token is rejected before lookup (401).
        self.assertEqual(self.request('/api/media?id=unknown&token=test-token', token='', headers=headers)[0], 404)
        self.assertEqual(self.request('/api/media?id=unknown&token=wrong', token='', headers=headers)[0], 401)
        self.assertEqual(self.request('/api/project?token=test-token', token='', headers=headers)[0], 401)
        self.assertEqual(self.request('/api/media?token=test-token', {}, token='', headers=headers)[0], 401)


    def test_detect_native_project_and_copy_migrate_without_switching_on_error(self):
        source = Path(self.temp.name) / 'old'
        (source / 'game').mkdir(parents=True)
        (source / 'project.json').write_text('{"packages":["pc"]}')
        (source / 'game/script.rpy').write_text('label start:\n    "Hello"\n    return\n')
        status, info = self.request('/api/project/inspect', {'path': str(source)})
        self.assertEqual((status, info['kind']), (200, 'renpy'))
        status, opened = self.request('/api/project/open', {'path': str(source)})
        self.assertEqual(status, 200, opened)
        self.assertEqual(self.service.root, source.resolve())
        self.assertTrue(opened['project']['nativeRenpy']['inPlace'])
        self.assertEqual((source / 'project.json').read_text(), '{"packages":["pc"]}')
        target = Path(self.temp.name) / 'imported'
        status, response = self.request('/api/project/migrate', {'kind': 'renpy', 'sourceProject': str(source), 'path': str(target), 'title': 'Imported'})
        self.assertEqual(status, 200, response)
        self.assertEqual(response['project']['nativeRenpy']['sourceName'], 'old')
        self.assertEqual((source / 'game/script.rpy').read_text(), 'label start:\n    "Hello"\n    return\n')
        self.assertEqual(self.request('/api/project/reindex', {'revision': 0})[0], 400)
        revision = response['project']['revision']
        self.assertEqual(self.request('/api/project/reindex', {'revision': revision})[0], 200)

