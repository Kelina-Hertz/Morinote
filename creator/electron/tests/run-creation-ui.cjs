// Real renderer, preload, authenticated Python backend and Ren'Py; disposable game/profile only.
const {app}=require('electron');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const output=path.join(root,'.checks','creation-ui',crypto.randomUUID()),profile=path.join(output,'profile'),project=path.join(output,'project');
fs.mkdirSync(path.join(project,'game'),{recursive:true});fs.mkdirSync(profile,{recursive:true});
const source=String.raw`screen main_menu():
    tag menu
    textbutton "Start" action Start()
screen say(who, what):
    text what id "what"
screen choice(items):
    vbox:
        for item in items:
            textbutton item.caption action item.action
default score = 0
label start:
    jump C1a
# morinote-scene: {"title":"邀请开始","group":"第一章"}
label C1a:
    "邀请开始"
    jump accepted
# morinote-scene: {"title":"接受后的场景","group":"第一章"}
label accepted:
    "接受邀请"
    return
# morinote-scene: {"title":"拒绝后的场景","group":"第一章"}
label declined:
    "拒绝邀请"
    return
label setup:
    $ score = 7
    return
`;
const story=path.join(project,'game','story.rpy');fs.writeFileSync(story,source);
fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
app.commandLine.appendSwitch('user-data-dir',profile);app.disableHardwareAcceleration();
const report={project,checks:[],screenshots:[],errors:[]};
const exit=app.exit.bind(app);app.exit=code=>exit(report.ok===false?1:code);
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let started=false;
app.on('browser-window-created',(_event,window)=>{
 window.webContents.setBackgroundThrottling(false);
 window.hide();
 window.webContents.on('console-message',(_event,...args)=>{const d=args[0];if((typeof d==='object'?d.level:args[0])==='error'||args[0]===3)report.errors.push(typeof d==='object'?d.message:args[1]);});
 window.webContents.on('did-finish-load',async()=>{
  if(started)return;started=true;
  const js=code=>window.webContents.executeJavaScript(code,true);
  async function until(expression,label,timeout=25000){const end=Date.now()+timeout;while(Date.now()<end){if(await js(expression))return;await pause(100);}throw new Error(label+'\n'+await js('document.body.innerText.slice(-5000)'));}
  const check=(value,message)=>assert.ok(value,message);
  async function click(text,selector='button'){await js(`(()=>{const b=[...document.querySelectorAll(${JSON.stringify(selector)})].find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!b||b.disabled)throw new Error('Button unavailable: '+${JSON.stringify(text)});b.click();})()`);await pause(80);}
  async function input(label,value){await js(`(()=>{const e=document.querySelector('[aria-label='+CSS.escape(${JSON.stringify(label)})+']');if(!e)throw new Error('Field absent '+${JSON.stringify(label)});const proto=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);await pause(80);}
  async function selectScene(title){await js(`(()=>{const n=[...document.querySelectorAll('.react-flow__node')].find(n=>n.querySelector('strong')?.textContent===${JSON.stringify(title)});if(!n)throw new Error('Scene absent '+${JSON.stringify(title)});n.dispatchEvent(new MouseEvent('click',{bubbles:true}));})()`);await until(`document.querySelector('.inspector h3')?.textContent===${JSON.stringify(title)}`,'Scene selection');}
  async function capture(name){await js('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');await pause(250);const file=path.join(output,name+'.png');fs.writeFileSync(file,(await window.webContents.capturePage()).toPNG());report.screenshots.push(file);}
  async function idle(){await until(`document.querySelector('.native-ide:not([inert])') && !document.querySelector('.statusbar')?.innerText.includes('更新编辑稿')`,'Editor idle');}
  async function save(){await click('保存全部');await until(`document.querySelector('.project-title')?.innerText.includes('源码已保存')`,'Save completion',45000);await pause(600);check(await js(`!document.querySelector('.native-workspace>.error-banner[role=alert]')`),'Saving must not leave a visible error');}
  try{
   await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Workspace startup');
   await selectScene('邀请开始');await click('场景');
   check(await js(`![...document.querySelectorAll('[role=dialog] details')].some(d=>d.open)`),'Scene advanced defaults closed');
   check(await js(`!document.querySelector('[role=dialog]').innerText.includes('标签名称')`),'Technical fields hidden');
   await input('场景名称','邀请的新场景');await capture('01-new-scene');
   await click('添加到编辑稿');await until(`document.querySelector('.inspector h3')?.textContent==='邀请的新场景'`,'Created scene selected');
   check(!fs.existsSync(path.join(project,'game','creator_scenes.rpy')),'Creation must only change draft');
   check(fs.readFileSync(story,'utf8')===source,'Original story untouched');
   await click('打开三轨');await until(`document.querySelector('.native-timeline h1')?.textContent==='邀请的新场景'`,'New scene three-track');
   await js(`document.querySelector('button[aria-label="撤销"]').click()`);await idle();await click('剧情总图');
   await until(`![...document.querySelectorAll('.react-flow__node strong')].some(e=>e.textContent==='邀请的新场景')`,'Undo updates graph');
   await js(`document.querySelector('button[aria-label="重做"]').click()`);
   await until(`!!document.querySelector('.native-timeline')`,'Redo restores scene tab');await click('剧情总图');
   await until(`[...document.querySelectorAll('.react-flow__node strong')].some(e=>e.textContent==='邀请的新场景')`,'Redo updates graph');
   await until(`document.querySelector('.statusbar')?.innerText.includes('草稿已备份')`,'Draft backup');
   window.webContents.reload();await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Draft reload');
   await until(`[...document.querySelectorAll('.react-flow__node strong')].some(e=>e.textContent==='邀请的新场景')`,'Unsaved scene and name recover');
   check(!fs.existsSync(path.join(project,'game','creator_scenes.rpy')),'Recovery does not save source');
   await save();check(fs.readFileSync(path.join(project,'game','creator_scenes.rpy'),'utf8').includes('morinote-scene:'),'Saved source includes display hints');
   report.checks.push('Chinese scene creation, independent draft, three-track display, undo/redo, draft reload, save');

   await selectScene('邀请开始');await click('选项');
   check(await js(`document.querySelector('.creation-form button[type=submit]').disabled`),'Blank choices cannot submit');
   await input('选项 1 文字','接受邀请');await input('选项 1 目标场景','accepted');
   await input('选项 2 文字','拒绝邀请');await input('选项 2 目标场景','declined');
   await input('搜索选项 1 目标场景','接受后的');
   check(await js(`document.querySelector('[aria-label="选项 1 目标场景"]').options.length===2`),'Scene search filters options');
   await input('搜索选项 1 目标场景','');
   await js(`document.querySelector('[aria-label="下移选项 1"]').click()`);await pause(80);
   check(await js(`document.querySelector('[aria-label="选项 1 文字"]').value==='拒绝邀请'`),'Row reordering');
   await js(`document.querySelector('[aria-label="上移选项 2"]').click()`);await pause(80);
   await click('＋ 添加选项');await js(`document.querySelector('[aria-label="删除选项 3"]').click()`);await pause(80);
   await js(`document.querySelector('.creation-advanced').open=true`);await input('选项列表 JSON','{bad');
   await js(`document.querySelector('.creation-advanced').open=false`);
   check(await js(`document.querySelector('.creation-form button[type=submit]').disabled && document.querySelector('.creation-form [role=alert]').textContent.includes('JSON')`),'Invalid JSON cannot silently submit when collapsed');
   await click('放弃无效 JSON，恢复表单');
   check(await js(`document.querySelector('[aria-label="选项 1 文字"]').value==='接受邀请'`),'Discard keeps last valid rows');
   await capture('02-choice-form');await click('添加到编辑稿');await until(`!document.querySelector('[role=dialog]')`,'Choice submitted');
   check(fs.readFileSync(story,'utf8')===source,'Choice stays in draft');
   await save();const written=fs.readFileSync(story,'utf8');
   check(written.includes("'接受邀请':")&&written.indexOf("'接受邀请':")<written.indexOf("'拒绝邀请':"),'Menu order and literal text saved');
   report.checks.push('Structured choices, scene search, reorder/add/delete, JSON error/discard, native menu save');

   const config={args:'[]',state:'{"score":3}',initialize:'["setup"]'};
   await js(`(async()=>{const c=await window.creator.request('/api/project');await window.creator.request('/api/workspace/metadata',{revision:c.project.revision,ide:{...c.project.ide,testEntry:{label:'accepted',...${JSON.stringify(config)}}}});})()`);
   window.webContents.reload();await until(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`,'Reload');
   await click('片段测试','.app-header button');
   check(await js(`!document.querySelector('[role=dialog] details').open`),'Preview advanced defaults closed');
   check(await js(`document.querySelector('[aria-label="起始场景"]').value==='accepted'`),'Saved test target preserved');
   check(await js(`document.querySelector('[role=dialog]').innerText.includes('已使用高级配置')`),'Hidden active config is disclosed');
   await capture('03-preview-simple');
   await js(`document.querySelector('[role=dialog] details').open=true`);await input('标签参数 JSON','{bad');
   check(await js(`document.querySelector('[role=dialog] [role=alert]').innerText.includes('标签参数')`),'Field-specific preview validation');
   await input('标签参数 JSON','[]');await capture('04-preview-advanced');
   await click('保存测试入口');await until(`document.querySelector('[role=dialog]')?.innerText.includes('测试入口已保存')`,'Test profile saved');
   await js(`document.querySelector('[role=dialog] details').open=false`);await click('仅试玩此片段');
   await until(`!document.querySelector('[role=dialog]')`,'Preview dialog closes only after success');
   await until(`(async()=>{const s=await window.creator.request('/api/preview/status?after=0');if(s.status==='error')throw new Error(s.error);return s.status==='running'&&s.runtime?.state?.score===7;})()`,'Native preview receives saved advanced fields',45000);
   await js(`document.querySelector('button[aria-label="停止预览"]').click()`);
   report.checks.push('Saved test selection, collapsed active advanced settings, validation, real RenPy preview with initializer');
   await capture('05-complete');check(report.errors.length===0,'No renderer errors: '+report.errors.join('\n'));
   report.ok=true;
  }catch(error){report.ok=false;report.error=String(error.stack||error);report.body=await js('document.body.innerText').catch(()=>null);await capture('failure').catch(()=>{});}
  finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.ok)process.exitCode=1;window.close();}
 });
});
require('../main.cjs');
