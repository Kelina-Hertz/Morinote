import json
from pathlib import Path
import tempfile
import unittest

from backend.renpy_import import open_native
from backend.project import load_project
from backend.workspace import read_document,commit,restore,file_tree
from backend import native_config,native_flow,native_stage

SCRIPT='''define e = Character("甲")
image hero = "#aabbcc"
label start:
    e "第一句"
    e "第二句"
    call helper
    menu:
        "A":
            jump route_a
        "B":
            jump route_b
label route_a:
    if score > 0:
        jump finish
    else:
        jump route_b
label route_b:
    while score < 1:
        $ score += 1
    jump finish
label finish:
    return
'''


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'game').mkdir()
        (self.root/'game/story.rpy').write_bytes(b'\xef\xbb\xbf'+SCRIPT.replace('\n','\r\n').encode())
        (self.root/'game/helper.rpy').write_text('label helper:\n    "帮助"\n    return\n',encoding='utf-8')
        (self.root/'game/options.rpy').write_text('define config.name = "中文标题" # keep\ndefine preferences.text_cps = 50\n',encoding='utf-8')
        (self.root/'game/achievements.rpy').write_text('init python:\n    ACHIEVEMENTS = [\n        {"id":"a", "name":"成就甲", "hint":"提示", "condition":lambda: score > 0},\n    ]\n',encoding='utf-8')
        _,self.project=open_native(self.root)

    def tearDown(self):self.temp.cleanup()

    def test_save_preserves_bom_crlf_and_stable_ids_after_insertion(self):
        old=next(s for s in self.project['scenes'] if s['title']=='start')['lines']
        doc=read_document(self.root,'game/story.rpy')
        result=commit(self.root,[{**doc,'content':doc['content'].replace('    e "第一句"','    e "新增"\n    e "第一句"')}],self.project['revision'])
        data=(self.root/'game/story.rpy').read_bytes()
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'));self.assertNotIn(b'\n',data.replace(b'\r\n',b''))
        lines=next(s for s in result['project']['scenes'] if s['title']=='start')['lines']
        self.assertEqual(lines[1]['id'],old[0]['id']);self.assertEqual(lines[2]['id'],old[1]['id'])
        self.assertEqual(len({l['id'] for l in lines}),3)

    def test_external_change_blocks_save_and_undo(self):
        doc=read_document(self.root,'game/story.rpy')
        result=commit(self.root,[{**doc,'content':doc['content'].replace('第一句','改过')}],self.project['revision'])
        (self.root/'game/story.rpy').write_text('label start:\n    "external"\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'外部修改'):commit(self.root,[doc],result['project']['revision'])
        with self.assertRaisesRegex(ValueError,'后续修改'):restore(self.root,result['transaction'],result['project']['revision'])

    def test_invalid_code_keeps_last_index_but_forms_roll_back(self):
        class BadEngine:
            def build(self,*args,**kwargs):raise ValueError('parse error')
        doc=read_document(self.root,'game/story.rpy')
        with self.assertRaisesRegex(ValueError,'未应用'):commit(self.root,[{**doc,'content':'broken'}],self.project['revision'],engine=BadEngine(),strict=True)
        self.assertEqual(read_document(self.root,doc['path'])['hash'],doc['hash'])
        result=commit(self.root,[{**doc,'content':'broken'}],self.project['revision'],engine=BadEngine())
        self.assertFalse(result['project']['sourceStatus']['valid'])
        self.assertEqual(result['project']['scenes'],self.project['scenes'])
        self.assertEqual(read_document(self.root,doc['path'])['content'],'broken')

    def test_native_save_checks_original_source_without_asset_generation(self):
        from unittest.mock import Mock
        engine=Mock()
        engine.build.side_effect=AssertionError('Native source save must not generate a copied game')
        doc=read_document(self.root,'game/story.rpy')
        result=commit(self.root,[{**doc,'content':doc['content'].replace('第一句','更新第一句')}],self.project['revision'],engine=engine)
        self.assertTrue(result['project']['sourceStatus']['valid'])
        engine.check_native.assert_called_once_with(self.root.resolve())
        engine.build.assert_not_called()

    def test_config_field_preserves_lambda_comments_and_shared_buffer(self):
        data=native_config.catalog(self.root,self.project)
        achievement=next(g for g in data['groups'] if g['id']=='achievements')['tables'][0]
        field=next(f for f in achievement['entries'][0]['fields'] if f['name']=='name')
        edit=native_config.edit(self.root,self.project,{'binding':field['id'],'hash':field['hash'],'value':'新的名字'})
        self.assertIn('lambda: score > 0',edit['content'])
        self.assertIn("'新的名字'",edit['content'])
        buffered={**read_document(self.root,edit['path']),'content':edit['content']}
        refreshed=native_config.catalog(self.root,self.project,[buffered])
        nextfield=next(f for f in refreshed['groups'][4]['tables'][0]['entries'][0]['fields'] if f['name']=='hint')
        second=native_config.edit(self.root,self.project,{'binding':nextfield['id'],'hash':nextfield['hash'],'value':'b','documents':[buffered]})
        self.assertIn('新的名字',second['content']);self.assertIn("'b'",second['content'])

    def test_config_append_and_remove_preserve_expressions(self):
        data=native_config.catalog(self.root,self.project);table=data['groups'][4]['tables'][0]
        edit=native_config.edit(self.root,self.project,{'binding':table['id'],'hash':table['hash'],'operation':'append','value':{'id':'b','name':'乙'}})
        result=commit(self.root,[edit],self.project['revision'])
        table=native_config.catalog(self.root,result['project'])['groups'][4]['tables'][0]
        self.assertEqual(len(table['entries']),2)
        entry=table['entries'][0]
        edit=native_config.edit(self.root,result['project'],{'binding':entry['id'],'hash':entry['hash'],'operation':'delete'})
        self.assertIn("'b'",edit['content']);self.assertNotIn('lambda:',edit['content'])

    def test_global_graph_cross_file_calls_options_conditions_and_loops(self):
        flow=native_flow.graph(self.root,self.project)
        self.assertTrue(any(n['title']=='helper' for n in flow['nodes']))
        self.assertTrue({'choice','condition','loop','call','return'} <= {n['type'] for n in flow['nodes']})
        self.assertEqual(len([e for e in flow['edges'] if e['kind']=='option']),2)
        self.assertTrue(any(e['kind']=='return' and e.get('callSite') for e in flow['edges']))
        self.assertTrue(any(e['kind']=='yes' and e['source']==e['target'] for e in flow['edges']))

    def test_audio_split_and_volume_edit_do_not_replay_music(self):
        (self.root/'game/audio/bgm').mkdir(parents=True)
        (self.root/'game/audio/bgm/theme.ogg').write_bytes(b'fixture')
        (self.root/'game/story.rpy').write_text('label start:\n    play music "audio/bgm/theme.ogg" volume 0.5\n    "甲"\n    "乙"\n    return\n',encoding='utf-8')
        _,project=open_native(self.root);scene=next(s for s in project['scenes'] if s['title']=='start');line=scene['lines'][1]
        document=read_document(self.root,'game/story.rpy')
        edited=native_stage.edit(self.root,project,{'path':document['path'],'hash':document['hash'],'line':4,'nodeId':line['id'],'operation':'split_track','track':'audio'})
        self.assertEqual(edited['content'].count('play music'),1)
        self.assertIn('renpy.music.set_volume(1.0',edited['content'])
        result=commit(self.root,[edited],project['revision']);project=result['project']
        cue=next(s for s in project['scenes'] if s['title']=='start')['lines'][1]['audio']['music']
        self.assertEqual(cue['volume'],.5)
        document=read_document(self.root,'game/story.rpy')
        changed=native_stage.edit(self.root,project,{**cue['nativeSource'],'hash':document['hash'],'operation':'audio','channel':'music','property':'volume','value':.8})
        self.assertIn('renpy.music.set_volume(1.6',changed['content'])
        self.assertEqual(changed['content'].count('play music'),1)
        result=commit(self.root,[changed],project['revision'])
        cue=next(s for s in result['project']['scenes'] if s['title']=='start')['lines'][1]['audio']['music']
        self.assertEqual(cue['volume'],.8)

    def test_visual_split_and_effective_zoom_preserve_intrinsic_scale(self):
        (self.root/'game/gui/characters/hero').mkdir(parents=True)
        (self.root/'game/gui/characters/hero/normal.png').write_bytes(b'fixture')
        script='image bg = "#ffffff"\nimage hero:\n    "gui/characters/hero/normal.png"\n    zoom 0.4\nlabel start:\n    scene bg\n    show hero as actor:\n        xpos 200\n        zoom 0.5\n    "甲"\n    "乙"\n    return\n'
        (self.root/'game/story.rpy').write_text(script,encoding='utf-8')
        _,project=open_native(self.root);scene=next(s for s in project['scenes'] if s['title']=='start')
        sprite=scene['lines'][0]['visual']['sprites'][0];self.assertEqual(sprite['scale'],.2)
        document=read_document(self.root,'game/story.rpy')
        changed=native_stage.edit(self.root,project,{**sprite['nativeSource'],'hash':document['hash'],'operation':'property','property':'zoom','value':.6,'effective':True})
        self.assertAlmostEqual(float(__import__('re').findall(r'zoom ([0-9.]+)',changed['content'])[-1]),1.5)
        result=commit(self.root,[changed],project['revision']);project=result['project']
        scene=next(s for s in project['scenes'] if s['title']=='start');line=scene['lines'][1];document=read_document(self.root,'game/story.rpy')
        changed=native_stage.edit(self.root,project,{'path':document['path'],'hash':document['hash'],'line':line['source']['line'],'nodeId':line['id'],'operation':'split_track','track':'visual'})
        result=commit(self.root,[changed],project['revision'])
        after=next(s for s in result['project']['scenes'] if s['title']=='start')['lines'][1]['visual']
        self.assertAlmostEqual(after['sprites'][0]['scale'],.6);self.assertEqual(after['sprites'][0]['x'],200)

    def test_source_tree_cannot_escape_or_expose_internal_files(self):
        (self.root/'.creator/secret').write_text('hidden')
        tree=json.dumps(file_tree(self.root));self.assertNotIn('secret',tree)
        for path in ('../outside.py','.creator/editor/project.json','game/saves/x.json'):
            with self.assertRaises(ValueError):read_document(self.root,path)

    def test_stage_preserves_tag_transform_comment_and_positions(self):
        doc=read_document(self.root,'game/story.rpy')
        text=doc['content'].replace('    e "第一句"','    show hero as existing at leftin_dissolve: # keep\n        xpos 700\n    e "第一句"')
        result=commit(self.root,[{**doc,'content':text}],self.project['revision'])
        doc=read_document(self.root,doc['path'])
        line=next(i+1 for i,r in enumerate(doc['content'].splitlines()) if 'show hero' in r)
        edit=native_stage.edit(self.root,result['project'],{'path':doc['path'],'line':line,'hash':doc['hash'],'operation':'properties','values':{'xpos':900,'ypos':800}})
        self.assertIn('as existing at leftin_dissolve: # keep',edit['content']);self.assertIn('xpos 900',edit['content']);self.assertIn('ypos 800',edit['content'])

    def test_project_session_rejects_stale_work(self):
        from backend.server import Service
        from backend.compiler import sdk_path
        service=Service(sdk_path(),'test');service.root=self.root
        session=service.response()['session'];service.project_session='different'
        with self.assertRaisesRegex(ValueError,'项目已切换'):service.dispatch('/api/workspace/metadata',{'projectSession':session,'revision':self.project['revision'],'ide':{}})

    def test_chat_prefill_retains_advance_semantics(self):
        path=self.root/'game/message.rpy'
        path.write_text('define mc_nvl = Character("我",kind=nvl)\nlabel phone:\n    $ nvl_mode = "phone"\n    nvl_narrator "历史" (interact=False)\n    mc_nvl "消息"\n    return\n',encoding='utf-8')
        _,project=open_native(self.root)
        lines=next(s for s in project['scenes'] if s['title']=='phone')['lines']
        self.assertEqual([l['kind'] for l in lines],['chat','chat']);self.assertFalse(lines[0]['advance']);self.assertTrue(lines[1]['advance'])

    def test_new_file_undo_redo_and_rename_are_reversible(self):
        from backend.workspace import rename
        doc=read_document(self.root,'game/new.rpy')
        result=commit(self.root,[{**doc,'content':'label added:\n    return\n'}],self.project['revision'])
        undone=restore(self.root,result['transaction'],result['project']['revision'])
        self.assertFalse((self.root/'game/new.rpy').exists())
        redone=restore(self.root,result['transaction'],undone['project']['revision'],redo=True)
        renamed=rename(self.root,'game/new.rpy','game/renamed.rpy',read_document(self.root,'game/new.rpy')['hash'],redone['project']['revision'])
        restore(self.root,renamed['transaction'],renamed['project']['revision'])
        self.assertTrue((self.root/'game/new.rpy').exists());self.assertFalse((self.root/'game/renamed.rpy').exists())

    def test_category_cycles_and_duplicate_ids_rejected(self):
        from backend.workspace import validate_metadata
        validate_metadata({'categories':[{'id':'a','name':'立绘','parent':None},{'id':'b','name':'角色','parent':'a'}]})
        for categories in ([{'id':'a','name':'A','parent':'b'},{'id':'b','name':'B','parent':'a'}],[{'id':'a','name':'A','parent':None},{'id':'a','name':'B','parent':None}]):
            with self.assertRaises(ValueError):validate_metadata({'categories':categories})

    def test_native_generation_keeps_missing_references_without_silent_substitution(self):
        from backend.compiler import generate_project
        path=self.root/'game/missing.rpy'
        text='image absent = "gui/characters/hero/absent.png"\nlabel missing:\n    show absent\n    play music "audio/absent.ogg"\n    e "audio/absent.ogg"\n    return\n'
        path.write_text(text,encoding='utf-8');_,doc=open_native(self.root)
        self.assertEqual(len([a for a in doc['assets'] if a['status']=='missing']),2)
        output=self.root/'.creator/test-build';generate_project(self.root,output)
        self.assertEqual((output/'game/missing.rpy').read_text('utf-8'),text)
        self.assertFalse((output/'game/creator_native_placeholders.rpy').exists())
        self.assertEqual(path.read_text('utf-8'),text)

    def test_unlocalized_title_wrapper_is_preserved(self):
        path=self.root/'game/options.rpy';path.write_text('define config.name = _("原名") # comment\n',encoding='utf-8')
        _,project=open_native(self.root)
        field=next(g for g in native_config.catalog(self.root,project)['groups'] if g['id']=='game')['fields'][0]
        edit=native_config.edit(self.root,project,{'binding':field['id'],'hash':field['hash'],'value':'新名'})
        self.assertIn("_('新名') # comment",edit['content'])

    def test_nvl_novel_narrator_is_indexed_without_phone_conversion(self):
        path=self.root/'game/ova.rpy'
        path.write_text('define n = Character(\n    None,kind=nvl)\nlabel novel:\n    $ nvl_mode = "ova"\n    n "小说正文"\n    return\n',encoding='utf-8')
        _,doc=open_native(self.root)
        line=next(s for s in doc['scenes'] if s['title']=='novel')['lines'][0]
        self.assertEqual(line['text'],'小说正文');self.assertEqual(line['kind'],'narration')

    def test_stage_rejects_shifted_statement_instead_of_editing_other_object(self):
        doc=read_document(self.root,'game/story.rpy')
        with self.assertRaisesRegex(ValueError,'位置已变化'):
            native_stage.edit(self.root,self.project,{'path':doc['path'],'line':4,'hash':doc['hash'],'operation':'property','property':'xpos','value':900,'statement':'    show hero'})

    def test_native_auto_override_roundtrip_and_restore(self):
        doc=read_document(self.root,'game/story.rpy');line=next(s for s in self.project['scenes'] if s['title']=='start')['lines'][0]
        operation={'path':doc['path'],'line':4,'nodeId':line['id'],'hash':doc['hash'],'operation':'auto_wait','value':2.5}
        prepared=native_stage.edit(self.root,self.project,operation)
        result=commit(self.root,prepared['edits'],self.project['revision'])
        updated=next(s for s in result['project']['scenes'] if s['title']=='start')['lines'][0]
        self.assertEqual(updated['autoWait'],2.5);self.assertEqual(updated['id'],line['id'])
        edited=read_document(self.root,doc['path']);self.assertIn('(afm=False)',edited['content'])
        reverted=native_stage.edit(self.root,result['project'],{**operation,'hash':edited['hash'],'value':None})
        commit(self.root,[reverted],result['project']['revision'])
        self.assertEqual(read_document(self.root,doc['path'])['content'],doc['content'])

    def test_auto_wait_keeps_hashes_callback_arguments_and_literal_afm_text(self):
        doc=read_document(self.root,'game/story.rpy')
        original=doc['content'].replace('e "第一句"','e "C# afm=False" (cb_args={"note":"#tag"}) # keep')
        result=commit(self.root,[{**doc,'content':original}],self.project['revision'])
        line=next(s for s in result['project']['scenes'] if s['title']=='start')['lines'][0]
        doc=read_document(self.root,doc['path']);op={'path':doc['path'],'line':4,'nodeId':line['id'],'hash':doc['hash'],'operation':'auto_wait','value':.5}
        edits=native_stage.edit(self.root,result['project'],op)['edits'];updated=commit(self.root,edits,result['project']['revision'])
        current=read_document(self.root,doc['path'])
        self.assertIn('cb_args={"note":"#tag"}',current['content'])
        restored=native_stage.edit(self.root,updated['project'],{**op,'hash':current['hash'],'value':None})
        commit(self.root,[restored],updated['project']['revision'])
        self.assertEqual(read_document(self.root,doc['path'])['content'],original)

if __name__=='__main__':unittest.main()
