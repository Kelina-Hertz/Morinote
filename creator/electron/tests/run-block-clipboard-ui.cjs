// Context-menu authoring in a disposable project, without saves or previews.
const {app,ipcMain}=require('electron'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),output=path.join(root,'.checks','block-clipboard-ui',crypto.randomUUID()),profile=path.join(output,'profile'),project=path.join(output,'project');
fs.mkdirSync(path.join(project,'game'),{recursive:true});fs.mkdirSync(profile,{recursive:true});
const original='label start:\n    jump a\n# morinote-scene: {"title":"邀请剧情","group":"剧情"}\nlabel a:\n    "接受邀请还是拒绝邀请"\n    jump b\n# morinote-scene: {"title":"后续剧情","group":"剧情"}\nlabel b:\n    "后续"\n    return\n';
fs.writeFileSync(path.join(project,'game/story.rpy'),original);fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
let latest,started=false,failed=false;const exit=app.exit.bind(app);app.exit=code=>exit(failed?1:code);
const handle=ipcMain.handle.bind(ipcMain);ipcMain.handle=(channel,listener)=>handle(channel,channel!=='creator:request'?listener:async(...args)=>{const result=await listener(...args);if(args[1]==='/api/workspace/analyze')latest=result;return result;});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
app.on('browser-window-created',(_,window)=>{window.hide();window.webContents.setBackgroundThrottling(false);window.webContents.on('did-finish-load',async()=>{
 if(started)return;started=true;const report={ok:false,output},js=code=>window.webContents.executeJavaScript(code,true);
 async function until(code,label){for(let i=0;i<180;i++){if(await js(code))return;await pause(80);}throw Error(label+'\n'+await js('document.body.innerText'));}
 async function idle(){await until(`document.querySelector('.statusbar').textContent.startsWith('就绪')&&!document.querySelector('.flow-connection-error')`,'Edit finished');await pause(100);}
 async function click(text){await js(`(()=>{const b=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()===${JSON.stringify(text)}||e.getAttribute('aria-label')===${JSON.stringify(text)});if(!b||b.disabled)throw Error('Unavailable '+${JSON.stringify(text)});b.click();})()`);await pause(80);}
 async function menu(title){await js(`(()=>{const n=[...document.querySelectorAll('.react-flow__node')].find(n=>n.querySelector('strong')?.textContent===${JSON.stringify(title)});if(!n)throw Error('Missing scene '+${JSON.stringify(title)});n.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:600,clientY:300}));})()`);await until(`!!document.querySelector('[aria-label="剧情块操作"]')`,'Node context menu');}
 async function item(text){await js(`(()=>{const b=[...document.querySelectorAll('[role=menuitem]')].find(e=>e.textContent.startsWith(${JSON.stringify(text)}));if(!b||b.disabled)throw Error('Unavailable menu '+${JSON.stringify(text)});b.click();})()`);await pause(100);await idle();}
 async function paste(){await js(`document.querySelector('.react-flow__pane').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:900,clientY:550}))`);await until(`!!document.querySelector('[aria-label="新建剧情节点"]')`,'Canvas menu');await item('粘贴剧情块');}
 try{
  await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Project loaded');
  await js(`document.querySelector('.react-flow__node[data-id="group:剧情"]').dispatchEvent(new MouseEvent('dblclick',{bubbles:true,button:0}))`);await idle();
  await until(`[...document.querySelectorAll('.react-flow__node strong')].some(e=>e.textContent==='邀请剧情')`,'Chapter expanded');
  await menu('邀请剧情');assert.equal(await js(`document.querySelectorAll('[aria-label="剧情块操作"] [role=menuitem]').length`),3);
  fs.writeFileSync(path.join(output,'menu.png'),(await window.webContents.capturePage()).toPNG());
  await js(`document.querySelector('[aria-label="剧情块操作"]').dispatchEvent(new KeyboardEvent('keydown',{key:'c',ctrlKey:true,bubbles:true,cancelable:true}))`);await idle();
  await click('项目素材库');await click('剧情总图');await until(`!!document.querySelector('.react-flow__pane')`,'Back to canvas');
  await paste();await until(`[...document.querySelectorAll('.react-flow__node strong')].some(e=>e.textContent==='邀请剧情 副本')`,'Copy pasted after changing tabs');
  const clone=latest.project.nativeRenpy.labels.find(l=>l.displayTitle==='邀请剧情 副本');assert(clone);assert.notEqual(clone.name,'a');
  const scene=latest.project.scenes.find(s=>s.id===clone.id);assert.equal(scene.lines[0].text,'接受邀请还是拒绝邀请');
  await menu('邀请剧情 副本');await item('剪切');assert(!latest.project.nativeRenpy.labels.some(l=>l.id===clone.id));
  await paste();assert(latest.project.nativeRenpy.labels.some(l=>l.id===clone.id));
  await menu('邀请剧情');await item('删除');assert(!latest.project.nativeRenpy.labels.some(l=>l.name==='a'));
  const entry=latest.flow.nodes.find(n=>n.title==='start');assert.equal(latest.flow.authoring.points[entry.editPoint].status,'pending');
  await click('撤销');await idle();assert(latest.project.nativeRenpy.labels.some(l=>l.name==='a'));
  await click('重做');await idle();assert(!latest.project.nativeRenpy.labels.some(l=>l.name==='a'));
  // Backspace/Delete are handled as source edits, rather than cosmetic removals.
  await menu('邀请剧情 副本');await js(`document.querySelector('.global-flow-canvas').focus();document.querySelector('.global-flow-canvas').dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}))`);await idle();assert(!latest.project.nativeRenpy.labels.some(l=>l.id===clone.id));
  assert.equal(fs.readFileSync(path.join(project,'game/story.rpy'),'utf8'),original);assert.equal(fs.existsSync(path.join(project,'game/creator_scenes.rpy')),false);
  report.ok=true;report.checks='Right-click menu, copy and paste across tabs, full text and unique label, cut and paste, connected-scene deletion with pending upstream outlet, undo/redo, Delete shortcut, draft-only edits';
 }catch(error){failed=true;report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);fs.writeFileSync(path.join(output,'failure.png'),(await window.webContents.capturePage()).toPNG());}
 finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await pause(250);window.destroy();app.quit();}
});});
require('../main.cjs');
