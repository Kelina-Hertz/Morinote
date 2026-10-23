// One focused UI check, entirely in a disposable project; never launch or save a game.
const {app,ipcMain,nativeImage}=require('electron'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),output=path.join(root,'.checks','media-timeline-performance',crypto.randomUUID());
const profile=path.join(output,'profile'),project=path.join(output,'project'),images=path.join(project,'game/images/characters/hero');
fs.mkdirSync(images,{recursive:true});fs.mkdirSync(profile,{recursive:true});
const png=nativeImage.createFromBitmap(Buffer.from([130,110,80,255]),{width:1,height:1}).toPNG();
for(let i=0;i<180;i++)fs.writeFileSync(path.join(images,'portrait'+String(i).padStart(3,'0')+'.png'),png);
const original='image bg0 = "#334455"\nimage bg1 = "#556677"\n# morinote-scene: {"title":"长场景","group":"剧情"}\nlabel start:\n'+Array.from({length:127},(_,i)=>(i%3===0?`    scene bg${Math.floor(i/3)%2}\n`:'')+`    "第 ${i+1} 句台词"\n`).join('')+'    return\n';
fs.writeFileSync(path.join(project,'game/story.rpy'),original);fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
let started=false,latest,failed=false;const exit=app.exit.bind(app);app.exit=code=>exit(failed?1:code);
const handle=ipcMain.handle.bind(ipcMain);ipcMain.handle=(channel,listener)=>handle(channel,channel!=='creator:request'?listener:async(...args)=>{const result=await listener(...args);if(args[1]==='/api/workspace/analyze')latest=result;return result;});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
app.on('browser-window-created',(_,window)=>{window.hide();window.webContents.setBackgroundThrottling(false);window.webContents.on('did-finish-load',async()=>{
 if(started)return;started=true;const report={ok:false,output},js=code=>window.webContents.executeJavaScript(code,true);
 async function until(code,label){for(let i=0;i<180;i++){if(await js(code))return;await pause(80);}throw Error(label+'\n'+await js('document.body.innerText'));}
 async function click(text){await js(`(()=>{const e=[...document.querySelectorAll('button')].find(e=>(e.textContent.trim()===${JSON.stringify(text)}||e.getAttribute('aria-label')===${JSON.stringify(text)}));if(!e||e.disabled)throw Error('Missing button '+${JSON.stringify(text)});e.click();})()`);await pause(100);}
 try{
  await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Project loaded');
  await click('项目素材库');await until(`!!document.querySelector('.windowed-grid .asset-card')`,'Asset gallery');
  report.gallery=await js(`(()=>{const g=document.querySelector('.windowed-grid');return {mounted:g.querySelectorAll('.asset-card').length,total:Number(g.querySelector('[role=listitem]').getAttribute('aria-setsize')),height:g.clientHeight,scroll:g.scrollHeight};})()`);
  assert(report.gallery.total>=180);assert(report.gallery.mounted<40);assert(report.gallery.height>150);
  await until(`!!document.querySelector('.windowed-grid img[src*="thumbnail="]')`,'Thumbnail URLs');
  await until(`!![...document.querySelectorAll('.windowed-grid img')].find(i=>i.complete&&i.naturalWidth>0)`,'Thumbnails decoded');
  fs.writeFileSync(path.join(output,'gallery.png'),(await window.webContents.capturePage()).toPNG());
  await js(`document.querySelector('.windowed-grid').scrollTop=999999`);await pause(350);
  assert.equal(await js(`!![...document.querySelectorAll('.windowed-grid b')].find(e=>e.textContent==='portrait179')`),true);
  await js(`(()=>{const input=document.querySelector('[aria-label="搜索素材"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'portrait017');input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  await until(`document.querySelectorAll('.windowed-grid .asset-card').length===1`,'Search resets virtual scroll');
  await js(`document.querySelector('.virtual-bind-button').click()`);await until(`!!document.querySelector('.virtual-target-grid')`,'Binding picker');
  assert((await js(`document.querySelectorAll('.virtual-target').length`))<40);
  await js(`document.querySelector('.modal [aria-label="关闭"]').click()`);
  await click('剧情总图');await until(`!!document.querySelector('.react-flow__node')`,'Back to graph');
  await js(`(()=>{const n=[...document.querySelectorAll('.react-flow__node')].find(n=>n.querySelector('strong')?.textContent==='长场景');if(!n)throw Error('Missing scene');n.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,button:0}));})()`);
  await until(`!!document.querySelector('.web-text-row textarea')`,'Timeline opened');await pause(300);
  report.timeline=await js(`({total:document.querySelectorAll('.web-text-row').length,mounted:document.querySelectorAll('.web-text-row textarea').length,stages:document.querySelectorAll('.web-visual-segment .stage').length})`);
  assert.equal(report.timeline.total,127);assert(report.timeline.mounted<20);assert(report.timeline.stages<10);
  await js(`(()=>{const t=document.querySelector('.web-text-row textarea');t.focus();Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(t,'保留未提交输入');t.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.web-timeline-scroll').scrollTop=999999;})()`);await pause(400);
  assert.equal(await js(`document.activeElement.value`),'保留未提交输入');
  await until(`[...document.querySelectorAll('.web-text-row textarea')].some(t=>t.value==='第 127 句台词')`,'Last rows mounted');
  report.blankVisibleStages=await js(`(()=>{const r=document.querySelector('.web-timeline-scroll').getBoundingClientRect();return [...document.querySelectorAll('.web-visual-segment')].filter(e=>{const b=e.getBoundingClientRect();return b.bottom>r.top+45&&b.top<r.bottom&&!e.querySelector('.stage');}).length;})()`);
  assert.equal(report.blankVisibleStages,0,'Visible shared segments must mount their stage');
  await js(`document.activeElement.blur()`);await until(`document.querySelector('.statusbar').textContent.startsWith('就绪')&&document.querySelector('.statusbar').textContent.includes('更改未保存')`,'Blur edit analyzed');
  assert.equal(latest.project.scenes[0].lines[0].text,'保留未提交输入');
  await click('撤销');await until(`document.querySelector('.statusbar').textContent.startsWith('就绪')`,'Undo');assert.equal(latest.project.scenes[0].lines[0].text,'第 1 句台词');
  await click('重做');await until(`document.querySelector('.statusbar').textContent.startsWith('就绪')`,'Redo');assert.equal(latest.project.scenes[0].lines[0].text,'保留未提交输入');
  await js(`document.querySelector('.web-timeline-scroll').scrollTop=0`);await pause(300);
  fs.writeFileSync(path.join(output,'timeline.png'),(await window.webContents.capturePage()).toPNG());
  assert.equal(fs.readFileSync(path.join(project,'game/story.rpy'),'utf8'),original);
  report.ok=true;
 }catch(error){failed=true;report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);fs.writeFileSync(path.join(output,'failure.png'),(await window.webContents.capturePage()).toPNG());}
 finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await pause(250);window.destroy();app.quit();}
});});
require('../main.cjs');
