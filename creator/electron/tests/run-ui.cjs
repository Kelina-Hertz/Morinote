// Real Electron + preload + authenticated Python service, with isolated data.
// Invoke with electron.exe electron/tests/run-ui.cjs; never loads the user's profile.
const {app}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..');
const fixture=process.env.CREATOR_UI_FIXTURE;
if(!fixture||!fs.existsSync(path.join(fixture,'game')))throw new Error('Set CREATOR_UI_FIXTURE to a disposable native game.');
const output=path.join(root,'.checks','desktop-ui'),run=path.join(output,crypto.randomUUID()),profile=path.join(run,'profile'),project=path.join(run,'project');
function copyGame(source,target){fs.mkdirSync(target,{recursive:true});for(const entry of fs.readdirSync(source,{withFileTypes:true})){if(['cache','saves','__pycache__'].includes(entry.name))continue;const a=path.join(source,entry.name),b=path.join(target,entry.name);if(entry.isDirectory())copyGame(a,b);else if(entry.isFile()){if(/\.(?:rpy|py|json|txt)$/i.test(entry.name))fs.copyFileSync(a,b);else{try{fs.linkSync(a,b);}catch{fs.copyFileSync(a,b);}}}}}
copyGame(path.join(fixture,'game'),path.join(project,'game'));
fs.mkdirSync(profile,{recursive:true});fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);
app.disableHardwareAcceleration();
const report={checks:[],errors:[],project,profile};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let started=false;
app.on('browser-window-created',(_event,window)=>{
 window.hide();
 window.webContents.on('console-message',(_event,...args)=>{const details=args[0];const level=typeof details==='object'?details.level:args[0],message=typeof details==='object'?details.message:args[1];if(level==='error'||level===3)report.errors.push(String(message));});
 window.webContents.on('did-finish-load',async()=>{
  if(started)return;started=true;
  const js=code=>window.webContents.executeJavaScript(code,true);
  async function until(expression,message,timeout=20000){const end=Date.now()+timeout;while(Date.now()<end){if(await js(expression))return;await pause(100);}throw new Error(message+'\n'+await js('document.body.innerText.slice(0,4000)'));}
  async function click(text){await js(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()===${JSON.stringify(text)});if(!b)throw new Error('Button absent: '+${JSON.stringify(text)});b.click();})()`);}
  try{
   await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Native workspace did not load');
   await until(`document.body.innerText.includes('百团巡游 · 寻找动漫社') && document.body.innerText.includes('章节收尾')`,'Story cards did not finish mounting');
   const content=await js('document.body.innerText');
   for(const title of ['百团巡游 · 寻找动漫社','摊位初遇 · 汐泉与渡鸥','章节收尾'])if(!content.includes(title))throw new Error('Missing flow title: '+title);
   if(/API Key|AI 侧栏/.test(content))throw new Error('AI UI leaked into offline edition');
   report.checks.push('native workspace renders readable chapter flow with offline UI');
   fs.writeFileSync(path.join(output,'flow.png'),(await window.webContents.capturePage()).toPNG());
   await js(`document.querySelectorAll('.react-flow__node').forEach(n=>{if(n.innerText.includes('摊位初遇 · 汐泉与渡鸥'))n.dispatchEvent(new MouseEvent('click',{bubbles:true}));})`);
   await until(`!![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='打开三轨')`,'Flow selection did not show scene actions');
   await click('打开三轨');
   await until(`!!document.querySelector('.native-timeline textarea[aria-label="本句文字"]')`,'Three-track scene did not load');
   report.checks.push('scene click selects correct scene and opens editable three-track timeline');
   const documentPath=path.join(project,'game','script_c1b.rpy'),original=fs.readFileSync(documentPath);
   await js(`(()=>{const t=document.querySelector('.native-timeline textarea[aria-label="本句文字"]');t.focus();Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,t.value+'【恢复测试】');t.dispatchEvent(new Event('input',{bubbles:true}));t.blur();})()`);
   await until(`document.querySelector('.statusbar')?.innerText.includes('源码未保存')`,'Timeline edit did not mark source dirty');
   await until(`document.querySelector('.statusbar')?.innerText.includes('草稿已备份')`,'Autosave did not complete');
   if(!fs.readFileSync(documentPath).equals(original))throw new Error('Draft autosave changed original RPY');
   report.checks.push('timeline edit enters buffer and recovery backup without changing disk source');
   fs.writeFileSync(path.join(output,'timeline.png'),(await window.webContents.capturePage()).toPNG());
   await click('项目素材库');
   await until(`!!document.querySelector('.virtual-library .asset-type-tabs')`,'Virtual asset library did not load');
   const assetText=await js(`document.querySelector('.virtual-library').innerText`);
   for(const title of ['立绘','背景','CG','BGM'])if(!assetText.includes(title))throw new Error('Missing asset tab '+title);
   if(!assetText.includes('汐泉'))throw new Error('Known character role was lost during import');
   await until(`[...document.querySelectorAll('.virtual-library .asset-grid img')].some(i=>i.complete&&i.naturalWidth>0)`,'Registered portrait thumbnail did not load');
   report.checks.push('project-scoped virtual asset library opens with separate material tabs');
   fs.writeFileSync(path.join(output,'assets.png'),(await window.webContents.capturePage()).toPNG());
   await click('摊位初遇 · 汐泉与渡鸥');await until(`!!document.querySelector('.native-timeline')`,'Scene tab failed to reopen');await click('源码');
   await until(`!!document.querySelector('.monaco-editor')`,'Monaco source editor failed to load');
   report.checks.push('scene source action opens bundled Monaco editor');
   await until(`(async()=>{const context=await window.creator.request('/api/project');const backup=await window.creator.recovery('current',{projectSession:context.session});return backup.state?.active?.startsWith('code:');})()`,'Code tab layout was not backed up');
   window.webContents.reload();await pause(300);
   await until(`!!document.querySelector('.native-ide:not([inert]) .monaco-editor')`,'Source tabs did not recover after reload');
   await until(`document.querySelector('.statusbar')?.innerText.includes('源码未保存')`,'Unsaved timeline edits did not recover');
   if(!fs.readFileSync(documentPath).equals(original))throw new Error('Reload recovery wrote to original RPY');
   report.checks.push('reload restores source tabs and unsaved draft while original file remains intact');
   if(report.errors.length)throw new Error('Renderer errors: '+report.errors.join('\n'));
   report.ok=true;
  }catch(error){report.ok=false;report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);}
  finally{
   fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));
   console.log(JSON.stringify(report));
   window.close();
  }
 });
});
require('../main.cjs');
