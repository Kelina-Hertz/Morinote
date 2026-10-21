const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {startupProject,rememberProject}=require('../workspace-startup.cjs');
const {RecoveryStore}=require('../recovery.cjs');
const {routeMethod}=require('../security.cjs');
const session='a'.repeat(32),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
function temporary(t){const root=fs.mkdtempSync(path.join(os.tmpdir(),'offline-ide-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));return root;}
function state(value='draft',exists=true){return {documents:[{base:{path:'game/script.rpy',content:'original\r\n',hash:sha('original\r\n'),exists,bom:true,newline:'\r\n'},value}],tabs:[{id:'code:game/script.rpy',title:'剧本',kind:'code',target:'game/script.rpy'}],active:'code:game/script.rpy',lastCode:'game/script.rpy'};}
async function store(root){const s=new RecoveryStore();await s.register({root,session,project:{id:'test-project',nativeRenpy:{inPlace:true}}});return s;}
test('portable startup finds repository above hash cache; remembers explicit project',t=>{
 const root=temporary(t),userData=path.join(root,'user');fs.mkdirSync(path.join(root,'game'));
 const args={userData,sourceDirectory:path.join(root,'creator','.portable','hash','win-unpacked','resources','app.asar','electron'),executable:path.join(root,'creator','.portable','hash','win-unpacked','Morinote IDE.exe')};
 assert.equal(startupProject(args).path,root);rememberProject(userData,path.join(root,'other'));assert.equal(startupProject(args).path,path.join(root,'other'));
});
test('offline IPC has native editing routes and rejects all AI endpoints',()=>{
 for(const route of ['/api/workspace/merge','/api/workspace/motion-source','/api/preview/motion'])assert.equal(routeMethod(route,{}),'POST');
 assert.equal(routeMethod('/api/workspace/save-recovery'),'GET');
 for(const route of ['/api/tasks','/api/tasks/new','/api/ai/settings'])assert.throws(()=>routeMethod(route,{}));
 assert.throws(()=>routeMethod('/api/workspace/document?path=../outside'));
});
test('recovery persists buffers, encoding, new files and history without writing original',async t=>{
 const root=temporary(t);fs.mkdirSync(path.join(root,'game'));fs.writeFileSync(path.join(root,'game/script.rpy'),'original\r\n');
 const s=await store(root),payload={projectSession:session,sequence:1,reason:'close',state:state('new draft',false)};
 await s.request('write',payload);const restored=await (await store(root)).request('current',{projectSession:session});
 assert.equal(restored.state.documents[0].value,'new draft');assert.equal(restored.state.documents[0].base.exists,false);assert.equal(restored.state.documents[0].base.newline,'\r\n');
 assert.equal(fs.readFileSync(path.join(root,'game/script.rpy'),'utf8'),'original\r\n');
 const history=await s.request('history',{projectSession:session});assert.equal(history.items.length,1);
 const snapshot=await s.request('snapshot',{projectSession:session,id:history.items[0].id});assert.equal(snapshot.state.documents[0].value,'new draft');
});
test('stale writes and previous-project recovery requests are rejected',async t=>{
 const s=await store(temporary(t));await s.request('write',{projectSession:session,sequence:2,reason:'auto',state:state('newest')});
 await assert.rejects(s.request('write',{projectSession:session,sequence:1,reason:'auto',state:state('old')}));
 await assert.rejects(s.request('current',{projectSession:'b'.repeat(32)}));assert.equal((await s.request('current',{projectSession:session})).state.documents[0].value,'newest');
});
test('damaged latest recovery falls back to previous complete record',async t=>{
 const root=temporary(t),s=await store(root);
 for(const [sequence,value] of [[1,'first'],[2,'second']])await s.request('write',{projectSession:session,sequence,reason:'close',state:state(value)});
 fs.writeFileSync(path.join(root,'.creator/editor/recovery/current.json'),'broken');
 const restored=await (await store(root)).request('current',{projectSession:session});assert.equal(restored.state.documents[0].value,'first');assert.ok(restored.warning);
});
test('discard suppresses automatic recovery but retains history',async t=>{
 const root=temporary(t),s=await store(root);await s.request('write',{projectSession:session,sequence:1,reason:'close',state:state()});
 await s.request('discard',{projectSession:session,sequence:2});const reopened=await store(root);
 assert.equal((await reopened.request('current',{projectSession:session})).state,null);assert.ok((await reopened.request('history',{projectSession:session})).items.length);
});
