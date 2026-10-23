import test from 'node:test';
import assert from 'node:assert/strict';
import type {NativeFlow,FlowEditPoint} from '../src/native-types';
import {chapterPorts,chapterCollapsedHeight} from '../src/chapter-ports';

function fixture():NativeFlow {
 return {groups:[{id:'chapter',title:'第一章'}],nodes:['a','b'].map((id,line)=>({id,type:'scene',title:id,group:'chapter',label:id,source:{path:'game/story.rpy',line:line+1}})),edges:[{id:'ab',source:'a',target:'b',kind:'jump',title:''}],authoring:{documents:{},points:{},targets:[{id:'a',reason:''},{id:'b',reason:''}],reachability:{}}};
}
function point(id:string,owner:string,target:string|null,title=''):FlowEditPoint {return {id,owner,target,title,kind:'jump',actions:['connect'],source:{path:'game/story.rpy',line:1},contentHash:'hash'};}

test('chapter proxies retain exact exit identities and only expose a unique entry',()=>{
 const flow=fixture();flow.authoring!.points={ab:point('ab','a','b'),out:point('out','b','outside')};
 const result=chapterPorts(flow,'chapter',id=>({a:'开场',b:'结尾',outside:'第二章'}[id]||id));
 assert.deepEqual(result.entry,{sceneId:'a',caption:'开场'});
 assert.deepEqual(result.ports.map(port=>port.point.id),['out']);
 assert.equal(result.ports[0].caption,'结尾 · 后续');assert.equal(result.ports[0].targetCaption,'第二章');
 assert.strictEqual(result.ports[0].point,flow.authoring!.points.out);
});

test('zero and multiple exits stay explicit; duplicate captions are distinguishable',()=>{
 const flow=fixture();assert.equal(chapterPorts(flow,'chapter').ports.length,0);
 flow.authoring!.points={one:point('one','b',null,'接受'),two:point('two','b',null,'接受'),blocked:{...point('blocked','b',null),actions:[]}};
 const model=chapterPorts(flow,'chapter');assert.equal(model.ports.length,2);
 assert.deepEqual(model.ports.map(port=>port.caption),['b · 接受 1','b · 接受 2']);
 assert.ok(chapterCollapsedHeight(model)>chapterCollapsedHeight({ports:[],entry:model.entry}));
});

test('multiple roots have a visible default while unavailable targets remain blocked',()=>{
 const flow=fixture();flow.edges=[];assert.equal(chapterPorts(flow,'chapter').entry?.sceneId,'a');
 flow.authoring!.targets[1].reason='标签重复';assert.equal(chapterPorts(flow,'chapter').entry?.sceneId,'a');
 flow.edges=[{id:'ab',source:'a',target:'b',kind:'jump',title:''}];
 flow.authoring!.targets[0].reason='无法确定运行目标';assert.equal(chapterPorts(flow,'chapter').entry,undefined);
 assert.equal(chapterPorts(flow,'chapter').entryReason,'无法确定运行目标');
 flow.authoring!.targets[0].reason='';flow.authoring!.targets[1].reason='';flow.edges.push({id:'xb',source:'outside',target:'b',kind:'jump',title:''});
 assert.equal(chapterPorts(flow,'chapter').entry?.sceneId,'b');
});

test('inactive copies and unavailable helpers do not obscure a unique entry, but their internal edges remain',()=>{
 const flow=fixture();
 flow.nodes.push({...flow.nodes[0],id:'old-copy'},{...flow.nodes[0],id:'system-helper',role:'system'});
 flow.authoring!.targets.push({id:'old-copy',reason:'当前采用编号版本，此副本仅供查看。'});
 assert.equal(chapterPorts(flow,'chapter').entry?.sceneId,'a');
 flow.edges.push({id:'helper-entry',source:'system-helper',target:'a',kind:'jump',title:''});
 assert.equal(chapterPorts(flow,'chapter').entry,undefined);
});

test('call and return continuations do not masquerade as chapter entrances',()=>{
 const flow=fixture();flow.edges.push({id:'call',source:'outside',target:'b',kind:'call',title:''},{id:'return',source:'b',target:'a',kind:'return',title:''});
 assert.equal(chapterPorts(flow,'chapter').entry?.sceneId,'a');
 assert.equal(chapterPorts(flow,'empty').entryReason,'章节中还没有场景');
});

test('chapter entry and continuation preferences are explicit and stale choices do not silently retarget',()=>{
 const flow=fixture();flow.authoring!.points={one:point('one','b',null,'完成'),two:point('two','b',null,'离开')};
 const selected=chapterPorts(flow,'chapter',undefined,{entry:'b',exit:'two'});
 assert.equal(selected.entry?.sceneId,'b');assert.equal(selected.exit?.point.id,'two');
 assert.equal(chapterPorts(flow,'chapter').exit,undefined);
 assert.equal(chapterPorts(flow,'chapter',undefined,{entry:'missing',exit:'missing'}).entry,undefined);
 assert.equal(chapterPorts(flow,'chapter',undefined,{entry:'missing',exit:'missing'}).exit,undefined);
});

test('an established incoming chapter entrance is preferred over new independent scenes',()=>{
 const flow=fixture();flow.edges=[{id:'incoming',source:'outside',target:'b',kind:'jump',title:''}];
 assert.equal(chapterPorts(flow,'chapter').entry?.sceneId,'b');
});
