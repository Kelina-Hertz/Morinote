'use strict';
const crypto=require('node:crypto');
const {generationIntent}=require('./creative-coordinator.cjs');
const {fail}=require('./common.cjs');
function acceptanceIntent(text,records){
 if(/(?:不|还没|尚未|未|别).{0,5}(?:满意|通过|验收|接受|采用|应用)|[？?]|比如|例如|假如|如果|是否|什么意思|解释/.test(text)||!/(?:验收通过|验收成功|确认采用|用这一版|用这版|这张可以|这句可以|可以了|满意了|接受这|应用(?:这个|当前|片段|这版|全部))/.test(text))return null;
 const active=records.filter(f=>!f.legacy&&['awaiting_review','accepted_pending_apply','bound'].includes(f.status));
 const named=active.filter(f=>text.includes(f.id)||text.includes(f.title));const choices=named.length?named:active.filter(f=>f.status!=='bound');if(choices.length!==1)return {ambiguous:true};const f=choices[0];
 const whole=f.kind==='fragment'&&/片段|全部|整段|全都/.test(text);let items=Object.values(f.items);
 if(!whole&&/这张|图片|背景|立绘|CG/i.test(text))items=items.filter(i=>i.kind==='image');else if(!whole&&/这句|配音|语音|声音/.test(text))items=items.filter(i=>i.kind==='voice');
 const explicit=items.filter(i=>i.candidates.some(c=>text.includes(c.id)));if(explicit.length)items=explicit;
 if(!whole&&items.length!==1||items.some(i=>!i.selectedId))return {ambiguous:true};
 return {creativeId:f.id,candidateIds:items.map(i=>i.candidates.find(c=>text.includes(c.id))?.id||i.selectedId),whole};
}
const methods={
 mediaChanged(record){if(!record.items||record.status!=='awaiting_review')return;this.mediaNotifications||=new Map();const key=JSON.stringify(Object.values(record.items).map(i=>i.selectedId));if(this.mediaNotifications.get(record.id)===key)return;this.mediaNotifications.set(record.id,key);this.event('status',record.title+'：已生成，待验收。',record.conversationId);},
 mediaRuntime(conversationId){const c=this.conversation(conversationId),r=this.runtimes.get(c.id)||this.makeRuntime(c);r.session=this.scope.session;return r;},
 captureMediaMessage(text,id){let records=[];if(!this.media.error)try{records=this.media.fragments?.records(this.scope.root).filter(f=>f.conversationId===id)||[];}catch{}return {mediaGenerationAuthorized:generationIntent(text),mediaAcceptance:acceptanceIntent(text,records)};},
 async mediaHandle(method,payload,context){await this.media.ready;this.media.assertReady();const creativeId=payload.creativeId||payload.fragmentId;
  if(method==='media_cancel'){await this.media.fragments.cancel(creativeId);return {cancelled:true};}
  const f=this.media.fragments.get(creativeId),r=this.mediaRuntime(f.conversationId);if(payload.conversationId&&payload.conversationId!==r.id)throw new Error('候选不属于当前对话。');
  if(method==='media_artifact'){const c=this.media.fragments.findCandidate(f,payload.candidateId);const {data,job}=this.media.jobs.artifact(c.jobId);return {data:data.toString('base64'),mime:job.artifact.mime};}
  if(method==='media_select')return this.media.fragments.select(r,f.id,payload.itemKey,payload.candidateId);
  if(method==='media_feedback')return this.media.fragments.feedback(r,f.id,payload.itemKey,payload.text);
  if(method==='media_revise')return this.media.fragments.revise(r,{...payload,creativeId:f.id});
  if(method==='media_accept')return this.media.fragments.accept(r,{...payload,creativeId:f.id,origin:'button'});
  if(method==='media_apply')return this.media.fragments.apply(r,f.id);
  if(method==='media_conflicts')return {conflicts:f.pendingMerge||[]};
  if(method==='media_resolve')return this.media.fragments.resolveMerge(r,{...payload,creativeId:f.id});
  if(method==='media_resume')return this.media.resume(f.id,r);
  if(method==='media_budget')return this.media.jobs.increaseBudget(f.runId,payload.totalCny);
  if(method==='media_preview'||method==='media_lint'){
   if(r.running)throw new Error('请等待当前回复结束后从卡片启动候选试玩。');
   const snapshot=await this.media.fragments.preview(r,f.id);r.previewTask=snapshot.task;r.executionStates.set(snapshot.task.id,snapshot.state);
   await this.ensureWorker(r,this.conversation(r.id),true);const phase=method==='media_lint'?'lint':'preview';const result=await this.backend('tool',{taskId:snapshot.task.id,name:phase,args:phase==='preview'?{label:snapshot.label}:{},callId:'candidate-'+crypto.randomUUID(),bridge:{address:r.url,token:r.token}});
   if(!result.execution)return result;r.executions.set(result.execution.id,snapshot.task.id);
   const value=await this.runHostExecution(r,result.execution);await this.media.fragments.execution(f.id,phase,value);return value;
  }
  if(method==='media_generate'){
   if(r.running)throw new Error('请等待当前回复结束后生成。');const previous=r.current,previousRound=r.round;r.current={id:payload.actionId||crypto.randomUUID(),text:payload.newVariation?'同样提示词再生成一版':'生成所选素材',mediaGenerationAuthorized:true};r.round=r.current.id;
   try{return await this.media.fragments.generateSelected(r,{...payload,creativeId:f.id});}finally{r.current=previous;r.round=previousRound;}
  }
  throw new Error('未知候选操作。');
 },
 async mediaTool(r,name,args,callId){await this.media.ready;this.media.assertReady();const coordinator=this.media.fragments;
  if(name==='creative_draft')return this.media.modelResult(await coordinator.draft(r,{...args,runId:this.conversation(r.id).mediaRunId}));
  if(['creative_revise','creative_generate'].includes(name)&&args.expectedVersion===undefined)fail('FS_NOT_OBSERVED','请先读取创作项，并传入 editVersion。');
  if(name==='creative_revise')return this.media.modelResult(await coordinator.revise(r,args));
  if(name==='creative_candidates')return {creations:coordinator.records(this.scope.root).filter(f=>!f.legacy&&f.conversationId===r.id&&(!args.creativeId||f.id===args.creativeId)).slice(-5).map(f=>this.media.modelQuery(f,args))};
  if(name==='generate_media'){const draft=await coordinator.draft(r,{...args,runId:this.conversation(r.id).mediaRunId});return this.media.modelResult(await coordinator.generateSelected(r,{...args,creativeId:draft.id,expectedVersion:draft.editVersion,callId}));}
  if(name==='creative_generate')return this.media.modelResult(await coordinator.generateSelected(r,{...args,callId}));
  if(name==='creative_apply')return this.media.modelResult(await coordinator.apply(r,args.creativeId));
  if(name==='read_candidate'){const f=coordinator.get(args.creativeId,r),c=coordinator.findCandidate(f,args.candidateId);if(c.kind!=='image')return {kind:c.kind,director:c.request.director,request:c.request,reason:'配音请由用户试听验收。'};const {data,job}=this.media.jobs.artifact(c.jobId);return {path:c.id+'.'+job.artifact.extension,image:{data:data.toString('base64'),mimeType:job.artifact.mime}};}
  if(name==='creative_preview'||name==='creative_lint'){const decision=await this.checkpoint(r,name==='creative_preview'?'临时试玩候选':'检查候选');if(!decision.approved)return {status:'not_run',reason:decision.reason};const snapshot=await coordinator.preview(r,args.creativeId);r.previewTask=snapshot.task;r.executionStates.set(snapshot.task.id,snapshot.state);const result=await this.backend('tool',{taskId:snapshot.task.id,name:name==='creative_preview'?'preview':'lint',args:name==='creative_preview'?{label:snapshot.label}:{},callId,bridge:{address:r.url,token:r.token}});if(result.execution)r.executions.set(result.execution.id,snapshot.task.id);return {...result,candidateVersion:snapshot.candidateVersion};}
  fail('UNKNOWN_TOOL','未知创作工具。');
 },
 runHostExecution(r,descriptor){r.hostExecutions||=new Map();const id=crypto.randomUUID();return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{r.hostExecutions.delete(id);reject(new Error('候选执行未返回结果；请停止试玩后重试。'));},360000);r.hostExecutions.set(id,{id,descriptor,resolve:value=>{clearTimeout(timer);r.hostExecutions.delete(id);resolve(value);},reject:error=>{clearTimeout(timer);r.hostExecutions.delete(id);reject(error);}});});},
};
module.exports={methods,acceptanceIntent};
