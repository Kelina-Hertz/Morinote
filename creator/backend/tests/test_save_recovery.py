import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from backend.source_merge import merge
from backend import source_transactions as journal


class SaveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root/'game').mkdir()
        self.before = {'game/a.rpy': b'old a', 'game/b.rpy': b'old b'}
        self.after = {'game/a.rpy': b'new a', 'game/b.rpy': b'new b'}
        for name, content in self.before.items(): (self.root/name).write_bytes(content)

    def tearDown(self): self.temp.cleanup()

    def test_interrupted_multifile_save_restores_all_and_keeps_intended_drafts(self):
        journal.begin(self.root, self.before, self.after, [])
        (self.root/'game/a.rpy').write_bytes(self.after['game/a.rpy'])
        journal.recover(self.root)
        for name, content in self.before.items(): self.assertEqual((self.root/name).read_bytes(), content)
        item = journal.notices(self.root)['items'][0]
        self.assertEqual({d['base']['path']: d['value'] for d in item['documents']}, {k:v.decode() for k,v in self.after.items()})
        journal.acknowledge(self.root, [item['id']])
        self.assertFalse(journal.notices(self.root)['items'])
        self.assertTrue((self.root/'.creator/editor/history'/ (item['id']+'.json')).exists())

    def test_external_changes_survive_recovery_and_are_reported(self):
        journal.begin(self.root, self.before, self.after, [])
        (self.root/'game/a.rpy').write_bytes(b'external edit')
        (self.root/'game/b.rpy').write_bytes(self.after['game/b.rpy'])
        journal.recover(self.root)
        self.assertEqual((self.root/'game/a.rpy').read_bytes(), b'external edit')
        self.assertEqual((self.root/'game/b.rpy').read_bytes(), b'old b')
        self.assertEqual(journal.notices(self.root)['items'][0]['conflicts'], ['game/a.rpy'])

    def test_new_file_and_metadata_are_rolled_back_together(self):
        metadata = self.root/'.creator/editor/index.json'
        metadata.parent.mkdir(parents=True); metadata.write_text('{"before":true}')
        record = journal.begin(self.root, {'game/new.rpy':None}, {'game/new.rpy':b'new'}, [metadata])
        (self.root/'game/new.rpy').write_bytes(b'new')
        journal.write_json(self.root, record, metadata, {'after':True})
        journal.recover(self.root)
        self.assertFalse((self.root/'game/new.rpy').exists())
        self.assertEqual(json.loads(metadata.read_text()), {'before':True})
        self.assertFalse(journal.notices(self.root)['items'][0]['documents'][0]['base']['exists'])

    def test_completed_save_is_not_rolled_back(self):
        record=journal.begin(self.root,self.before,self.after,[])
        for name, content in self.after.items(): (self.root/name).write_bytes(content)
        journal.finish(self.root,record,'committed');journal.recover(self.root)
        self.assertEqual((self.root/'game/a.rpy').read_bytes(),b'new a')
        self.assertFalse(journal.notices(self.root)['items'])

    def test_merge_nonoverlap_works_and_conflicting_edits_stay_explicit(self):
        result=merge('a\nb\nc\n','A\nb\nc\n','a\nb\nC\n')['parts']
        self.assertFalse(any(p['conflict'] for p in result))
        self.assertEqual(''.join(p['text'] for p in result),'A\nb\nC\n')
        parts=merge('a\nb\n','a\nlocal\n','a\ndisk\n')['parts']
        conflict=next(p for p in parts if p['conflict'])
        self.assertEqual((conflict['local'],conflict['disk']),('local\n','disk\n'))

    def test_merge_crlf_inserts_deletes_and_identical_edits(self):
        for base,local,disk,want in [('a\r\nb\r\n','a\r\nb\r\nc\r\n','a\r\nb\r\n','a\nb\nc\n'),
                                     ('a\nb\nc\n','a\nc\n','a\nc\n','a\nc\n'),
                                     ('','new','new','new')]:
            parts=merge(base,local,disk)['parts']
            self.assertFalse(any(p['conflict'] for p in parts));self.assertEqual(''.join(p['text'] for p in parts),want)

