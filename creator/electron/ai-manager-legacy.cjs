'use strict';
// Only this host can prepare an apply; the plugin bridge never exposes it.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const {spawn}=require('node:child_process');
const {SecureStore,atomicWrite}=require('./ai-storage.cjs');
const {redact}=require('./security.cjs');
const PIN='22ddee3792402c3e70ec5f86a63c3e3e895a2f60';
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function cleanEnv(extra={}){
 const env={};for(const key of ['SystemRoot','WINDIR','COMSPEC','PATHEXT','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','ProgramFiles','ProgramFiles(x86)','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'])if(process.env[key])env[key]=process.env[key];
 return {...env,...extra};
}
class AIManager{
 constructor({directory,base,safeStorage,request,context}){
  this.directory=directory;this.base=base;this.request=request;this.context=context;
  this.store=new SecureStore(directory,safeStorage);this.worker=null;this.running=false;this.approvals=new Map();this.events=[];this.sequence=0;this.scope=null;this.rpc=new Map();this.epoch=0;this.serial=Promise.resolve();this.bridge=null;
  this.runtime=path.join(base,'ai-runtime');
  // The standalone Node process cannot load Electron's virtual app.asar paths.
  const bundledWorker=path.join(base,'dsh-worker.mjs');
  this.workerFile=fs.existsSync(bundledWorker)?bundledWorker:path.join(__dirname,'dsh-worker.mjs');
 }
 runtimeInfo(){
  const node=path.join(this.runtime,'node','node.exe'),pwsh=path.join(this.runtime,'pwsh','pwsh.exe'),manifest=path.join(this.runtime,'manifest.json');let available=false,reason='缺少锁定版本的 DSH、Node、PowerShell 或随附 IDE Skill，请更新完整免安装包。';
  try{const value=JSON.parse(fs.readFileSync(manifest,'utf8'));available=value.commit===PIN&&value.version==='0.2.1-rc.3'&&value.node==='25.8.2'&&fs.existsSync(node)&&fs.existsSync(pwsh)&&fs.existsSync(this.workerFile)&&fs.existsSync(path.join(this.runtime,'node_modules/@deepseek-ai/dsh-sdk-client/lib/index.js'))&&fs.existsSync(path.join(this.runtime,'skills/morinote-ide/SKILL.md'))&&fs.existsSync(path.join(this.runtime,'plugin/knowledge.mjs'));if(available)reason='';}catch{}
  return {version:'0.2.1-rc.3',commit:PIN,available,reason};
 }
 assertScope(payload){const c=this.context();if(!payload?.projectSession||c?.session!==payload.projectSession||!c?.root)throw new Error('项目已切换，AI 请求已拒绝。');return c;}
 async backend(action,payload={}){if(!this.scope)throw new Error('AI 项目会话不可用');return this.request('/api/ai/'+action,{...payload,projectSession:this.scope.session});}
 async bind(context){
  if(this.binding){await this.binding;if(this.scope?.session===context.session)return;}
  if(this.scope?.session===context.session)return;
  const pending=this.bindContext(context);this.binding=pending;try{await pending;}finally{if(this.binding===pending)this.binding=null;}
 }
 async bindContext(context){
  await this.stop();this.scope={...context};this.events=[];this.sequence=0;
  this.historyFile=path.join(this.directory,'ai-history',crypto.createHash('sha256').update(path.resolve(context.root)).digest('hex')+'.json');
  try{const history=JSON.parse(fs.readFileSync(this.historyFile,'utf8'));this.events=history.events||[];this.sequence=this.events.at(-1)?.seq||0;}catch{}
  // An interrupted task is resumable, never silently re-executed on startup.
  const {tasks}=await this.backend('list');for(const task of tasks)if(['running','waiting_user'].includes(task.status))await this.backend('mark',{taskId:task.id,values:{status:'cancelled',error:'上次执行已中断，可审核已有修改或手动继续。'}});
 }
 event(type,data,taskId=this.taskId){
  const secrets=[this.credentials?.key,this.bridgeToken].filter(Boolean);let safe=redact(data,secrets);
  if(typeof safe==='object'&&safe!==null){safe=JSON.parse(JSON.stringify(safe,(_key,value)=>typeof value==='string'&&value.length>100000?value.slice(0,100000)+'…':value));}
  const previous=this.events.at(-1);
  if(type==='text')this.events=this.events.filter(e=>!(e.taskId===taskId&&e.type==='stream'));
  if(type==='text'&&previous?.taskId===taskId&&previous.type==='text'&&typeof previous.data==='string'&&typeof safe==='string'&&previous.data.length<100000)previous.data+=safe;
  else this.events.push({seq:++this.sequence,taskId,type,data:safe,time:Date.now()});
  this.events=this.events.slice(-1200);
  clearTimeout(this.historyTimer);this.historyTimer=setTimeout(()=>{const file=this.historyFile,events=JSON.stringify({version:1,events:this.events});this.serial=this.serial.then(()=>atomicWrite(file,events)).catch(()=>{this.persistenceError='AI 会话记录写入失败，当前修改仍在任务副本中。';});},150);
 }
 handle(method,payload){
  if(['status','approve','cancel'].includes(method))return this.handleRequest(method,payload);
  const next=(this.actions||Promise.resolve()).then(()=>this.handleRequest(method,payload));this.actions=next.catch(()=>{});return next;
 }
 async handleRequest(method,payload){
  const context=this.assertScope(payload);await this.bind(context);this.assertScope(payload);
  if(method==='status'){const {tasks}=await this.backend('list');return {settings:{...this.store.settings(),...(this.persistenceError?{storageWarning:this.persistenceError}:{}),runtime:this.runtimeInfo()},tasks,events:this.events,approvals:[...this.approvals.values()].map(a=>a.public)};}
  if(method==='configure'){if(this.running)throw new Error('请先取消当前 AI 执行，再修改模型。');return this.store.configure(payload);}
  if(method==='preferences')return this.store.preferences({autoSave:payload.autoSave});
  if(method==='cancel'){await this.stop();return {cancelled:true};}
  if(method==='approve')return this.approve(payload.id,payload.allow);
  if(method==='diff'||method==='rebase'){
   if(this.running)throw new Error('请先等待或取消 AI 执行，再审核修改。');return this.backend(method,{...payload});
  }
  if(method==='prepare'){
   if(this.running)throw new Error('AI 仍在修改副本。');return this.backend('prepare',payload);
  }
  if(method==='applied'){
   const diff=await this.backend('diff',{taskId:payload.taskId});if(diff.reviewHash!==payload.reviewHash)throw new Error('副本又发生了变化，请重新审核。');
   return this.backend('mark',{taskId:payload.taskId,values:{status:'applied'}});
  }
  if(method==='start'||method==='continue'||method==='connection'){
   if(this.running)throw new Error('已有 AI 任务正在执行。');
   const info=this.runtimeInfo();if(!info.available)throw new Error(info.reason);
   if(method!=='continue')this.credentials=this.store.config();
   if(method==='connection')return this.connection();
   const capturedEpoch=this.epoch;let task,prior,dialogue='';
   if(method==='start'&&payload.previousTaskId){
    const {tasks}=await this.backend('list');prior=tasks.find(t=>t.id===payload.previousTaskId);
    if(!prior||prior.status!=='applied')throw new Error('请先完成当前修改的审核，再继续应用后的对话。');
    const conversationId=prior.conversationId||prior.id,ids=new Set(tasks.filter(t=>(t.conversationId||t.id)===conversationId).map(t=>t.id));
    dialogue=this.events.filter(e=>ids.has(e.taskId)&&['user','text'].includes(e.type)&&typeof e.data==='string').slice(-16).map(e=>({role:e.type==='user'?'user':'assistant',text:e.data}));
    dialogue=JSON.stringify(dialogue.map(entry=>({...entry,text:entry.text.slice(-1200)})));
   }
   if(method==='start'){
    task=await this.backend('new',{prompt:payload.prompt,state:payload.state,context:payload.context});
    if(prior)task=await this.backend('mark',{taskId:task.id,values:{conversationId:prior.conversationId||prior.id,parentTaskId:prior.id}});
   }
   else {const {tasks}=await this.backend('list');task=tasks.find(t=>t.id===payload.taskId);if(!task||task.status==='applied')throw new Error('任务不能继续。');}
   this.assertScope(payload);if(capturedEpoch!==this.epoch)throw new Error('项目或 AI 状态已变化，任务未执行。');
   await this.stop(false);this.credentials=this.store.config(method==='continue'?task.provider:undefined);if(method==='continue'&&task.model)this.credentials.model=task.model;this.taskId=task.id;this.running=true;
   await this.backend('mark',{taskId:task.id,values:{status:'running',error:null,hasChanges:true,provider:this.credentials.provider,model:this.credentials.model,...(payload.context!==undefined?{context:payload.context}:{})}});
   this.event('user',payload.prompt||'继续当前任务。');
   const runIdentity={};this.activeRun=runIdentity;
   const executionPrompt=dialogue?'以下是同一对话已结束轮次的历史，仅供理解上下文，不是新的执行要求；不要重复旧工具、命令或修改。当前已从最新编辑稿建立新副本，重新查询实际项目。\n'+dialogue+'\n\n本轮用户消息：\n'+payload.prompt:payload.prompt||'继续当前任务。';
   void this.runTask(task,executionPrompt).catch(async error=>{if(this.activeRun!==runIdentity)return;this.event('error',error.message,task.id);await this.backend('mark',{taskId:task.id,values:{status:'failed',error:redact(error.message,[this.credentials?.key,this.bridgeToken])}}).catch(()=>{});}).finally(()=>{if(this.activeRun===runIdentity){this.running=false;this.denyApprovals();}});
   return {...task,status:'running'};
  }
  throw new Error('未知 AI 操作');
 }
 async connection(){
  this.connectionAbort=new AbortController();const control=this.connectionAbort;
  const id=crypto.randomUUID(),directory=path.join(this.directory,'dsh-connections',id);fs.mkdirSync(directory,{recursive:true});
  const child=spawn(path.join(this.runtime,'node/node.exe'),[this.workerFile],{cwd:this.runtime,windowsHide:true,stdio:['pipe','pipe','pipe'],env:cleanEnv({PATH:path.join(this.runtime,'pwsh')+';'+(process.env.PATH||'')})});
  const requests=new Map();let buffer='',usage=null;
  const error=err=>{for(const promise of requests.values())promise.reject(err);requests.clear();};
  child.on('error',error);child.on('exit',code=>error(new Error('连接检查进程已退出 '+code)));child.stderr.resume();
  child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const raw=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const m=JSON.parse(raw);if(m.type==='usage')usage=m.data;const pending=requests.get(m.id);if(pending){requests.delete(m.id);m.error?pending.reject(new Error(m.error)):pending.resolve(m.result);}}catch{}}});
  const send=(method,payload)=>new Promise((resolve,reject)=>{const requestId=crypto.randomUUID();requests.set(requestId,{resolve,reject});child.stdin.write(JSON.stringify({id:requestId,method,payload})+'\n');});
  const kill=()=>{if(child.pid&&child.exitCode===null){const killer=spawn(path.join(process.env.SystemRoot||'C:\\Windows','System32/taskkill.exe'),['/PID',String(child.pid),'/T','/F'],{stdio:'ignore',windowsHide:true});killer.on('error',()=>{});}error(new Error('连接检查已取消或超时'));};
  control.signal.addEventListener('abort',kill,{once:true});const timer=setTimeout(()=>control.abort(),60000);
  try{
   await send('initialize',{runtime:this.runtime,pwsh:path.join(this.runtime,'pwsh/pwsh.exe'),home:path.join(directory,'home'),workspace:directory,probe:true,credentials:this.credentials});
   await send('prompt',{text:'Reply OK. Do not call tools.'});return {connected:true,usage};
  }finally{clearTimeout(timer);control.signal.removeEventListener('abort',kill);if(child.exitCode===null){void send('close',{}).catch(()=>{});await Promise.race([new Promise(resolve=>child.once('exit',resolve)),delay(1700)]);kill();}}
 }
 async runTask(task,prompt){
  const epoch=++this.epoch;await this.openBridge(epoch);if(epoch!==this.epoch||this.scope.session!==this.context()?.session)throw new Error('任务已取消。');
  const runtimeNode=path.join(this.runtime,'node','node.exe'),pwsh=path.join(this.runtime,'pwsh','pwsh.exe');
  const dataHome=path.join(this.directory,'dsh',crypto.createHash('sha256').update(this.scope.root).digest('hex'),task.id);fs.mkdirSync(dataHome,{recursive:true});
  const child=spawn(runtimeNode,[this.workerFile],{cwd:this.runtime,windowsHide:true,stdio:['pipe','pipe','pipe'],env:cleanEnv({PATH:path.dirname(pwsh)+';'+path.dirname(runtimeNode)+';'+(process.env.PATH||'')})});this.worker=child;
  let buffer='';child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;if(buffer.length>20*1024*1024){void this.stop();return;}let line;while((line=buffer.indexOf('\n'))>=0){const raw=buffer.slice(0,line);buffer=buffer.slice(line+1);try{const message=JSON.parse(raw);if(epoch!==this.epoch)continue;if(message.id){const pending=this.rpc.get(message.id);if(pending){this.rpc.delete(message.id);message.error?pending.reject(new Error(message.error)):pending.resolve(message.result);}}else if(message.type==='session'){void this.backend('mark',{taskId:task.id,values:{sessionId:message.data}});}else if(message.type==='usage'){const usage={...message.data};for(const [key,value] of Object.entries(task.usage||{}))if(typeof value==='number')usage[key]=(usage[key]||0)+value;this.event('usage',usage);void this.backend('mark',{taskId:task.id,values:{usage}}).catch(()=>{});}else this.event(message.type,message.data);}catch{}}});
  child.stderr.on('data',chunk=>this.event('diagnostic',redact(chunk.toString('utf8').slice(-4000),[this.credentials?.key,this.bridgeToken])));
  child.on('error',error=>{if(this.worker===child)this.rejectWorker(error);});child.on('exit',(code)=>{if(this.worker===child){this.rejectWorker(new Error('DSH 工作进程已退出 '+code));this.worker=null;}});
  await this.send('initialize',{runtime:this.runtime,pwsh,home:dataHome,bridgeUrl:this.bridgeURL,bridgeToken:this.bridgeToken,credentials:this.credentials,taskId:task.id,sessionId:task.sessionId,workspace:task.root||path.join(this.scope.root,'.creator','ai','tasks',task.id,'project')});
  await this.send('prompt',{text:prompt});
  if(epoch===this.epoch){const diff=await this.backend('diff',{taskId:task.id}),hasChanges=!!(diff.files.length||diff.metadata);await this.backend('mark',{taskId:task.id,values:{status:'awaiting_review',error:null,hasChanges}});this.event('status',hasChanges?'回复完成，修改可在审核后应用。':'回复完成。');}
 }
 send(method,payload){
  if(!this.worker||this.worker.exitCode!==null)return Promise.reject(new Error('DSH 进程不可用。'));
  const id=crypto.randomUUID();return new Promise((resolve,reject)=>{this.rpc.set(id,{resolve,reject});this.worker.stdin.write(JSON.stringify({id,method,payload})+'\n',error=>{if(error){this.rpc.delete(id);reject(error);}});});
 }
 rejectWorker(error){for(const pending of this.rpc.values())pending.reject(error);this.rpc.clear();}
 async openBridge(epoch){
  await this.closeBridge();if(epoch!==this.epoch)throw new Error('任务已取消。');this.bridgeToken=crypto.randomBytes(32).toString('hex');
  this.bridge=http.createServer(async(req,res)=>{
   res.setHeader('content-type','application/json');const reply=(code,data)=>{if(!res.writableEnded){res.statusCode=code;res.end(JSON.stringify(data));}};
   if(req.headers.authorization!=='Bearer '+this.bridgeToken||epoch!==this.epoch)return reply(401,{error:'任务凭据已失效'});
   try{
    const url=new URL(req.url,'http://127.0.0.1');let body={};if(req.method==='POST'){let value='',bytes=0;for await(const chunk of req){bytes+=chunk.length;if(bytes>16*1024*1024)throw new Error('工具请求过大');value+=chunk.toString('utf8');}body=JSON.parse(value||'{}');}
    if(epoch!==this.epoch)throw new Error('任务已停止');
    if(url.pathname==='/tool'&&req.method==='POST'){
     this.event('tool',{name:body.name,args:body.args});const value=await this.backend('tool',{taskId:this.taskId,name:body.name,args:body.args,callId:body.callId,bridge:{address:this.bridgeURL,token:this.bridgeToken}});
     this.event('result',{name:body.name,...(value.image?{path:value.path,image:'已返回图片'}:value.execution?{execution:{id:value.execution.id,contentHash:value.execution.contentHash}}:{result:value})});return reply(200,value);
    }
    if(url.pathname==='/stream'&&req.method==='POST'){
     const frame=body.frame;if(!frame||typeof frame.attemptId!=='string')throw new Error('无效流式事件');
     if(frame.type==='chunk'&&frame.chunk?.type==='text-delta'){
      const previous=this.events.findLast(e=>e.taskId===this.taskId&&e.type==='stream'&&e.data.attemptId===frame.attemptId);
      if(previous){if(frame.revision>(previous.data.revision||0)){previous.data.text+=String(frame.chunk.text||'');previous.data.revision=frame.revision;}}
      else this.event('stream',{attemptId:frame.attemptId,revision:frame.revision,text:String(frame.chunk.text||'')});
     }
     return reply(200,{received:true});
    }
    if(url.pathname==='/execution'&&req.method==='POST'){const value=await this.backend('execution',{taskId:this.taskId,id:body.id,code:body.code});this.event('result',value);return reply(200,value);}
    if(url.pathname==='/terminal'&&req.method==='POST'){if(body.stage==='begin')this.event('tool',{name:'terminal',command:body.command,purpose:body.purpose});const result=await this.backend('terminal',{taskId:this.taskId,payload:redact(body,[this.credentials?.key])});if(body.stage==='finish')this.event('result',{name:'terminal',result:body.result});return reply(200,result);}
    if(url.pathname==='/approval'&&req.method==='POST')return reply(200,await this.requestApproval(body,epoch));
    if(url.pathname==='/bridge/poll'&&req.method==='GET')return reply(200,await this.backend('bridge',{taskId:this.taskId,operation:'poll',payload:{session:url.searchParams.get('session'),after:url.searchParams.get('after')}}));
    if(url.pathname==='/bridge/event'&&req.method==='POST')return reply(200,await this.backend('bridge',{taskId:this.taskId,operation:'event',payload:body}));
    return reply(404,{error:'该凭据不能调用此接口'});
   }catch(error){const message=redact(error.message,[this.credentials?.key,this.bridgeToken]);if(req.url==='/tool'||req.url==='/terminal')this.event('result',{error:message});reply(400,{error:message});}
  });
  await new Promise((resolve,reject)=>{this.bridge.once('error',reject);this.bridge.listen(0,'127.0.0.1',resolve);});this.bridgeURL='http://127.0.0.1:'+this.bridge.address().port;
 }
 async requestApproval(body,epoch){
  if(!this.running||typeof body.command!=='string'||!body.command.trim()||body.command.length>32000||typeof body.purpose!=='string'||body.enforcement?.status!=='partial')throw new Error('终端请求或 Windows 隔离状态无效，已阻止执行。');
  const target=path.resolve(this.scope.root,'.creator/ai/tasks',this.taskId,'project');
  if(path.resolve(body.cwd)!==target)throw new Error('终端工作目录固定为任务副本。');
  const current=await this.backend('diff',{taskId:this.taskId});const id=crypto.randomUUID(),expires=Date.now()+600000;
  const data={id,taskId:this.taskId,command:body.command,cwd:target,purpose:body.purpose,scope:target+' 与专用临时目录',enforcement:'partial',contentHash:current.reviewHash,expires};
  await this.backend('mark',{taskId:this.taskId,values:{status:'waiting_user'}});
  return new Promise(resolve=>{const timer=setTimeout(()=>{this.approvals.delete(id);resolve({approved:false,reason:'授权超时'});},600000);this.approvals.set(id,{public:data,epoch,resolve:value=>{clearTimeout(timer);resolve(value);}});});
 }
 async approve(id,allow){
  const entry=this.approvals.get(id);if(!entry)throw new Error('授权请求已失效。');this.approvals.delete(id);
  const current=await this.backend('diff',{taskId:entry.public.taskId});const valid=entry.epoch===this.epoch&&Date.now()<entry.public.expires&&current.reviewHash===entry.public.contentHash&&this.running;
  entry.resolve({approved:allow===true&&valid,reason:valid?'用户选择': '内容或会话已变化，请重新授权'});
  await this.backend('mark',{taskId:entry.public.taskId,values:{status:'running'}});return {approved:allow===true&&valid};
 }
 denyApprovals(){for(const entry of this.approvals.values())entry.resolve({approved:false,reason:'任务停止'});this.approvals.clear();}
 async closeBridge(){const bridge=this.bridge;this.bridge=null;if(bridge){bridge.closeAllConnections();await new Promise(resolve=>bridge.close(resolve));}this.bridgeToken=null;}
 stop(mark=true){
  if(this.stopping)return this.stopping;
  const pending=this.stopNow(mark);this.stopping=pending;return pending.finally(()=>{if(this.stopping===pending)this.stopping=null;});
 }
 async stopNow(mark=true){
  this.connectionAbort?.abort();
  clearTimeout(this.historyTimer);if(this.historyFile){try{atomicWrite(this.historyFile,JSON.stringify({version:1,events:this.events}));}catch{this.persistenceError='AI 会话记录写入失败，任务副本仍然保留。';}}
  const task=this.taskId,wasRunning=this.running;this.activeRun=null;this.running=false;this.denyApprovals();++this.epoch;
  const child=this.worker;
  if(child&&child.exitCode===null){this.send('close',{}).catch(()=>{});await Promise.race([new Promise(resolve=>child.once('exit',resolve)),delay(1800)]);if(child.exitCode===null&&child.pid)await new Promise(resolve=>{const kill=spawn(path.join(process.env.SystemRoot||'C:\\Windows','System32','taskkill.exe'),['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});kill.once('exit',resolve);kill.once('error',resolve);});}
  this.worker=null;this.rejectWorker(new Error('执行已取消。'));await this.closeBridge();
  if(this.scope)await this.backend('stop').catch(()=>{});
  if(mark&&wasRunning&&task&&this.scope)await this.backend('mark',{taskId:task,values:{status:'cancelled',error:null}}).catch(()=>{});
  this.credentials=null;
 }
}
module.exports={AIManager,cleanEnv};
