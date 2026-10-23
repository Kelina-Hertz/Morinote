// Chapter-level authoring only, in a disposable project; no game or save.
const {app,ipcMain}=require('electron'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),output=path.join(root,'.checks','chapter-ui',crypto.randomUUID()),profile=path.join(output,'profile'),project=path.join(output,'project');
fs.mkdirSync(path.join(project,'game'),{recursive:true});fs.mkdirSync(profile,{recursive:true});
const original='default score = 0\n# morinote-scene: {"title":"序章开场","group":"序章"}\nlabel start:\n    "序章"\n    return\n# morinote-scene: {"title":"第一章开场","group":"第一章"}\nlabel c1:\n    $ notify("keep")\n    "第一章"\n    menu:\n        "返回标题界面":\n            return\n# morinote-scene: {"title":"第二章开场 A","group":"第二章"}\nlabel c2a:\n    "第二章 A"\n    return\n# morinote-scene: {"title":"第二章开场 B","group":"第二章"}\nlabel c2b:\n    "第二章 B"\n    return\n';
fs.writeFileSync(path.join(project,'game','story.rpy'),original);fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
let latest,prepared,started=false,failed=false;const exit=app.exit.bind(app);app.exit=code=>exit(failed?1:code);
const handle=ipcMain.handle.bind(ipcMain);ipcMain.handle=(channel,listener)=>handle(channel,channel!=='creator:request'?listener:async(...args)=>{const result=await listener(...args);if(args[1]==='/api/workspace/analyze')latest=result;if(args[1]==='/api/workspace/prepare')prepared=result;return result;});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
app.on('browser-window-created',(_,window)=>{window.hide();window.webContents.setBackgroundThrottling(false);window.webContents.on('did-finish-load',async()=>{
 if(started)return;started=true;const report={ok:false,output},js=code=>window.webContents.executeJavaScript(code,true);
 async function until(code,label){for(let i=0;i<250;i++){if(await js(code))return;await pause(80);}throw Error(label+'\n'+await js('document.body.innerText'));}
 async function select(label,value){await js(`(()=>{const e=document.querySelector('[aria-label='+CSS.escape(${JSON.stringify(label)})+']');if(!e||e.disabled)throw Error('Unavailable select '+${JSON.stringify(label)});Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('change',{bubbles:true}));})()`);await pause(80);}
 async function fit(){await js(`document.querySelector('.react-flow__controls-fitview').click()`);await pause(500);}
 try{
  await until(`!!document.querySelector('.native-ide:not([inert]) [aria-label="进入第一章"]')`,'Chapter entry on expanded chapter');
  assert.equal(await js(`!!document.querySelector('[aria-label="进入序章"]')&&!!document.querySelector('[aria-label="进入第二章"]')&&!!document.querySelector('[aria-label="连接第一章下一章"]')`),true);
  await select('序章下一章','第一章');await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已连接：序章 → 第一章')`,'Prologue connects to chapter one');
  const second=latest.project.nativeRenpy.labels.find(label=>label.name==='c2b').id;
  await js(`document.querySelector('[aria-label="第二章入口"]').closest('details').open=true`);
  await select('第二章入口',second);await until(`document.querySelector('[aria-label="第二章入口"]').value===${JSON.stringify(second)}`,'Explicit chapter entry selected');
  await js(`document.querySelector('[aria-label="第二章入口"]').closest('details').open=false`);await pause(650);await fit();
  await js(`(async()=>{const from=document.querySelector('[aria-label="连接第一章下一章"]'),to=document.querySelector('[aria-label="进入第二章"]'),a=from.getBoundingClientRect(),b=to.getBoundingClientRect(),x=a.x+a.width/2,y=a.y+a.height/2,tx=b.x+b.width/2,ty=b.y+b.height/2;from.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0,buttons:1,clientX:x,clientY:y,view:window}));for(let i=1;i<=10;i++){document.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,buttons:1,clientX:x+(tx-x)*i/10,clientY:y+(ty-y)*i/10,view:window}));await new Promise(r=>setTimeout(r,25));}to.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0,clientX:tx,clientY:ty,view:window}));})()`);
  await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已连接：第一章 → 第二章')`,'Chapter-level drag connection');
  assert.equal(await js(`!!document.querySelector('[role=dialog]')`),false);
  assert.match(prepared.edits[0].content,/\$ notify\("keep"\)/);assert.match(prepared.edits[0].content,/jump c2b/);
  assert.equal(latest.project.ide.chapterEntries['第二章'],'c2b');
  await js(`document.querySelector('button[aria-label="撤销"]').click()`);await until(`document.querySelector('.statusbar').textContent.startsWith('就绪')`,'Undo finished');
  assert.equal(latest.flow.authoring.points[Object.keys(latest.flow.authoring.points).find(id=>latest.flow.authoring.points[id].title==='返回标题界面')].target,null);
  await js(`document.querySelector('button[aria-label="重做"]').click()`);await until(`document.querySelector('.statusbar').textContent.startsWith('就绪')`,'Redo finished');
  assert.equal(Object.values(latest.flow.authoring.points).find(point=>point.title==='返回标题界面').target,second);
  await fit();fs.writeFileSync(path.join(output,'chapters.png'),(await window.webContents.capturePage()).toPNG());
  assert.equal(fs.readFileSync(path.join(project,'game','story.rpy'),'utf8'),original);
  report.ok=true;report.checks='Entries visible expanded and folded, default chapter connection, configured chapter entrance, chapter-to-chapter drag, static terminal choice preserved after opaque calls, undo/redo, draft-only edits';
 }catch(error){failed=true;report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);fs.writeFileSync(path.join(output,'failure.png'),(await window.webContents.capturePage()).toPNG());}
 finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));window.destroy();app.quit();}
});});
require('../main.cjs');
