// Trusted out-of-tree DSH plugin. No official-project path or backend token is supplied.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {defineTool} from '@deepseek-ai/dsh-tools';
import {createUserMessage} from '@deepseek-ai/dsh-llm';
import {readGuide,sections} from './knowledge.mjs';
import {ensureSnapshotRead} from './windows-snapshot-read.mjs';
export const name='morinote-ide-tools';
export const inject=['tools','sandbox','attachments'];
const url=process.env.MORINOTE_BRIDGE_URL,token=process.env.MORINOTE_BRIDGE_TOKEN,workspace=path.resolve(process.env.MORINOTE_WORKSPACE),taskId=process.env.MORINOTE_TASK_ID;
const jobs=new Map(),calls=new Map();
const sleep=(ms,signal)=>new Promise((resolve,reject)=>{const timer=setTimeout(done,ms);function done(){signal?.removeEventListener('abort',abort);resolve();}function abort(){clearTimeout(timer);reject(signal.reason||new Error('已取消'));}signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)abort();});
async function bridge(route,body,signal){
 const response=await fetch(url+route,{method:'POST',headers:{Authorization:'Bearer '+token,'content-type':'application/json'},body:JSON.stringify(body),signal,redirect:'error'});
 const value=await response.json();if(!response.ok)throw new Error(value.error||'IDE 工具桥错误');return value;
}
function childEnv(extra={}){
 const env={};for(const key of ['SystemRoot','WINDIR','COMSPEC','PATHEXT','PATH','USERPROFILE','APPDATA','LOCALAPPDATA','ProgramFiles','ProgramFiles(x86)','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'])if(process.env[key])env[key]=process.env[key];
 // Engine's bridge token is task-scoped. No model, DSH or general IDE credential is inherited.
 for(const [key,value] of Object.entries(extra))if(key.startsWith('RENPY_')||key.startsWith('SDL_')||key.startsWith('CREATOR_PREVIEW_')||['CREATOR_BRIDGE_URL','CREATOR_BRIDGE_TOKEN','CREATOR_NATIVE_INDEX','CREATOR_NATIVE_SUPPORT','CREATOR_NATIVE_TEST','CREATOR_NATIVE_TEST_ENTRY','CREATOR_NATIVE_PREVIEW_SUPPORT','PYTHONIOENCODING','PYTHONUTF8','PYTHONDONTWRITEBYTECODE'].includes(key))env[key]=value;
 return env;
}
async function killTree(child){
 if(!child?.pid||child.exitCode!==null)return;
 await new Promise(resolve=>{const killer=spawn(path.join(process.env.SystemRoot||'C:\\Windows','System32/taskkill.exe'),['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore',env:childEnv()});killer.once('exit',resolve);killer.once('error',resolve);});
}
function runnerFailure(confined,code,text){
 if(code===0)return false;
 return confined.runnerFailureRules.some(rule=>(!rule.allowedExitCodes||rule.allowedExitCodes.includes(code))&&text.split(/\r?\n/).some(line=>!rule.informationalLines?.some(s=>s.toLowerCase()===line.toLowerCase())&&rule.fatalSignatures.some(s=>line.toLowerCase().includes(s.toLowerCase()))));
}
async function confinedRun(ctx,descriptor,exec,{terminal=false}={}){
 const executionRoot=path.resolve(descriptor.workspace),snapshots=path.join(workspace,'.creator','ai','tasks')+path.sep;
 if(!executionRoot.startsWith(snapshots)||path.basename(executionRoot)!=='project'||!fs.existsSync(path.join(path.dirname(executionRoot),'task.json')))throw new Error('执行对象不是已登记的隔离目录。');
 const temp=path.join(executionRoot,'.creator','ai-temp');fs.mkdirSync(temp,{recursive:true});
 const policy={mode:'workspace-write',workspaceRoot:executionRoot,sessionId:exec.agent?.session?.id};
 const confined=await ctx.sandbox.confine(descriptor.argv,policy,exec.signal);
 if(!['partial','full'].includes(confined.enforcement)||!confined.argv.length)throw new Error('受限执行后端不可用；已阻止执行。');
 if(terminal){
  if(confined.enforcement!=='partial')throw new Error('Windows 隔离报告与预期不一致；已阻止终端执行。');
  const decision=await bridge('/approval',{callId:String(exec.callId),command:descriptor.command,purpose:descriptor.purpose,cwd:executionRoot,enforcement:{status:confined.enforcement}},exec.signal);
  if(!decision.approved)return {status:'denied',reason:decision.reason};
 }
 exec.signal.throwIfAborted();
 await ensureSnapshotRead(confined,executionRoot,childEnv(),exec.signal);
 const log=path.resolve(descriptor.log);if(!log.startsWith(executionRoot+path.sep))throw new Error('日志目录越界。');fs.mkdirSync(path.dirname(log),{recursive:true});
 const fd=fs.openSync(log,'w');let child;
 try{child=spawn(confined.argv[0],confined.argv.slice(1),{cwd:descriptor.cwd,env:{...childEnv(descriptor.env),TEMP:temp,TMP:temp},windowsHide:true,stdio:['ignore',fd,fd]});}finally{fs.closeSync(fd);}
 const id=descriptor.id||crypto.randomUUID();let timedOut=false;const abort=()=>void killTree(child);exec.signal.addEventListener('abort',abort,{once:true});
 const timeout=descriptor.timeoutMs?setTimeout(()=>{timedOut=true;void killTree(child);},Math.min(descriptor.timeoutMs,600000)):null;
 const settled=new Promise(resolve=>{child.once('error',error=>resolve({code:-1,error:error.message}));child.once('exit',code=>resolve({code:code??130}));});
 const job={child,settled};jobs.set(id,job);
 const complete=settled.then(async({code,error})=>{
  if(timeout)clearTimeout(timeout);exec.signal.removeEventListener('abort',abort);jobs.delete(id);
  const text=fs.existsSync(log)?fs.readFileSync(log,'utf8').slice(-40000):'';
  const failed=runnerFailure(confined,code,text);const value={exitCode:code,log:text,status:timedOut?'timeout':failed?'sandbox_unavailable':error?'failed':code===0?'passed':'failed',enforcement:confined.enforcement,...(error?{error}:{}),...(failed?{reason:'沙箱启动失败，未无限制重试。'}:{})};
  if(descriptor.id&&!terminal){
   value.contentHash=descriptor.contentHash;
   const receipt=await bridge('/execution',{id,code:failed?-1:code}).catch(()=>null);
   value.stale=receipt?.stale??true;
   if(!receipt)value.resultRecorded=false;
  }
  return value;
 });job.complete=complete;
 if(descriptor.background){await sleep(700,exec.signal);if(child.exitCode!==null)return complete;return {status:'started',executionId:id,enforcement:confined.enforcement,contentHash:descriptor.contentHash};}
 return complete;
}
async function imageValue(ctx,value){
 if(!value.image)return value;
 if(process.env.MORINOTE_HAS_VISION!=='1')return {path:value.path,status:'captured',reason:'当前模型未声明图像输入能力。截图已生成，可在 IDE 中查看；需要视觉分析时请选择支持图像的模型。'};
 const attachment=await ctx.attachments.saveImage({data:Buffer.from(value.image.data,'base64'),mediaType:value.image.mimeType,name:path.basename(value.path)});
 return {path:value.path,attachment};
}
function render(_args,value){return [{type:'text',text:JSON.stringify(value)},...(value.attachment?[{type:'image',attachment:value.attachment}]:[])];}
function previewInteractive(status){
 const started=status.events?.findLast(e=>e.type==='started')?.seq||0;
 return status.events?.some(e=>e.seq>started&&['snapshot','node','line'].includes(e.type));
}
export async function apply(ctx){
 let agent,controlling=false;
 const delivered=new Set();
 ctx.on('agent/created',({agent:current})=>{agent=current;});
 ctx.on('agent/disposed',({agent:current})=>{if(agent===current)agent=null;});
 const controlTimer=setInterval(async()=>{if(controlling)return;controlling=true;try{const response=await bridge('/control',{stage:'poll',sessionId:agent?.session.id,status:agent?.status||'idle'});for(const execution of response.executions||[]){if(delivered.has(execution.id))continue;delivered.add(execution.id);const controller=new AbortController();void confinedRun(ctx,execution.descriptor,{signal:controller.signal,callId:execution.id,agent}).then(result=>bridge('/host-execution-result',{id:execution.id,result}),error=>bridge('/host-execution-result',{id:execution.id,result:{status:'failed',reason:String(error.message||error).slice(0,1000)}})).catch(()=>{});}for(const command of response.commands||[]){if(!delivered.has(command.id)){if(!agent||agent.status==='idle'){await bridge('/control',{stage:'ack',id:command.id,accepted:false});continue;}delivered.add(command.id);agent.steer(createUserMessage({content:[{type:'text',text:command.text}],source:{kind:'user'}}));}await bridge('/control',{stage:'ack',id:command.id,accepted:true});}}catch{}finally{controlling=false;}},120);
 ctx.on('dispose',()=>clearInterval(controlTimer));
 let streams=Promise.resolve();
 ctx.on('agent/assistant-stream',({frame})=>{if(frame.type==='chunk'&&frame.chunk?.type==='text-delta')streams=streams.then(()=>bridge('/stream',{frame})).catch(()=>{});});
 const catalog=await bridge('/tool',{name:'catalog',args:{},callId:'catalog-'+crypto.randomUUID()});
 // Refuse accidentally mounted built-in or future tools, including plugin installation.
 ctx.tools.guard(exec=>['skill','read','write','edit'].includes(exec.name)||exec.name.startsWith('morinote_')?undefined:'Morinote 只允许当前项目的受管工具和随附 Skill。');
 if(process.env.MORINOTE_LOW_COST!=='1')ctx.tools.register(defineTool({name:'morinote_guide',description:'Read only the specific guide needed for an actual editing task: architecture, tracks, systems, assets or verification. General discussion and capability questions need no guide or project query. Read-only installation documentation.',parameters:{section:{type:'string',required:true,enum:[...sections],description:'Guide section needed for this task.'}},output:{schema:{type:'json'},render},async execute(args,exec){exec.signal.throwIfAborted();return readGuide(args.section);}}));
 for(const tool of catalog.tools){
  ctx.tools.register(defineTool({name:'morinote_'+tool.name,description:tool.description,parameters:tool.parameters,output:{schema:{type:'json'},render},async execute(args,exec){
   const callId=String(exec.callId);
   if(calls.has(callId))return calls.get(callId);
   const execution=(async()=>{
    let before=tool.name==='screenshot'?await bridge('/tool',{name:'preview_status',args:{},callId:callId+':before'},exec.signal):null;
    // ready is emitted while Ren'Py is entering its startup labels. Commands
    // queued then can be discarded by the initial restart. Wait for the first
    // actual interaction snapshot before requesting an image.
    if(tool.name==='screenshot'){
     for(let attempt=0;attempt<120;attempt++){
      if(['stopped','exited','failed','error'].includes(before.status)||before.error)throw new Error(before.error||'副本试玩已停止，无法截图。');
      if(previewInteractive(before))break;
      await sleep(350,exec.signal);
      before=await bridge('/tool',{name:'preview_status',args:{},callId:callId+':ready:'+attempt},exec.signal);
     }
     if(!previewInteractive(before))throw new Error('副本试玩尚未进入可截图的交互画面。');
    }
    const after=before?.events?.reduce((n,e)=>Math.max(n,e.seq||0),0)||0;
    let value=await bridge('/tool',{name:tool.name,args,callId},exec.signal);
    const candidateVersion=value.candidateVersion;if(value.execution)value=await confinedRun(ctx,value.execution,exec);
    if(['creative_preview','creative_lint'].includes(tool.name))await bridge('/fragment-result',{fragmentId:args.creativeId,phase:tool.name==='creative_preview'?'preview':'lint',result:{...value,candidateVersion}},exec.signal);
    if(tool.name==='stop_preview'){for(const job of jobs.values())await killTree(job.child);}
    if(tool.name==='screenshot'){
     await sleep(400,exec.signal);
     for(let attempt=0;attempt<120;attempt++){
      const status=await bridge('/tool',{name:'preview_status',args:{after},callId:callId+':status:'+attempt},exec.signal);
      if(['stopped','exited','failed','error'].includes(status.status)||status.error)throw new Error(status.error||'副本试玩已停止，无法截图。');
      if(status.events?.some(e=>e.type==='screenshot')){value=await bridge('/tool',{name:'read_image',args:{path:'@preview'},callId:callId+':image'},exec.signal);break;}
      await sleep(350,exec.signal);
     }
     if(!value.image)throw new Error('引擎尚未返回截图，请检查副本试玩状态。');
    }
    return imageValue(ctx,value);
   })();calls.set(callId,execution);return execution;
  }}));
 }
 if(process.env.MORINOTE_LOW_COST!=='1')ctx.tools.register(defineTool({name:'morinote_terminal',description:'Request one PowerShell 7 command in an internal execution snapshot. Host approval follows the selected reviewer; text changes are imported through versioned source transactions. No persistent shell or unrestricted fallback.',parameters:{command:{type:'string',required:true,description:'Exact PowerShell command.'},purpose:{type:'string',required:true,description:'Why this command is necessary.'},timeoutSeconds:{type:'integer',description:'Timeout, at most 600 seconds.'}},output:{schema:{type:'json'},render},async execute(args,exec){
  const callId=String(exec.callId);if(calls.has(callId))return calls.get(callId);
  const command=args.command;if(!command.trim()||command.length>32000)throw new Error('命令为空或过长。');
  const execution=(async()=>{
   const stamp={callId,command,purpose:args.purpose};const receipt=await bridge('/terminal',{...stamp,stage:'begin'},exec.signal);
   if(!receipt.accepted)return receipt.result;
   const executionRoot=receipt.workspace;
   if(typeof executionRoot!=='string')throw new Error('缺少隔离执行目录。');
   const descriptor={workspace:executionRoot,cwd:executionRoot,argv:[process.env.MORINOTE_PWSH,'-NoLogo','-NoProfile','-NonInteractive','-Command',command],command,purpose:args.purpose,env:{},timeoutMs:Math.min(Math.max(args.timeoutSeconds||120,1),600)*1000,log:path.join(executionRoot,'.creator','terminal',crypto.randomUUID()+'.log')};
   const result=await confinedRun(ctx,descriptor,exec,{terminal:true});
   await bridge('/terminal',{...stamp,stage:'finish',result});return result;
  })();calls.set(callId,execution);return execution;
 }}));
 ctx.on('dispose',async()=>{for(const job of jobs.values())await killTree(job.child);await Promise.allSettled([...jobs.values()].map(j=>j.complete));jobs.clear();});
}
