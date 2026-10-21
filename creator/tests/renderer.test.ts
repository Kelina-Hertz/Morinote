import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileSavedBuffers} from '../src/native-buffers';
import {effective,insertLine,splitTrack,segments,sceneEntryState,textConnected} from '../src/model';
import {storyLayout} from '../src/story-layout';
import {sceneTitle} from '../src/scene-titles';

test('save completion preserves later typing while advancing the base version',()=>{
 const base={path:'game/a.rpy',hash:'old',content:'old'},saved={...base,hash:'new',content:'submitted'};
 const result=reconcileSavedBuffers({'game/a.rpy':{base,value:'typed during save'}},[saved],[{path:base.path,content:'submitted'}]);
 assert.equal(result[base.path].value,'typed during save');assert.equal(result[base.path].base.hash,'new');
});
test('unchanged submitted buffer becomes clean after save',()=>{
 const base={path:'game/a.rpy',hash:'old',content:'old'},saved={...base,hash:'new',content:'submitted'};
 const result=reconcileSavedBuffers({'game/a.rpy':{base,value:'submitted'}},[saved],[{path:base.path,content:'submitted'}]);
 assert.equal(result[base.path].value,result[base.path].base.content);
});
test('splitting B propagates forward until explicit C; inserting text does not add cues',()=>{
 const scene:any={lines:[{id:'a',kind:'narration',visual:{background:'A',sprites:[]},audio:null},{id:'b',kind:'narration',visual:null,audio:null},{id:'inherited',kind:'narration',visual:null,audio:null},{id:'c',kind:'narration',visual:{background:'C',sprites:[]},audio:null}]};
 const split=splitTrack(scene,1,'visual');split.lines[1].visual!.background='B';
 assert.equal(effective(split.lines,2,'visual')!.background,'B');assert.equal(effective(split.lines,3,'visual')!.background,'C');
 assert.equal(scene.lines[0].visual.background,'A');assert.equal(segments(split.lines,'visual').length,3);
 const inserted=insertLine(split,1,'narration');assert.equal(inserted.lines[2].visual,null);assert.equal(inserted.lines[2].audio,null);
});
test('text merging preserves explicit cue boundaries and chat identity',()=>{
 const lines:any=[{kind:'dialogue',speaker:'甲',visual:null,audio:null},{kind:'dialogue',speaker:'甲',visual:null,audio:null}];
 assert.equal(textConnected(lines,1),true);lines[1].visual={background:'A'};assert.equal(textConnected(lines,1),false);
 lines[1]={kind:'chat',phone:{title:'手机'},visual:null,audio:null};assert.equal(textConnected(lines,1),false);
});
test('branch merge shows varying visual state rather than inventing a common background',()=>{
 const p:any={graphs:[{id:'g',parent:null,entry:'choice',nodes:[{id:'choice',type:'choice',options:[{id:'a',target:'a'},{id:'b',target:'b'}]},{id:'a',type:'scene',scene:'a',next:'join'},{id:'b',type:'scene',scene:'b',next:'join'},{id:'join',type:'scene',scene:'join'}]}],scenes:[{id:'a',lines:[{visual:{background:'A'}}]},{id:'b',lines:[{visual:{background:'B'}}]},{id:'join',lines:[]}]};
 assert.equal(sceneEntryState(p,'join','visual').kind,'varying');
});
test('story layout keeps branch nodes parallel, merge below, and loop as a back edge',()=>{
 const flow:any={nodes:['a','b','c','d'].map((id,i)=>({id,group:'g',source:{path:'game/script.rpy',line:i}})),edges:[['a','b'],['a','c'],['b','d'],['c','d'],['d','a']].map(([source,target],i)=>({id:String(i),source,target,kind:'next'}))};
 const layout=storyLayout(flow,'g');assert.equal(layout.positions.b.y,layout.positions.c.y);assert.ok(layout.positions.d.y>layout.positions.b.y);assert.equal(layout.backs.size,1);
});
test('readable Morinote titles preserve label identity and explicit user names',()=>{
 const names=['C1a','C1b1','C1b2','C1b3','C1c1','C1c2','C1c3','phonelabel_01'];
 const p:any={nativeRenpy:{labels:names.map(name=>({id:name,name,file:name==='C1a'?'script_c1a.rpy':name.startsWith('C1b')?'script_c1b.rpy':name.startsWith('C1c')?'script_c1c.rpy':'message.rpy'}))}};
 assert.equal(sceneTitle(p,'C1b2'),'摊位初遇 · 汐泉与渡鸥');p.ide={sceneTitles:{C1b2:'我的场景'}};assert.equal(sceneTitle(p,'C1b2'),'我的场景');assert.equal(p.nativeRenpy.labels[2].name,'C1b2');
});
