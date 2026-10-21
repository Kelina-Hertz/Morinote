import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


@unittest.skipUnless(os.name=='nt' and shutil.which('powershell.exe'), 'Windows PowerShell required')
class PortableLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='creator-portable-')
        self.root=Path(self.temp.name).resolve()/'中文目录';(self.root/'scripts').mkdir(parents=True)
        shutil.copy2(Path(__file__).resolve().parents[2]/'scripts/start-portable.ps1',self.root/'scripts/start-portable.ps1')
        (self.root/'portable').mkdir();self.archive=self.root/'portable/runtime.zip'
        self.files={'win-unpacked/Morinote IDE.exe':b'fixture executable, never launched', 'win-unpacked/resources/中文.txt':'台词与素材'.encode()}
        self.package()

    def tearDown(self): self.temp.cleanup()

    def package(self):
        with zipfile.ZipFile(self.archive,'w',zipfile.ZIP_STORED) as bundle:
            for name,value in self.files.items():bundle.writestr(name,value)
            bundle.writestr('win-unpacked/padding.bin',b'x'*2048)
        manifest={'archive':self.archive.name,'bytes':self.archive.stat().st_size,'sha256':hashlib.sha256(self.archive.read_bytes()).hexdigest()}
        (self.root/'portable/manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        self.hash=manifest['sha256']

    def start(self):
        return subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.root/'scripts/start-portable.ps1'),'-PrepareOnly'],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)

    def cache(self):return self.root/'.portable'/self.hash[:16]

    def test_first_extract_unicode_and_cached_launch_without_reextract(self):
        result=self.start();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual((self.cache()/'win-unpacked/resources/中文.txt').read_text('utf-8'),'台词与素材')
        sentinel=self.cache()/'sentinel';sentinel.write_text('keep')
        self.assertEqual(self.start().returncode,0);self.assertTrue(sentinel.exists())

    def test_lfs_pointer_and_missing_archive_have_actionable_errors(self):
        self.archive.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:'+'a'*64+'\nsize 2048\n')
        result=self.start();self.assertNotEqual(result.returncode,0);self.assertIn('LFS pointer',result.stdout)
        self.archive.unlink();result=self.start();self.assertNotEqual(result.returncode,0);self.assertIn('git lfs pull',result.stdout)

    def test_same_size_corruption_is_rejected_before_extraction(self):
        data=bytearray(self.archive.read_bytes());data[50]^=1;self.archive.write_bytes(data)
        result=self.start();self.assertNotEqual(result.returncode,0);self.assertIn('checksum',result.stdout)
        self.assertFalse(self.cache().exists())

    def test_interrupted_cache_is_replaced_without_erasing_previous_files(self):
        cache=self.cache();cache.mkdir(parents=True);(cache/'unsaved.txt').write_text('keep')
        result=self.start();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue((cache/'win-unpacked/Morinote IDE.exe').exists())
        self.assertEqual(len(list((self.root/'.portable').glob('incomplete-*/unsaved.txt'))),1)

    def test_malicious_archive_cannot_extract_outside_cache(self):
        self.files['../escape.txt']=b'escape';self.package()
        result=self.start();self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'.portable/escape.txt').exists())

