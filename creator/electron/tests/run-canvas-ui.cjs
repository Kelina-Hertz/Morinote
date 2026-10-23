// One canvas smoke check in a disposable project. Does not start a game or save story files.
const {app}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),output=path.join(root,'.checks','canvas-ui',crypto.randomUUID());
const profile=path.join(output,'profile'),project=path.join(output,'project');
fs.mkdirSync(path.join(project,'game'),{recursive:true});fs.mkdirSync(profile,{recursive:true});
const original='default score = 0\n# morinote-scene: {"title":"起点","group":"剧情"}\nlabel start:\n    jump before\n# morinote-scene: {"title":"原剧情","group":"剧情"}\nlabel before:\n    "原剧情"\n    return\n# morinote-scene: {"title":"独立片段","group":"剧情"}\nlabel insertable:\n    "独立片段"\n    return\n';
fs.writeFileSync(path.join(project,'game','story.rpy'),original);
fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let started=false,failed=false;
const exit=app.exit.bind(app);app.exit=code=>exit(failed?1:code);
app.on('browser-window-created',(_event,window)=>{
 window.hide();window.webContents.setBackgroundThrottling(false);
 window.webContents.on('console-message',(_event,...args)=>{const detail=args[0];if(typeof detail==='object'?detail.level==='error':detail===3)console.error('renderer:',typeof detail==='object'?detail.message:args[1]);});
 window.webContents.on('did-finish-load',async()=>{
  if(started)return;started=true;
  const js=code=>window.webContents.executeJavaScript(code,true),report={ok:false,output};
  async function until(expression,label){const end=Date.now()+25000;while(Date.now()<end){if(await js(expression))return;await pause(100);}throw Error(label+'\n'+await js('document.body.innerText.slice(-3500)'));}
  async function click(text,selector='button'){await js(`(()=>{const b=[...document.querySelectorAll(${JSON.stringify(selector)})].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!b||b.disabled)throw Error('Unavailable button '+${JSON.stringify(text)});b.click();})()`);await pause(80);}
  async function input(label,value){await js(`(()=>{const e=document.querySelector('[aria-label='+CSS.escape(${JSON.stringify(label)})+']');if(!e)throw Error('Missing field '+${JSON.stringify(label)});e.focus();Object.getOwnPropertyDescriptor(e.tagName==='SELECT'?HTMLSelectElement.prototype:e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);await pause(80);}
  async function create(kind){await click('新建');await click(kind);await until(`!!document.querySelector('.flow-quick-create')`,'Canvas form');assert.equal(await js(`!!document.querySelector('[role=dialog]')`),false);}
  async function outlet(label){await js(`(()=>{const e=document.querySelector('[aria-label='+CSS.escape(${JSON.stringify(label)})+']');if(!e||e.disabled)throw Error('Unavailable outlet');const r=e.getBoundingClientRect();e.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:r.x+r.width/2,clientY:r.y+r.height/2}));})()`);await pause(80);}
  async function fit(){await js(`document.querySelector('.react-flow__controls-fitview').click()`);await pause(600);}
  async function drag(sourceTitle,targetTitle,port='.flow-edit-handle'){
   await until(`document.querySelector('.statusbar')?.textContent.startsWith('就绪')`,'Editor ready to connect');
   await fit();
   await js(`(async()=>{const all=[...document.querySelectorAll('.react-flow__node')];const node=t=>all.find(n=>n.querySelector('strong')?.textContent===t);const from=node(${JSON.stringify(sourceTitle)})?.querySelector(${JSON.stringify(port)}),to=node(${JSON.stringify(targetTitle)})?.querySelector('.react-flow__handle.target');if(!from||!to)throw Error('Missing drag handles');const a=from.getBoundingClientRect(),b=node(${JSON.stringify(targetTitle)}).getBoundingClientRect(),x=a.x+a.width/2,y=a.y+a.height/2,tx=b.x+b.width*.6,ty=b.y+b.height*.5;from.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0,buttons:1,clientX:x,clientY:y,view:window}));for(let i=1;i<=8;i++){document.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,buttons:1,clientX:x+(tx-x)*i/8,clientY:y+(ty-y)*i/8,view:window}));await new Promise(r=>setTimeout(r,25));}to.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0,clientX:tx,clientY:ty,view:window}));})()`);
  }
  try{
   await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Workspace startup');
   await create('选项分支');await input('选项 1 文字','接受邀请');await input('选项 2 文字','拒绝邀请');
   await js(`document.querySelector('.flow-quick-advanced').open=true`);await click('编辑选项 JSON');await input('选项列表 JSON','[{');
   assert.equal(await js(`document.querySelector('.flow-quick-actions .primary').disabled`),true);
   await js(`document.querySelector('.flow-quick-advanced').open=false`);
   assert.equal(await js(`document.body.innerText.includes('选项 JSON 格式不正确')`),true);
   await click('放弃 JSON 修改');await click('创建');
   assert.equal(await js(`!!document.querySelector('[role=dialog]')`),false);
   await until(`[...document.querySelectorAll('.react-flow__node')].some(n=>n.querySelector('strong')?.textContent==='剧情分支'&&n.querySelectorAll('.flow-edit-handle').length===2)`,'Branch block with two ports');
   await until(`!document.querySelector('.flow-quick-create')&&!document.querySelector('[aria-label="选项文字：拒绝邀请"]').disabled`,'Quick creation finished');
   await until(`(()=>{const n=document.querySelector('[aria-label="选项文字：拒绝邀请"]')?.closest('.react-flow__node'),b=n?.getBoundingClientRect(),c=document.querySelector('.global-flow-canvas').getBoundingClientRect();return b&&b.left>=c.left&&b.right<=c.right&&b.top>=c.top&&b.bottom<=c.bottom;})()`,'New node stays in viewport');
   await input('选项文字：拒绝邀请','暂不接受');
   await js(`document.querySelector('[aria-label="选项文字：拒绝邀请"]').dispatchEvent(new FocusEvent('focusout',{bubbles:true,relatedTarget:document.body}))`);
   await until(`!!document.querySelector('[aria-label="选项文字：暂不接受"]')`,'Inline option rename');
   await outlet('在暂不接受后新建');await click('结束此段','[role=menu] button');
   await until(`document.querySelector('[aria-label="选项文字：暂不接受"]')?.closest('.flow-outlet').textContent.includes('结束此段')`,'Explicit ending');
   await js(`document.querySelector('button[aria-label="撤销"]').click()`);
   await until(`document.querySelector('[aria-label="选项文字：暂不接受"]')?.closest('.flow-outlet').textContent.includes('待连接')`,'Undo restores pending');
   await js(`document.querySelector('button[aria-label="重做"]').click()`);
   await until(`document.querySelector('[aria-label="选项文字：暂不接受"]')?.closest('.flow-outlet').textContent.includes('结束此段')`,'Redo restores ending');
   await outlet('在接受邀请后新建');await click('剧情块');await input('剧情块名称','邀请后续');await click('创建');
   await until(`[...document.querySelectorAll('.react-flow__node strong')].some(n=>n.textContent==='邀请后续')`,'Create connected scene');
   await drag('邀请后续','原剧情');
   await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已连接：邀请后续')`,'Direct connection without dialog');
   assert.equal(await js(`!!document.querySelector('[role="dialog"]')`),false);
   await create('条件判断');assert.equal(await js(`!!document.querySelector('[aria-label="剧情块名称"]')`),false);
   await input('判断变量','score');await input('比较方式','>=');await input('比较值','3');
   fs.writeFileSync(path.join(output,'condition-form.png'),(await window.webContents.capturePage()).toPNG());await click('创建');
   await until(`[...document.querySelectorAll('.react-flow__node')].some(n=>n.querySelector('strong')?.textContent==='score ≥ 3'&&n.querySelector('[aria-label="连接是"]')&&n.querySelector('[aria-label="连接否"]'))`,'Readable condition with yes/no ports');
   await fit();
   await js(`(async()=>{const all=[...document.querySelectorAll('.react-flow__node')],node=t=>all.find(n=>n.querySelector('strong')?.textContent===t),source=node('起点'),target=node('原剧情'),moving=node('独立片段');const edge=[...document.querySelectorAll('.react-flow__edge')].find(e=>e.getAttribute('aria-label')==='Edge from '+source.dataset.id+' to '+target.dataset.id),line=edge?.querySelector('.react-flow__edge-path');if(!line)throw Error('Insertion edge absent');const matrix=line.getScreenCTM(),point=line.getPointAtLength(line.getTotalLength()*.5).matrixTransform(matrix),box=moving.getBoundingClientRect(),handle=moving.querySelector('strong'),h=handle.getBoundingClientRect(),x=h.x+h.width/2,y=h.y+h.height/2,tx=x+point.x-(box.x+box.width/2),ty=y+point.y-(box.y+box.height/2);handle.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0,buttons:1,clientX:x,clientY:y,view:window}));for(let i=1;i<=12;i++){document.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,buttons:1,clientX:x+(tx-x)*i/12,clientY:y+(ty-y)*i/12,view:window}));await new Promise(r=>setTimeout(r,30));}await new Promise(r=>setTimeout(r,100));if(!document.querySelector('.flow-canvas-hint').textContent.includes('松开插入'))throw Error('Insertion preview absent');document.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0,clientX:tx,clientY:ty,view:window}));})()`);
   await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已插入：起点 → 独立片段 → 原剧情')`,'Drag an existing block into a connection');
   await click('整理布局');await fit();
   await drag('独立片段','剧情分支');
   await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已连接：独立片段')`,'Branch joins main flow');
   await drag('邀请后续','score ≥ 3');
   await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已连接：邀请后续')`,'Condition joins accepted branch');
   await drag('score ≥ 3','原剧情','[aria-label="连接是"]');
   await until(`document.querySelector('.flow-connection-feedback')?.textContent.includes('已连接：score ≥ 3 → 原剧情')`,'True condition connects');
   await outlet('在否后新建');await click('结束此段','[role=menu] button');
   await until(`[...document.querySelectorAll('.react-flow__node')].find(n=>n.querySelector('strong')?.textContent==='score ≥ 3')?.textContent.includes('结束此段')`,'False condition ends');
   await js(`document.querySelector('.react-flow__pane').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);await click('整理布局');
   await fit();fs.writeFileSync(path.join(output,'canvas.png'),(await window.webContents.capturePage()).toPNG());
   await js(`(()=>{const n=[...document.querySelectorAll('.react-flow__node')].find(n=>n.querySelector('strong')?.textContent==='原剧情');n.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,button:0}));})()`);
   await until(`!!document.querySelector('[aria-label="本句文字"]')`,'Double click opens content editor');
   await input('本句文字','修改后的原剧情');await js(`document.activeElement.blur()`);
   await until(`document.querySelector('.statusbar').textContent.includes('更改未保存')`,'Content edits are drafts');
   assert.equal(fs.existsSync(path.join(project,'game','creator_scenes.rpy')),false);
   assert.equal(fs.readFileSync(path.join(project,'game','story.rpy'),'utf8'),original);
   report.ok=true;report.checks='Shared canvas creation, invalid JSON retained until abandoned, inline options, pending versus explicit ending with undo/redo, quick connected creation, whole-node drag target, condition state picker and readable name, drag-to-insert, double click content editing, draft-only edits';
  }catch(error){failed=true;report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);report.nodes=await js(`[...document.querySelectorAll('.react-flow__node')].map(n=>({id:n.dataset.id,text:n.textContent,style:n.getAttribute('style')}))`).catch(()=>null);fs.writeFileSync(path.join(output,'failure.png'),(await window.webContents.capturePage()).toPNG());}
  finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.ok)process.exitCode=1;window.destroy();app.quit();}
 });
});
require('../main.cjs');
