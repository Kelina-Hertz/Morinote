// Focused manual-save check in a disposable project; never launches Ren'Py.
const {app,ipcMain}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),output=path.join(root,'.checks','manual-save-ui',crypto.randomUUID());
const profile=path.join(output,'profile'),project=path.join(output,'project'),story=path.join(project,'game','story.rpy'),created=path.join(project,'game','creator_scenes.rpy');
fs.mkdirSync(path.dirname(story),{recursive:true});fs.mkdirSync(profile,{recursive:true});
const original='default score = 0\nlabel start:\n    "Original"\n    return\n';
fs.writeFileSync(story,original);fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let started=false,failed=false,testFinished=false,pendingExit;const exit=app.exit.bind(app);app.exit=code=>{if(!testFinished){pendingExit=code;return;}exit(failed?1:code);};
let closePhase=false;const closeRequests=[];
const handle=ipcMain.handle.bind(ipcMain);
ipcMain.handle=(channel,listener)=>handle(channel,channel!=='creator:request'?listener:async(...args)=>{if(closePhase)closeRequests.push(args[1].split('?')[0]);return listener(...args);});
app.on('browser-window-created',(_event,window)=>{
 window.hide();window.webContents.setBackgroundThrottling(false);
 window.webContents.on('did-finish-load',async()=>{
  if(started)return;started=true;
  const js=code=>window.webContents.executeJavaScript(code,true),report={ok:false,output};
  async function until(expression,label){const end=Date.now()+18000;while(Date.now()<end){if(await js(expression))return;await pause(80);}throw Error(label+'\n'+await js('document.body.innerText.slice(-2200)'));}
  async function click(text,selector='button'){await js(`(()=>{const b=[...document.querySelectorAll(${JSON.stringify(selector)})].find(e=>e.textContent.trim()===${JSON.stringify(text)});if(!b||b.disabled)throw Error('Missing button '+${JSON.stringify(text)});b.click();})()`);await pause(80);}
  async function createScene(title){await click('新建');await click('剧情块');await js(`(()=>{const e=document.querySelector('[aria-label="剧情块名称"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(title)});e.dispatchEvent(new Event('input',{bubbles:true}));})()`);await click('创建');await until(`!document.querySelector('.flow-quick-create')&&[...document.querySelectorAll('.react-flow__node strong')].some(e=>e.textContent===${JSON.stringify(title)})`,'Scene created');}
  const dirty=`document.querySelector('.project-title small')?.textContent==='有未保存更改'`,prompt=`[...document.querySelectorAll('[role=dialog] h2')].some(e=>e.textContent==='有未保存的修改')`;
  try{
   await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Workspace ready');
   await pause(1200);assert.equal(await js(dirty),false,'Opening the canvas must not dirty the project');
   const initial=await js(`window.creator.request('/api/project')`);
   await createScene('Discard me');await click('整理布局');await pause(1700);
   assert.equal(await js(dirty),true);assert.equal(fs.existsSync(created),false);assert.equal(fs.readFileSync(story,'utf8'),original);
   assert.equal(fs.existsSync(path.join(project,'.creator','editor','recovery','current.json')),false,'No timed draft writes');
   assert.equal((await js(`window.creator.request('/api/project')`)).project.revision,initial.project.revision,'Layout must stay in memory');
   if(process.argv.includes('--discard-close')){
    const closed=new Promise(resolve=>window.once('closed',resolve));window.close();await until(prompt,'Discard close prompt');
    closePhase=true;const at=performance.now();await click('不保存','[role=dialog]:not(.native-ide [role=dialog]) button');await closed;
    report.closeMs=Math.round(performance.now()-at);report.closeRequests=closeRequests;
    assert.equal(fs.existsSync(created),false);assert.equal(fs.readFileSync(story,'utf8'),original);
    assert.equal(fs.existsSync(path.join(project,'.creator','editor','recovery','cleared.json')),true,'Discard marker must prevent recovery on restart');
    if(process.argv.includes('--verify'))assert.equal(closeRequests.some(route=>['/api/project','/api/workspace','/api/workspace/analyze'].includes(route)),false,'Closing must not rebuild the workspace');
    report.ok=true;report.checks='Discard and close clears recovery without saving source or rebuilding the workspace';return;
   }
   window.close();await until(prompt,'Window close asks about changes');await click('取消','[role=dialog]:not(.native-ide [role=dialog]) button');await until(`!(${prompt})&&!document.querySelector('.native-ide').inert`,'Cancel keeps editing');assert.equal(await js(dirty),true);
   await click('打开项目');await until(prompt,'Switch project asks about changes');await click('取消','[role=dialog]:not(.native-ide [role=dialog]) button');assert.equal(await js(dirty),true);
   await click('打开项目');await until(prompt,'Discard prompt');await click('不保存','[role=dialog]:not(.native-ide [role=dialog]) button');await until(`!![...document.querySelectorAll('[role=dialog] h2')].find(e=>e.textContent==='打开项目')`,'Open project picker after discard');
   await js(`document.querySelector('[role=dialog] button[aria-label="关闭"]').click()`);assert.equal(await js(dirty),false);assert.equal(fs.existsSync(created),false);
   const recovery=await js(`(async()=>{const p=await window.creator.request('/api/project');return window.creator.recovery('current',{projectSession:p.session});})()`);assert.equal(recovery.state.documents.length,0,'Discarded work cannot restore on restart');
   await createScene('Save me');await click('整理布局');
   fs.writeFileSync(created,'label external:\n    return\n');
   window.close();await until(prompt,'Second close prompt');await click('保存','[role=dialog]:not(.native-ide [role=dialog]) button');await until(`!!document.querySelector('[role=dialog] [role=alert]')`,'Save conflict stays open');assert.equal(window.isDestroyed(),false);assert.match(fs.readFileSync(created,'utf8'),/external/);
   await click('取消','[role=dialog]:not(.native-ide [role=dialog]) button');await until(`!(${prompt})`,'Can cancel failed save');
   fs.unlinkSync(created);await js(`(()=>{const m=[...document.querySelectorAll('[role=dialog]')].find(e=>!e.querySelector('h2')?.textContent.includes('未保存'));m?.querySelector('button[aria-label="关闭"]')?.click();})()`);
   const closed=new Promise(resolve=>window.once('closed',resolve));window.close();await until(prompt,'Retry close prompt');closePhase=true;const at=performance.now();await click('保存','[role=dialog]:not(.native-ide [role=dialog]) button');await closed;
   report.closeMs=Math.round(performance.now()-at);report.closeRequests=closeRequests;
   if(process.argv.includes('--verify'))assert.equal(closeRequests.some(route=>['/api/project','/api/workspace','/api/workspace/analyze'].includes(route)),false,'Saving and closing must not rebuild the workspace');
   assert.match(fs.readFileSync(created,'utf8'),/Save me/);assert.equal(fs.readFileSync(story,'utf8'),original);
   report.ok=true;report.checks='No automatic source/config/draft writes; dirty indicator; cancel window/project leave; discard clears recovery; failed save keeps window and source; explicit save persists scene and closes';
  }catch(error){failed=true;report.error=String(error.stack||error);if(!window.isDestroyed())report.body=await js('document.body.innerText').catch(()=>null);}
  finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!window.isDestroyed())window.destroy();testFinished=true;if(pendingExit!==undefined)exit(failed?1:pendingExit);else app.quit();}
 });
});
require('../main.cjs');
