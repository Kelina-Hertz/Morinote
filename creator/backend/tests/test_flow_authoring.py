"""Focused source-editing checks; no engine, UI launch or production-game writes."""
import copy
from pathlib import Path
import tempfile
import unittest

from backend.native_flow import graph, edit
from backend.renpy_import import open_native
from backend.workspace import commit, projection, restore
from backend.flow_authoring import digest, PENDING_OUTLET


class FlowAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'game').mkdir()
        self.load('label start:\n    jump a\nlabel a:\n    call helper\n    "A"\n    jump b # retain\nlabel helper:\n    return\nlabel b:\n    "B"\n    return\nlabel spare:\n    return\n')

    def tearDown(self):
        self.temp.cleanup()

    def load(self, text):
        (self.root/'game/story.rpy').write_text(text,encoding='utf-8')
        _,self.project=open_native(self.root)
        self.flow=graph(self.root,self.project)

    def label(self, name, project=None):
        return next(l['id'] for l in (project or self.project)['nativeRenpy']['labels'] if l['name']==name)

    def point(self, name, flow=None):
        view=flow or self.flow
        node=next(n for n in view['nodes'] if n['id']==self.label(name))
        return view['authoring']['points'][node['editPoint']]

    def request(self, point, operation, flow=None, **data):
        hashes=copy.deepcopy((flow or self.flow)['authoring']['documents'])
        hashes.setdefault('game/creator_scenes.rpy',{'hash':digest(''),'contentHash':digest('')})
        return {'operation':operation,'point':point['id'],'hashes':hashes,**data}

    def scene(self, name='scene_added', path='game/creator_scenes.rpy'):
        return {'name':name,'title':'新剧情','group':'第一章','path':path}

    def test_numbered_default_connects_only_selected_sources(self):
        self.load('label start:\n    jump a\nlabel a:\n    return\nlabel helper:\n    return\nlabel original_only:\n    return\n')
        copy_text='label start:\n    call helper\n    jump a\nlabel helper:\n    return\nlabel a:\n    "Selected"\n    return\n'
        (self.root/'game/story (1).rpy').write_text(copy_text,encoding='utf-8')
        (self.root/'game/target.rpy').write_text('label b:\n    "Original"\n    return\n',encoding='utf-8')
        (self.root/'game/target (1).rpy').write_text('label b:\n    "Selected target"\n    return\n',encoding='utf-8')
        _,project=open_native(self.root)
        view=graph(self.root,project)
        def label(name,file):return next(l['id'] for l in project['nativeRenpy']['labels'] if l['name']==name and l['file']==file)
        a,b=label('a','story (1).rpy'),label('b','target (1).rpy')
        original_a=label('a','story.rpy')
        points=view['authoring']['points']
        node=next(n for n in view['nodes'] if n['id']==a)
        point=points[node['editPoint']]
        self.assertEqual(point['source']['path'],'game/story (1).rpy')
        self.assertFalse(next(t['reason'] for t in view['authoring']['targets'] if t['id']==b))
        self.assertTrue(next(t['reason'] for t in view['authoring']['targets'] if t['id']==original_a))
        self.assertFalse(next(n for n in view['nodes'] if n['id']==original_a).get('editPoint'))
        self.assertIn(label('original_only','story.rpy'),{n['id'] for n in view['story']['nodes']})
        self.assertEqual(view['authoring']['reachability'][a],'reachable')
        original_helper=label('helper','story.rpy')
        old_returns={n['id'] for n in view['nodes'] if n['label']==original_helper and n['type']=='return'}
        self.assertFalse(any(e['source'] in old_returns and e['kind']=='return' for e in view['edges']))
        entry=next(g for g in project['graphs'] if g['id']==project['entryGraph'])['entry']
        self.assertEqual(entry,label('start','story (1).rpy'))
        before={p.name:p.read_bytes() for p in (self.root/'game').glob('*.rpy')}
        request=self.request(point,'connect_exit',view,target=b)
        result=edit(self.root,project,request)
        self.assertEqual([d['path'] for d in result['edits']],['game/story (1).rpy'])
        self.assertIn('jump b',result['edits'][0]['content'])
        candidate=projection(self.root,project,result['edits'])
        updated=graph(self.root,candidate,result['edits'])
        self.assertEqual(updated['authoring']['reachability'][b],'reachable')
        self.assertTrue(any(e['target']==b and e['kind']=='jump' for e in updated['edges']))
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'game').glob('*.rpy')})
        (self.root/'game/target (1).rpy').write_text('label b:\n    "External"\n    return\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'变化'):edit(self.root,project,request)

    def test_numbered_default_keeps_unrelated_duplicates_read_only(self):
        self.load('label start:\n    return\nlabel a:\n    return\n')
        (self.root/'game/story (1).rpy').write_text('label start:\n    return\nlabel a:\n    return\n',encoding='utf-8')
        (self.root/'game/unrelated.rpy').write_text('label a:\n    return\n',encoding='utf-8')
        _,project=open_native(self.root)
        view=graph(self.root,project)
        for item in project['nativeRenpy']['labels']:
            if item['name']=='a' and item['file']!='story.rpy':
                self.assertIn('重复',next(t['reason'] for t in view['authoring']['targets'] if t['id']==item['id']))
                self.assertFalse(next(n for n in view['nodes'] if n['id']==item['id']).get('editPoint'))

    def canvas_operation(self, operation, **data):
        sources=getattr(self,'canvas_sources',{})
        candidate=projection(self.root,self.project,list(sources.values()))
        view=graph(self.root,candidate,list(sources.values()))
        hashes=copy.deepcopy(view['authoring']['documents'])
        hashes.setdefault('game/creator_scenes.rpy',{'hash':digest(''),'contentHash':digest('')})
        result=edit(self.root,candidate,{'operation':operation,'hashes':hashes,'documents':list(sources.values()),**data})
        sources.update({d['path']:d for d in result['edits']});self.canvas_sources=sources
        updated=projection(self.root,self.project,list(sources.values()))
        return graph(self.root,updated,list(sources.values())),updated,result

    def test_free_choice_block_ports_rename_connect_and_disconnect(self):
        before=(self.root/'game/story.rpy').read_bytes()
        view,project,_=self.canvas_operation('create_block',kind='choice',scene=self.scene(),options=['接受邀请','拒绝邀请'])
        owner=self.label('scene_added',project)
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        self.assertEqual(block['blockKind'],'choice');self.assertEqual(len(block['optionPoints']),2)
        self.assertEqual([n['id'] for n in view['story']['nodes'] if n['label']==owner],[owner])
        view,project,_=self.canvas_operation('connect_exit',point=block['optionPoints'][0],target=self.label('b'))
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        view,project,_=self.canvas_operation('rename_option',point=block['optionPoints'][0],text='同意邀请')
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        self.assertEqual(view['authoring']['points'][block['optionPoints'][0]]['title'],'同意邀请')
        self.assertTrue(any(e['source']==owner and e['target']==self.label('b') for e in view['story']['edges']))
        view,project,_=self.canvas_operation('connect_exit',point=block['optionPoints'][1],target=self.label('a'))
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        view,_,result=self.canvas_operation('disconnect_exits',points=block['optionPoints'])
        self.assertEqual(len(result['edits']),1)
        self.assertFalse(any(e['source']==owner for e in view['story']['edges']))
        self.assertEqual((self.root/'game/story.rpy').read_bytes(),before)
        self.assertFalse((self.root/'game/creator_scenes.rpy').exists())

    def test_condition_block_ports_edit_and_source_metadata_roundtrip(self):
        view,project,_=self.canvas_operation('create_block',kind='condition',scene=self.scene(),condition='score >= 3')
        owner=self.label('scene_added',project)
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        self.assertEqual(block['blockKind'],'condition')
        self.assertEqual([view['authoring']['points'][p]['title'] for p in block['optionPoints']],['是','否'])
        view,project,_=self.canvas_operation('connect_exit',point=block['optionPoints'][0],target=self.label('b'))
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        view,project,_=self.canvas_operation('update_condition',point=block['conditionPoint'],condition='score > 5')
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        self.assertEqual(block['conditionExpression'],'score > 5')
        self.assertTrue(any(e['source']==owner and e['target']==self.label('b') and e['kind']=='yes' for e in view['story']['edges']))
        commit(self.root,list(self.canvas_sources.values()),self.project['revision'])
        _,reopened=open_native(self.root)
        self.assertEqual(next(l['blockKind'] for l in reopened['nativeRenpy']['labels'] if l['id']==owner),'condition')

    def test_drag_create_preserves_old_continuation_for_all_block_types(self):
        for kind in ('scene','choice','condition'):
            with self.subTest(kind=kind):
                self.canvas_sources={}
                view,project,result=self.canvas_operation('create_block',kind=kind,point=self.point('a')['id'],scene=self.scene(),options=['继续','新方向'],condition='flag')
                self.assertEqual(len(result['edits']),2)
                content=self.canvas_sources['game/story.rpy']['content']
                self.assertIn('call helper',content);self.assertIn('jump scene_added # retain',content)
                created=self.canvas_sources['game/creator_scenes.rpy']['content']
                self.assertIn('jump b',created)
                if kind!='scene':self.assertTrue(created.endswith('return'+PENDING_OUTLET+'\n'))
                self.assertEqual(next(n['reachability'] for n in view['nodes'] if n['id']==self.label('scene_added',project)),'reachable')

    def test_unsafe_canvas_condition_and_partial_disconnect_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'函数调用'):
            self.canvas_operation('create_block',kind='condition',scene=self.scene(),condition='renpy.jump("b")')
        self.assertFalse((self.root/'game/creator_scenes.rpy').exists())
        with self.assertRaises(ValueError):
            self.canvas_operation('disconnect_exits',points=[self.point('a')['id'],'missing'])
        self.assertIn('jump b # retain',(self.root/'game/story.rpy').read_text('utf-8'))

    def test_insert_existing_scene_merges_same_file_edits_and_undo(self):
        before=(self.root/'game/story.rpy').read_bytes()
        result=edit(self.root,self.project,self.request(self.point('a'),'insert_existing',scene=self.label('spare'),scenePoint=self.point('spare')['id']))
        self.assertEqual(len(result['edits']),1)
        content=result['edits'][0]['content']
        self.assertIn('jump spare # retain',content)
        self.assertIn('label spare:\n    jump b',content.replace('\r\n','\n'))
        self.assertIn('call helper',content)
        saved=commit(self.root,result['edits'],self.project['revision'])
        restore(self.root,saved['transaction'],saved['project']['revision'])
        self.assertEqual((self.root/'game/story.rpy').read_bytes(),before)

    def test_insert_existing_scene_across_files_and_ending(self):
        view,project,_=self.canvas_operation('create_block',kind='scene',scene=self.scene())
        block=next(n for n in view['nodes'] if n['id']==self.label('scene_added',project))
        view,_,result=self.canvas_operation('insert_existing',point=self.point('a')['id'],scene=block['id'],scenePoint=block['editPoint'])
        self.assertEqual(len(result['edits']),2)
        self.assertIn('jump b',self.canvas_sources['game/creator_scenes.rpy']['content'])
        self.load('label start:\n    return\nlabel spare:\n    return # keep\n')
        result=edit(self.root,self.project,self.request(self.point('start'),'insert_existing',scene=self.label('spare'),scenePoint=self.point('spare')['id']))
        self.assertIn('jump spare',result['edits'][0]['content'])
        self.assertIn('return # keep',result['edits'][0]['content'])

    def test_insert_existing_rejects_connected_complex_cyclic_or_stale_scene(self):
        request=self.request(self.point('a'),'insert_existing',scene=self.label('b'),scenePoint=self.point('b')['id'])
        with self.assertRaises(ValueError):edit(self.root,self.project,request)
        self.load('label start:\n    jump a\nlabel a:\n    return\nlabel spare:\n    call a\n    return\n')
        with self.assertRaisesRegex(ValueError,'循环'):
            edit(self.root,self.project,self.request(self.point('a'),'insert_existing',scene=self.label('spare'),scenePoint=self.point('spare')['id']))
        self.load('label start:\n    return\nlabel spare:\n    return\n')
        request=self.request(self.point('start'),'insert_existing',scene=self.label('spare'),scenePoint='outdated')
        with self.assertRaises(ValueError):edit(self.root,self.project,request)
        request['scenePoint']=self.point('spare')['id']
        (self.root/'game/story.rpy').write_text('label start:\n    return\nlabel spare:\n    "external"\n    return\n',encoding='utf-8')
        with self.assertRaises(ValueError):edit(self.root,self.project,request)

    def test_insert_cross_file_preserves_continuation_call_comments_and_atomic_undo(self):
        before=(self.root/'game/story.rpy').read_bytes()
        point=self.point('a')
        projected=next(e for e in self.flow['story']['edges'] if e['source']==self.label('a'))
        self.assertEqual(projected['editPoint'],point['id'])
        result=edit(self.root,self.project,self.request(point,'insert_after',scene=self.scene()))
        by_path={d['path']:d['content'].replace('\r\n','\n') for d in result['edits']}
        self.assertIn('    call helper\n    "A"\n    jump scene_added # retain',by_path['game/story.rpy'])
        self.assertTrue(by_path['game/creator_scenes.rpy'].endswith('    jump b\n'))
        self.assertEqual((self.root/'game/story.rpy').read_bytes(),before)
        saved=commit(self.root,result['edits'],self.project['revision'])
        reverted=restore(self.root,saved['transaction'],saved['project']['revision'])
        self.assertEqual((self.root/'game/story.rpy').read_bytes(),before)
        self.assertFalse((self.root/'game/creator_scenes.rpy').exists())
        redone=restore(self.root,saved['transaction'],reverted['project']['revision'],redo=True)
        self.assertTrue(any(l['name']=='scene_added' for l in redone['project']['nativeRenpy']['labels']))

    def test_insert_return_fallthrough_and_same_file(self):
        for ending in ('    return\n','    "fallthrough"\n'):
            with self.subTest(ending=ending):
                self.load('label start:\n'+ending+'label after:\n    return\n')
                result=edit(self.root,self.project,self.request(self.point('start'),'insert_after',scene=self.scene(path='game/story.rpy')))
                self.assertEqual(len(result['edits']),1)
                content=result['edits'][0]['content']
                self.assertIn('jump scene_added',content)
                self.assertTrue(content.endswith('    return\n') if 'return' in ending else content.endswith('    jump after\n'))

    def test_branch_preserves_original_route_and_new_scene_ends_independently(self):
        operation=self.request(self.point('a'),'branch_exit',options=[
            {'text':'继续原剧情','destination':{'kind':'existing','label':self.label('b')}},
            {'text':'拒绝邀请','destination':{'kind':'new','scene':self.scene()}}])
        result=edit(self.root,self.project,operation)
        by_path={d['path']:d['content'].replace('\r\n','\n') for d in result['edits']}
        self.assertLess(by_path['game/story.rpy'].index('"A"'),by_path['game/story.rpy'].index('menu: # retain'))
        self.assertIn("'继续原剧情':\n            jump b",by_path['game/story.rpy'])
        self.assertTrue(by_path['game/creator_scenes.rpy'].endswith('    return'+PENDING_OUTLET+'\n'))
        self.assertNotIn('jump b',by_path['game/creator_scenes.rpy'])
        candidate=projection(self.root,self.project,result['edits'])
        flow=graph(self.root,candidate,result['edits'])
        menu=next(n for n in flow['nodes'] if n.get('branchPoint'))
        append=self.request(flow['authoring']['points'][menu['branchPoint']],'branch_exit',flow,documents=result['edits'],options=[{'text':'结束','destination':{'kind':'return'}}])
        updated=edit(self.root,candidate,append)
        changed=next(d['content'].replace('\r\n','\n') for d in updated['edits'] if d['path']=='game/story.rpy')
        self.assertIn("'继续原剧情':\n            jump b",changed)
        self.assertLess(changed.index("'拒绝邀请':"),changed.index("'结束':"))

    def test_connect_specific_option_preserves_other_branches_and_allows_cycles(self):
        self.load('label start:\n    "A"\n    menu:\n        "Left": # header\n            jump b # left\n        "Right":\n            return # right\nlabel b:\n    return\n')
        menu=next(n for n in self.flow['nodes'] if n.get('optionPoints'))
        point=self.flow['authoring']['points'][menu['optionPoints'][0]]
        edge=next(e for e in self.flow['story']['edges'] if e.get('editPoint')==point['id'])
        self.assertEqual(edge['source'],menu['id'])
        result=edit(self.root,self.project,self.request(point,'connect_exit',target=self.label('start')))
        content=result['edits'][0]['content']
        self.assertIn('jump start # left',content);self.assertIn('return # right',content);self.assertIn('"Left": # header',content)
        candidate=projection(self.root,self.project,result['edits'])
        self.assertEqual(graph(self.root,candidate,result['edits'])['authoring']['reachability'][self.label('b')],'disconnected')

    def test_unsafe_exits_targets_and_changed_sources_are_rejected_without_writes(self):
        for body in ('    jump expression destination\n','    if flag:\n        return\n    jump b\n','    python:\n        renpy.jump("b")\n    return\n','    return score\n'):
            with self.subTest(body=body):
                self.load('label start:\n'+body+'label b:\n    return\n')
                node=next(n for n in self.flow['nodes'] if n['id']==self.label('start'))
                self.assertFalse(node.get('editPoint'));self.assertTrue(node['blockedReason'])
        self.load('label start:\n    return\nlabel b(required):\n    return\n')
        with self.assertRaisesRegex(ValueError,'参数'):
            edit(self.root,self.project,self.request(self.point('start'),'connect_exit',target=self.label('b')))
        request=self.request(self.point('start'),'connect_exit',target=self.label('start'))
        (self.root/'game/story.rpy').write_text('label start:\n    "external"\n    return\n',encoding='utf-8')
        with self.assertRaises(ValueError):edit(self.root,self.project,request)
        self.assertFalse((self.root/'game/creator_scenes.rpy').exists())
        self.load('label start:\n    return\nlabel b:\n    return\nlabel b:\n    return\n')
        self.assertTrue(next(t['reason'] for t in self.flow['authoring']['targets'] if t['id']==self.label('b')))

    def test_reachability_does_not_fan_shared_returns_into_other_callers(self):
        self.load('label start:\n    call helper\n    jump a\nlabel unreachable:\n    call helper\n    jump spare\nlabel helper:\n    return\nlabel a:\n    return\nlabel spare:\n    return\n')
        status=self.flow['authoring']['reachability']
        self.assertEqual(status[self.label('helper')],'reachable')
        self.assertEqual(status[self.label('a')],'reachable')
        self.assertEqual(status[self.label('spare')],'disconnected')
        self.load('label start:\n    jump expression destination\nlabel spare:\n    return\n')
        self.assertEqual(self.flow['authoring']['reachability'][self.label('spare')],'unknown')
        self.load('label start:\n    return\nlabel start:\n    return\nlabel spare:\n    return\n')
        self.assertTrue(all(v=='unknown' for v in self.flow['authoring']['reachability'].values()))
        self.load('label start:\n    show screen navigation\n    return\nlabel spare:\n    return\n')
        self.assertEqual(self.flow['authoring']['reachability'][self.label('spare')],'unknown')

    def test_equal_basenames_resolve_to_their_exact_indexed_files(self):
        (self.root/'game/chapter').mkdir()
        (self.root/'game/chapter/story.rpy').write_text('label separate:\n    return\n',encoding='utf-8')
        _,self.project=open_native(self.root)
        self.flow=graph(self.root,self.project)
        result=edit(self.root,self.project,self.request(self.point('a'),'connect_exit',target=self.label('separate')))
        self.assertEqual([d['path'] for d in result['edits']],['game/story.rpy'])
        self.assertIn('jump separate # retain',result['edits'][0]['content'])
        self.assertTrue(result['edits'][0]['exists'])
        self.assertEqual((self.root/'game/chapter/story.rpy').read_text('utf-8'),'label separate:\n    return\n')

    def test_same_file_branch_creation_coalesces_edits_and_failure_is_atomic(self):
        original=(self.root/'game/story.rpy').read_bytes()
        options=[{'text':'新线','destination':{'kind':'new','scene':self.scene(path='game/story.rpy')}}, {'text':'结束','destination':{'kind':'return'}}]
        operation=self.request(self.point('a'),'branch_exit',options=options)
        result=edit(self.root,self.project,operation)
        self.assertEqual(len(result['edits']),1)
        self.assertIn('label scene_added:',result['edits'][0]['content']);self.assertIn('menu:',result['edits'][0]['content'])
        bad=copy.deepcopy(operation);bad['options'].append({'text':'错误','destination':{'kind':'existing','label':'missing'}})
        with self.assertRaises(ValueError):edit(self.root,self.project,bad)
        self.assertEqual((self.root/'game/story.rpy').read_bytes(),original)

    def test_pending_connected_and_ended_roundtrip_preserves_writer_comment(self):
        self.load('label start:\n    return # keep this\nlabel destination:\n    return\n')
        point=self.point('start')
        self.assertEqual(point['status'],'ended')
        view,project,_=self.canvas_operation('disconnect_exits',points=[point['id']])
        point=self.point('start',view)
        self.assertEqual(point['status'],'pending')
        self.assertIn('return # keep this'+PENDING_OUTLET,self.canvas_sources['game/story.rpy']['content'])
        view,project,_=self.canvas_operation('connect_exit',point=point['id'],target=self.label('destination'))
        point=self.point('start',view)
        self.assertEqual(point['status'],'connected')
        self.assertIn('jump destination # keep this',self.canvas_sources['game/story.rpy']['content'])
        self.assertNotIn(PENDING_OUTLET,self.canvas_sources['game/story.rpy']['content'])
        view,project,_=self.canvas_operation('disconnect_exits',points=[point['id']])
        point=self.point('start',view)
        self.assertEqual(point['status'],'pending')
        saved_pending=copy.deepcopy(list(self.canvas_sources.values()))
        view,project,_=self.canvas_operation('end_exits',points=[point['id']])
        self.assertEqual(self.point('start',view)['status'],'ended')
        self.assertIn('return # keep this\n',self.canvas_sources['game/story.rpy']['content'].replace('\r\n','\n'))
        # Buffer undo/redo reconstructs the same semantics without writing the game.
        pending_project=projection(self.root,self.project,saved_pending)
        pending_view=graph(self.root,pending_project,saved_pending)
        self.assertEqual(self.point('start',pending_view)['status'],'pending')
        saved=commit(self.root,list(self.canvas_sources.values()),self.project['revision'])
        _,reopened=open_native(self.root)
        self.assertEqual(self.point('start',graph(self.root,reopened))['status'],'ended')
        restored=restore(self.root,saved['transaction'],reopened['revision'])
        self.assertEqual((self.root/'game/story.rpy').read_text('utf-8'),'label start:\n    return # keep this\nlabel destination:\n    return\n')
        commit(self.root,saved_pending,restored['project']['revision'])
        _,reopened=open_native(self.root)
        self.assertEqual(self.point('start',graph(self.root,reopened))['status'],'pending')

    def test_new_block_outlets_pending_and_insertion_preserves_original_end(self):
        for kind in ('scene','choice','condition'):
            with self.subTest(kind=kind):
                self.canvas_sources={}
                view,project,_=self.canvas_operation('create_block',kind=kind,scene=self.scene(),options=['接受','拒绝'],condition='flag')
                owner=self.label('scene_added',project)
                outputs=[p for p in view['authoring']['points'].values() if p['owner']==owner and 'connect' in p['actions']]
                self.assertTrue(outputs)
                self.assertTrue(all(p['status']=='pending' for p in outputs))
                self.canvas_sources={}
                view,project,_=self.canvas_operation('create_block',kind=kind,point=self.point('b')['id'],scene=self.scene(),options=['继续','另一条路'],condition='flag')
                owner=self.label('scene_added',project)
                outputs=[p for p in view['authoring']['points'].values() if p['owner']==owner and 'connect' in p['actions']]
                self.assertEqual(outputs[0]['status'],'ended')
                if kind!='scene':self.assertEqual(outputs[1]['status'],'pending')
        self.canvas_sources={}
        result=edit(self.root,self.project,{'operation':'scene',**self.scene()})
        self.assertTrue(result['content'].endswith('return'+PENDING_OUTLET+'\n'))

    def test_branch_destinations_and_insert_preserve_pending_end_semantics(self):
        self.load('label start:\n    return'+PENDING_OUTLET+'\nlabel done:\n    return\n')
        view,project,result=self.canvas_operation('branch_exit',point=self.point('start')['id'],options=[
            {'text':'等待连接','destination':{'kind':'pending'}},
            {'text':'主动结束','destination':{'kind':'return'}},
            {'text':'新场景','destination':{'kind':'new','scene':self.scene()}}])
        points=view['authoring']['points']
        menu=next(n for n in view['nodes'] if n.get('branchPoint'))
        self.assertEqual([points[pid]['status'] for pid in menu['optionPoints']],['pending','ended','connected'])
        self.assertEqual(next(p['status'] for p in points.values() if p['owner']==self.label('scene_added',project) and 'connect' in p['actions']),'pending')
        self.canvas_sources={}
        view,project,_=self.canvas_operation('insert_after',point=self.point('start')['id'],scene=self.scene())
        self.assertEqual(next(p['status'] for p in view['authoring']['points'].values() if p['owner']==self.label('scene_added',project) and 'connect' in p['actions']),'pending')

    def test_multi_file_end_is_atomic_and_rejects_stale_or_unsafe_exits(self):
        view,project,_=self.canvas_operation('create_block',kind='scene',scene=self.scene())
        first=self.point('a',view)
        second=next(p for p in view['authoring']['points'].values() if p['owner']==self.label('scene_added',project) and 'connect' in p['actions'])
        sources=copy.deepcopy(self.canvas_sources)
        with self.assertRaisesRegex(ValueError,'出口'):
            self.canvas_operation('end_exits',points=[first['id'],'missing'])
        self.assertEqual(sources,self.canvas_sources)
        view,project,result=self.canvas_operation('end_exits',points=[first['id'],second['id']])
        self.assertEqual(len(result['edits']),2)
        self.assertEqual(self.point('a',view)['status'],'ended')
        self.assertIn('return # retain',self.canvas_sources['game/story.rpy']['content'])
        self.assertTrue(all(p['status']=='ended' for p in view['authoring']['points'].values() if p['owner']==second['owner'] and 'connect' in p['actions']))
        request=self.request(self.point('a'),'end_exits',points=[self.point('a')['id']])
        (self.root/'game/story.rpy').write_text('label start:\n    return\n',encoding='utf-8')
        with self.assertRaises(ValueError):edit(self.root,self.project,request)

    def test_choice_block_optional_targets_validate_before_creating_scene(self):
        view,project,_=self.canvas_operation('create_block',kind='choice',point=self.point('a')['id'],scene=self.scene(),
                                             options=['继承原后续','指定场景','待连接'],targets=[None,self.label('spare'),None])
        owner=self.label('scene_added',project)
        points=view['authoring']['points']
        block=next(n for n in view['story']['nodes'] if n['id']==owner)
        outputs=[points[pid] for pid in block['optionPoints']]
        self.assertEqual([p['target'] for p in outputs],[self.label('b'),self.label('spare'),None])
        self.assertEqual([p['status'] for p in outputs],['connected','connected','pending'])
        self.canvas_sources={}
        before=(self.root/'game/story.rpy').read_bytes()
        for targets in ([self.label('spare'),'missing'],[None],[None,12]):
            with self.subTest(targets=targets),self.assertRaises(ValueError):
                self.canvas_operation('create_block',kind='choice',scene=self.scene(),options=['一','二'],targets=targets)
        self.assertEqual((self.root/'game/story.rpy').read_bytes(),before)
        self.assertFalse((self.root/'game/creator_scenes.rpy').exists())

    def test_terminal_menu_exit_can_connect_without_rewriting_opaque_story_prefix(self):
        prefix='label start:\n    $ notify("keep")\n    "Chapter finished"\n'
        self.load(prefix+'    menu:\n        "Return to title":\n            return\nlabel chapter_two:\n    return\n')
        owner=next(n for n in self.flow['nodes'] if n['id']==self.label('start'))
        self.assertFalse(owner.get('editPoint'))
        menu=next(n for n in self.flow['nodes'] if n['label']==owner['id'] and n.get('optionPoints'))
        point=self.flow['authoring']['points'][menu['optionPoints'][0]]
        result=edit(self.root,self.project,self.request(point,'connect_exit',target=self.label('chapter_two')))
        content=result['edits'][0]['content'].replace('\r\n','\n')
        self.assertTrue(content.startswith(prefix))
        self.assertIn('"Return to title":\n            jump chapter_two',content)
        self.load(prefix+'    menu:\n        "Complex":\n            $ notify("branch")\n            return\n')
        self.assertFalse(any(n.get('optionPoints') for n in self.flow['nodes']))


if __name__=='__main__':unittest.main()
