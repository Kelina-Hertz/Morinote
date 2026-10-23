// Focused request-count and frame check; disposable project, no game or save.
const {app,ipcMain}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),output=path.join(root,'.checks','flow-performance',crypto.randomUUID());
const profile=path.join(output,'profile'),project=path.join(output,'project');
fs.mkdirSync(path.join(project,'game'),{recursive:true});fs.mkdirSync(profile,{recursive:true});
const original='default score = 0\n'+Array.from({length:60},(_,i)=>`# morinote-scene: {"title":"剧情 ${i}","group":"第${Math.floor(i/20)+1}章"}\nlabel ${i?'scene_'+i:'start'}:\n    "正文 ${i}"\n    ${i<59?'jump scene_'+(i+1):'return'}\n`).join('');
fs.writeFileSync(path.join(project,'game','story.rpy'),original);
fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
let phase='startup',started=false;const requests=[];
const handle=ipcMain.handle.bind(ipcMain);
ipcMain.handle=(channel,listener)=>handle(channel,channel!=='creator:request'?listener:async(...args)=>{
 const route=args[1].split('?')[0],at=performance.now(),current=phase;
 try{return await listener(...args);}finally{requests.push({phase:current,route,ms:Math.round(performance.now()-at)});}
});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
app.on('browser-window-created',(_,window)=>{
 window.hide();window.webContents.setBackgroundThrottling(false);
 window.webContents.on('did-finish-load',async()=>{
  if(started)return;started=true;const report={ok:false,output},js=code=>window.webContents.executeJavaScript(code,true);
  async function until(expression){for(let i=0;i<250;i++){if(await js(expression))return;await pause(80);}throw Error('Timed out: '+expression);}
  async function click(text){await js(`(()=>{const e=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()===${JSON.stringify(text)});if(!e||e.disabled)throw Error('Unavailable '+${JSON.stringify(text)});e.click();})()`);await pause(80);}
  try{
   await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`);await pause(900);
   phase='clean-layout';await click('整理布局');await pause(900);
   phase='create';await click('新建');await click('剧情块');await click('创建');
   await until(`!document.querySelector('.flow-quick-create')&&document.querySelector('.statusbar').textContent.startsWith('就绪')`);await pause(1000);
   phase='layout';await click('整理布局');await pause(1000);
   report.frames=await js(`(async()=>{const frames=[];let previous=performance.now();for(let i=0;i<35;i++){await new Promise(requestAnimationFrame);const now=performance.now();frames.push(now-previous);previous=now;}return {median:frames.sort((a,b)=>a-b)[17],max:Math.max(...frames)};})()`);
   report.requests=requests.filter(r=>r.route.includes('/workspace/analyze')||r.route.includes('/workspace/prepare'));
   report.createAnalyses=report.requests.filter(r=>r.phase==='create'&&r.route.endsWith('/analyze')).length;
   report.layoutAnalyses=report.requests.filter(r=>r.phase==='layout'&&r.route.endsWith('/analyze')).length;
   assert.equal(fs.readFileSync(path.join(project,'game','story.rpy'),'utf8'),original);assert.equal(fs.existsSync(path.join(project,'game','creator_scenes.rpy')),false);
   if(process.argv.includes('--verify')){assert.equal(report.createAnalyses,1,'One analysis per visual change');assert.equal(report.layoutAnalyses,0,'Layout must not analyze source');assert.equal(report.requests.filter(r=>r.phase==='clean-layout').length,0,'Clean layout must not analyze source');}
   report.ok=true;
  }catch(error){report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);process.exitCode=1;}
  finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));window.destroy();app.quit();}
 });
});
require('../main.cjs');
