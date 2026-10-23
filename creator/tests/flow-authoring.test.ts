import test from 'node:test';
import assert from 'node:assert/strict';
import {comparisonExpression,formsCycle,flowHashes,insertionProblem,pointsForNode} from '../src/flow-authoring';
import {storyLayout} from '../src/story-layout';

test('cycle detection terminates and excludes shared helper return edges',()=>{
 const flow:any={nodes:[],edges:[{source:'a',target:'helper',kind:'call'},{source:'helper',target:'unrelated',kind:'return'},{source:'a',target:'b',kind:'next'},{source:'b',target:'c',kind:'next'}]};
 assert.equal(formsCycle(flow,'a','a'),true);assert.equal(formsCycle(flow,'c','a'),true);assert.equal(formsCycle(flow,'unrelated','a'),false);
 flow.edges.push({source:'c',target:'a',kind:'jump'});assert.equal(formsCycle(flow,'missing','a'),false);
});

test('visual conditions preserve number, string and boolean comparisons',()=>{
 assert.equal(comparisonExpression('score','>=','3','number'),'score >= 3');
 assert.equal(comparisonExpression('invited','falsy','','boolean'),'not invited');
 assert.equal(comparisonExpression('name','==','接受邀请','string'),'name == "接受邀请"');
 assert.equal(comparisonExpression('persistent.opened','==','true','boolean'),'persistent.opened == True');
 assert.throws(()=>comparisonExpression('score','>','three','number'),/数字/);
 assert.throws(()=>comparisonExpression('renpy.jump()','truthy','','boolean'),/变量/);
});
test('only source-backed connect points become handles; missing files use empty fingerprints',()=>{
 const point={id:'exit-a',actions:['connect']};const flow:any={nodes:[{id:'a',editPoint:'exit-a'},{id:'opaque'}],authoring:{points:{'exit-a':point}}};
 assert.deepEqual(pointsForNode(flow,'a'),[point]);assert.deepEqual(pointsForNode(flow,'opaque'),[]);
 const docs={a:{hash:'disk',contentHash:'buffer'}};
 const hashes=flowHashes(docs,[{name:'scene_a',title:'新场景',path:'game/new.rpy',group:'剧情'}]);
 assert.deepEqual(hashes.a,docs.a);assert.equal(hashes['game/new.rpy'].hash,hashes['game/new.rpy'].contentHash);assert.equal(Object.keys(docs).length,1);
});

test('inserting an existing scene excludes connected scenes, foreign continuations and loops',()=>{
 const exit:any={id:'out',owner:'c',target:null,kind:'return'},point:any={owner:'a',target:'b'};
 const flow:any={nodes:[{id:'c',type:'scene',editPoint:'out'}],edges:[],authoring:{points:{out:exit},targets:[{id:'c',reason:''}]}};
 const project:any={graphs:[],nativeRenpy:{labels:[{id:'root',name:'start'},{id:'c',name:'c'}]}};
 assert.equal(insertionProblem(flow,project,'c',point),'');
 exit.target='other';assert.match(insertionProblem(flow,project,'c',point),/其他后续/);exit.target=null;
 flow.edges=[{source:'other',target:'c'}];assert.match(insertionProblem(flow,project,'c',point),/已有入口/);
 flow.edges=[{source:'c',target:'a',kind:'call'}];assert.match(insertionProblem(flow,project,'c',point),/循环/);
});

test('horizontal and vertical layout use measured node sizes without overlap',()=>{
 const flow:any={nodes:['a','b','c'].map((id,line)=>({id,group:'g',source:{path:'story',line}})),edges:[{id:'1',source:'a',target:'b',kind:'next'},{id:'2',source:'b',target:'c',kind:'next'}]};
 const sizes={a:{width:282,height:410},b:{width:282,height:260},c:{width:282,height:180}};
 const vertical=storyLayout(flow,'g',{sizes}),horizontal=storyLayout(flow,'g',{sizes,direction:'horizontal'});
 assert.ok(vertical.positions.b.y>=vertical.positions.a.y+sizes.a.height+60);
 assert.ok(horizontal.positions.b.x>=horizontal.positions.a.x+sizes.a.width+70);
 assert.equal(horizontal.positions.a.y,horizontal.positions.c.y);
 assert.deepEqual(flow.nodes.map((n:any)=>n.id),['a','b','c']);
});
