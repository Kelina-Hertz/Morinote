from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch
from backend.renpy_import import open_native
from backend.project import load_project,project_file,atomic_json
from backend.preview import PreviewManager,Engine


class OriginalLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=(Path(self.temp.name)/'original').resolve();(self.root/'game').mkdir(parents=True)
        self.source=b'\xef\xbb\xbfimage avatar = "gui/missing.png"\r\nlabel start:\r\n    "Original"\r\n    return\r\n'
        (self.root/'game/script.rpy').write_bytes(self.source)
        _,self.project=open_native(self.root)
        self.engine=SimpleNamespace(build=Mock(side_effect=AssertionError('Original launch must not build')),run=Mock(side_effect=AssertionError('Original launch must not compile or lint')),
            environment=lambda output:{'RENPY_SKIP_SPLASHSCREEN':'1','RENPY_PATH_TO_SAVES':str(output/'saves')},command=['fake-python','renpy.py'],sdk=Path(self.temp.name))
        self.process=Mock();self.process.poll.return_value=None;self.process.pid=123
        self.manager=PreviewManager(self.engine,'http://127.0.0.1:1','unused',None)
        self.desktop=patch('backend.preview.interactive_desktop',return_value=True);self.desktop.start()
        self.launch=patch('backend.preview.subprocess.Popen',return_value=self.process);self.Popen=self.launch.start()
    def tearDown(self):self.launch.stop();self.desktop.stop();self.temp.cleanup()
    def test_missing_assets_do_not_block_direct_project_launch(self):
        self.assertTrue(any(a['status']=='missing' for a in self.project['assets']))
        status=self.manager.start(self.root,{'clean':True},mode='play')
        self.assertEqual(self.Popen.call_args.args[0],['fake-python','renpy.py',str(self.root)])
        self.engine.build.assert_not_called();self.engine.run.assert_not_called()
        self.assertTrue(status['runtime']['original']);self.assertEqual(status['status'],'running')
        self.assertEqual(status['output'],str(self.root))
        self.assertEqual((self.root/'game/script.rpy').read_bytes(),self.source)
        self.assertEqual(list((self.root/'game').glob('creator*')),[])
        self.assertEqual([a['status'] for a in load_project(self.root)['assets']],[a['status'] for a in self.project['assets']])
    def test_preserves_menu_splash_and_isolates_saves_without_bridge(self):
        self.manager.start(self.root,{'clean':True})
        env=self.Popen.call_args.kwargs['env']
        self.assertNotIn('RENPY_SKIP_SPLASHSCREEN',env);self.assertNotIn('RENPY_SKIP_MAIN_MENU',env)
        self.assertFalse(any(k.startswith('CREATOR_') for k in env))
        self.assertTrue(Path(env['RENPY_PATH_TO_SAVES']).is_relative_to(self.root/'.creator/original-preview'))
        self.assertFalse((self.root/'game/creator_native_preview.rpy').exists())
    def test_original_does_not_use_test_entry_arguments_or_editor_index_error_gate(self):
        doc=load_project(self.root);doc['sourceStatus']={'valid':False,'message':'stale editor error'};atomic_json(project_file(self.root),doc)
        status=self.manager.start(self.root,{'clean':True,'nativeLabel':'not_a_real_label','args':'bad','state':[],'initialize':'bad'})
        self.assertEqual(status['status'],'running');self.assertEqual(self.manager.session['entry'],{'clean':True})
    def test_original_rejects_edit_commands_and_mode_switches(self):
        self.manager.start(self.root,{'clean':True})
        with self.assertRaisesRegex(ValueError,'原游戏试玩'):self.manager.command('native',{})
        with self.assertRaisesRegex(ValueError,'原游戏试玩'):self.manager.set_mode('edit')
    def test_exit_error_uses_session_log_and_reload_remains_direct(self):
        self.manager.start(self.root,{'clean':True})
        first=self.manager.session['id'];self.manager.reload()
        self.assertNotEqual(self.manager.session['id'],first);self.process.terminate.assert_called_once()
        self.assertTrue(self.manager.session['original']);self.engine.build.assert_not_called()
        Path(self.manager.session['launchLog']).write_text('original engine error',encoding='utf-8')
        self.process.poll.return_value=1
        status=self.manager.status();self.assertEqual(status['status'],'error');self.assertIn('original engine error',status['error'])

    def test_fragment_uses_authored_root_with_external_session_support(self):
        status=self.manager.start(self.root,{'nativeLabel':'start','state':{'flag':True}},'edit')
        self.assertEqual(self.Popen.call_args.args[0][-1],str(self.root))
        env=self.Popen.call_args.kwargs['env']
        support=Path(env['RENPY_SEARCHPATH'])
        self.assertTrue(support.is_relative_to(self.root/'.creator/native-preview'))
        self.assertTrue((support/'creator_native_preview.rpy').is_file())
        self.assertTrue(Path(env['CREATOR_NATIVE_INDEX']).is_file())
        self.assertEqual(status['status'],'starting');self.assertTrue(status['runtime']['direct'])
        self.assertEqual(env['RENPY_SKIP_MAIN_MENU'],'1')
        self.assertEqual((self.root/'game/script.rpy').read_bytes(),self.source)
        self.assertFalse((self.root/'game/creator_native_preview.rpy').exists())
        self.engine.build.assert_not_called();self.engine.run.assert_not_called()
        self.assertEqual(self.manager.session['entry']['scope'],'fragment')

    def test_continue_mode_is_explicit_and_invalid_scope_preserves_preview(self):
        status=self.manager.start(self.root,{'nativeLabel':'start','scope':'continue'})
        self.assertEqual(status['runtime']['scope'],'continue')
        with self.assertRaisesRegex(ValueError,'范围'):self.manager.start(self.root,{'nativeLabel':'start','scope':'other'})
        self.process.terminate.assert_not_called()

    def test_invalid_fragment_setup_preserves_current_preview(self):
        self.manager.start(self.root,{'clean':True})
        for entry in ({'nativeLabel':'unknown'},{'nativeLabel':'start','args':{}},
                      {'nativeLabel':'start','initialize':['missing']},{'nativeLabel':'start','state':{'flag.x':1}}):
            with self.assertRaises(ValueError):self.manager.start(self.root,entry)
        self.assertTrue(self.manager.session['original'])
        self.process.terminate.assert_not_called()

    def test_fragment_rejects_invalid_source_and_bridge_collision(self):
        doc=load_project(self.root);doc['sourceStatus']={'valid':False};atomic_json(project_file(self.root),doc)
        with self.assertRaisesRegex(ValueError,'修复源码'):self.manager.start(self.root,{'nativeLabel':'start'})
        doc['sourceStatus']={'valid':True};atomic_json(project_file(self.root),doc)
        (self.root/'game/creator_native_preview.rpyc').touch()
        with self.assertRaisesRegex(ValueError,'冲突'):self.manager.start(self.root,{'nativeLabel':'start'})
        self.Popen.assert_not_called()

    def test_fragment_ready_reload_and_separate_saves(self):
        self.manager.start(self.root,{'nativeLabel':'start'})
        env=self.Popen.call_args.kwargs['env'];first=self.manager.session['id']
        self.manager.receive(first,'ready',{'native':True})
        self.assertEqual(self.manager.status()['status'],'running')
        self.manager.reload()
        self.assertNotEqual(first,self.manager.session['id'])
        self.assertEqual(self.Popen.call_args.kwargs['env']['RENPY_PATH_TO_SAVES'],env['RENPY_PATH_TO_SAVES'])
        self.assertNotIn('original-preview',env['RENPY_PATH_TO_SAVES'])
        self.engine.build.assert_not_called()

    def test_native_source_check_uses_real_root_and_separate_logs(self):
        engine=object.__new__(Engine);engine.run=Mock(return_value='engine checked')
        result=engine.check_native(self.root,lint=True)
        self.assertEqual(engine.run.call_args_list[0].args,(self.root,))
        self.assertEqual(engine.run.call_args_list[1].args,(self.root,'lint'))
        self.assertEqual(engine.run.call_args.kwargs['log_dir'],self.root/'.creator/checks/native-source')
        self.assertEqual(result['output'],str(self.root))

    def test_direct_engine_compile_errors_are_reported(self):
        self.manager.start(self.root,{'nativeLabel':'start'})
        self.manager.session['startedAt']=0
        (self.root/'errors.txt').write_text('RenPy parse error: script.rpy:4',encoding='utf-8')
        status=self.manager.status()
        self.assertEqual(status['status'],'error');self.assertIn('parse error',status['error'])
