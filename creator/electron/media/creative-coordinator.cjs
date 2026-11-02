'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {digest,textHash,readJSON,saveJSON,fail,checkAbort,regular,imageInfo,sanitize,id}=require('./common.cjs');
const {voiceRequest,direction}=require('./voice-direction.cjs');
const {overlays,allLines}=require('./fragment-coordinator.cjs');
const REGISTRY='game/creator_assets/asset_bindings.rpy';
const uid=prefix=>prefix+'_'+crypto.randomUUID().replaceAll('-','').slice(0,24);
const candidateSignature=f=>digest([f.plan||f.request,Object.values(f.items||{}).map(i=>i.selectedId)]);
function generationIntent(text=''){
 if(/(?:先别|暂不|不要|不需要|不必|别再)\s*(?:自动|重新)?(?:生成|生图|配音|合成)|(?:^|[。！？!，,：:\s])(?:能否|能不能|是否|怎么|如何|为什么)[^。！？!，,：:\n]{0,40}(?:生成|配音)|(?:生成|配音).{0,10}(?:吗|么)[？?]?$/.test(text))return false;
 return /(?:^|[。！？!，,：:\s])(?:请|帮我|现在|开始|直接|再|重新|继续|麻烦|就)?\s*(?:生成(?:一|这|该|所|图片|配音|背景|立绘|候选|[，,。！!\s]|$)|生图|合成(?:配音|语音)|按(?:这个|这样|上述|刚才).{0,12}改|再来一版|重新画|画一(?:张|个)|给.{0,15}配音)/.test(text)||/^(?:请|帮我|麻烦)(?:根据|按照|按|把|为)(?!.*(?:讨论|解释|评估))[^\n。！？?]{0,180}(?:生成|生图|配音)/.test(text);
}
function safeMetadata(root){const target=path.join(root,'.creator/media/creations.json');let current=path.resolve(root);for(const part of ['.creator','media','creations.json']){current=path.join(current,part);if(fs.existsSync(current)&&fs.lstatSync(current).isSymbolicLink())fail('INVALID_PATH','候选目录不能包含链接。');}return target;}
function clean(value){return JSON.parse(JSON.stringify(value));}
class CreativeCoordinator{
 constructor(options){Object.assign(this,options);this.active=new Map();this.applying=new Map();}
 assert(session,root,signal){checkAbort(signal);if(this.context()?.session!==session||path.resolve(this.context()?.root||'')!==path.resolve(root))fail('PROJECT_CHANGED','项目已切换；已有产物保留，尚未应用。');}
 records(root){const data=readJSON(this.jobs.file,{runs:{},jobs:{}});return [...Object.values(data.creations||{}).map(f=>({...f,editVersion:f.editVersion||0})),...Object.values(data.fragments||{}).map(f=>({...f,legacy:true}))].filter(f=>f.projectRoot===path.resolve(root));}
 get(creativeId,r){if(!id(creativeId))fail('INVALID_REQUEST','无效创作编号。');const f=this.records(this.context().root).find(f=>f.id===creativeId);if(!f||f.legacy||r&&f.conversationId!==r.id)fail('CREATIVE_NOT_FOUND','当前项目或对话中没有此创作项。');return f;}
 async update(f,patch){const result=await this.jobs.locked(data=>{data.creations||={};const previous=data.creations[f.id];if(previous&&(previous.editVersion||0)!==(f.editVersion||0))fail('FS_STALE_VERSION','创作提示或候选已有新版本，请重新读取后修改。');Object.assign(f,patch,{editVersion:(previous?.editVersion||0)+1,updated:Date.now(),ownerPid:process.pid});f.viewSignature=candidateSignature(f);if(f.candidatePreview?.viewSignature!==undefined&&f.candidatePreview.viewSignature!==f.viewSignature){if(f.lint)f.lint.stale=true;if(f.preview)f.preview.stale=true;}data.creations[f.id]=clean(f);return clean(f);});
  // The ledger is authoritative. A project copy also keeps intent/history beside its candidates.
  let warning;try{const records=this.records(f.projectRoot).filter(item=>!item.legacy);saveJSON(safeMetadata(f.projectRoot),{version:2,creations:records});}catch(error){warning='项目内创作记录备份失败：'+sanitize(error);}
  if(warning!==f.storageWarning){await this.jobs.locked(data=>{if(data.creations[f.id]?.editVersion===f.editVersion){if(warning)data.creations[f.id].storageWarning=warning;else delete data.creations[f.id].storageWarning;}});f.storageWarning=warning;result.storageWarning=warning;}
  this.onChange?.(result);return result;
 }
 public(f){if(f.legacy)return {...f,acceptanceUnknown:true};return {...clean(f),base:undefined,voiceProfiles:undefined,appliedPrepared:undefined,pendingPrepared:undefined,pendingMerge:undefined,resolutions:undefined,conflictPaths:f.pendingMerge?.map(c=>c.path)};}
 async base(r,kind,target,fragmentId){const result={};const files=[REGISTRY];if(kind==='fragment')files.push('game/creator_fragments/'+fragmentId+'.rpy');if(kind==='voice'&&target?.path)files.push(target.path);
  for(const file of files){const d=await this.source.read(file,r.session);result[file]={version:d.version,hash:textHash(d.value),content:d.value};}return result;
 }
 async draft(r,args={}){const root=path.resolve(this.context().root);this.assert(r.session,root);const kind=args.kind||'fragment';if(!['fragment','image','voice'].includes(kind))fail('NOT_IMPLEMENTED','目前支持图片、配音与片段。');
  const prior=args.creativeId?this.get(args.creativeId,r):!args.newCreative?this.records(root).filter(f=>!f.legacy&&f.conversationId===r.id&&f.kind===kind).at(-1):null;
  if(prior&&(this.active.has(prior.id)||this.applying.has(prior.id)))fail('CREATIVE_BUSY','请先停止或等待当前操作，再修改提示词。');
  if(prior&&prior.kind!==kind)fail('INVALID_REQUEST','请沿用该创作项原有类型，另一种用途应另建创作项。');
  if(prior&&args.expectedVersion!==prior.editVersion)fail('FS_STALE_VERSION','请先读取当前创作项，并使用 editVersion 更新提示词。');
  const initial=await this.source.snapshot(r.session),plan=kind==='fragment'?clean(args.plan||prior?.plan):undefined;
  if(kind==='fragment')await this.request('/api/fragment/validate',{projectSession:r.session,plan,documents:overlays(initial),ide:initial.project.ide});
  const title=args.title||plan?.title||prior?.title;if(typeof title!=='string'||!title.trim()||title.length>100)fail('INVALID_REQUEST','请填写 100 字以内的标题。');
  const brief=args.brief??prior?.brief??'';if(typeof brief!=='string'||brief.length>12000)fail('INVALID_REQUEST','创作要求应为 12000 字以内的文本。');
  let target=clean(args.target||prior?.target||{}),request=kind==='fragment'?undefined:clean(args.request||prior?.request||{});
  if(target.assetId&&!initial.project.nativeAssetLibrary?.entries?.some(e=>e.id===target.assetId))fail('INVALID_TARGET','请选择当前工程中的虚拟素材。');
  if(kind==='voice'&&target.nodeId){const body=await this.request('/api/workspace/analyze',{projectSession:r.session,documents:overlays(initial),ide:initial.project.ide});const line=body.project.scenes.flatMap(s=>s.lines).find(l=>l.id===target.nodeId);if(!line||line.kind==='chat'&&line.advance===false)fail('INVALID_TARGET','目标台词不存在或不能推进。');const text=line.text.replace(/\[\[/g,'[').replace(/\{\{/g,'{');if(request.displayText&&request.displayText!==text)fail('VOICE_TEXT_CHANGED','请使用目标台词原文。');request.displayText=text;target={...target,path:'game/'+line.source.file,textHash:textHash(text),speaker:line.speaker};}
  const fid=prior?.id||uid('creative'),fragmentId=prior?.fragmentId||uid('fragment');const specs=[];
  if(kind==='fragment'){
   if(plan.background.mode==='generate')specs.push({key:'background',kind:'image',request:{...plan.background},brief:plan.background.brief||brief});
   for(const line of allLines(plan))if(line.voice!=null)specs.push({key:line.id,kind:'voice',speaker:line.speaker,request:{...line.voice,displayText:line.text},brief:line.voice.brief||brief});
  }else specs.push({key:kind,kind,request,brief});
  const items={};for(const spec of specs){const old=prior?.items[spec.key]||prior?.retiredItems?.[spec.key];let req=spec.request;delete req.mode;if(spec.kind==='voice'){
    req.voiceId??=old?.revisions.at(-1)?.request.voiceId||prior?.voiceProfiles?.[spec.speaker]||this.store.data.providers.minimax.voiceId;
    direction(req);const synthesis=voiceRequest(req.displayText,req);this.jobs.registry.get('voice').provider.estimate(synthesis,this.store.config('minimax',{mock:true}));
   }else{if(req.assetType&&!['background','sprite','cg','interface','unknown'].includes(req.assetType))fail('INVALID_REQUEST','图片用途应为背景、立绘、CG 或界面。');if(!Array.isArray(req.referenceAssetIds||[])||!Array.isArray(req.referenceCandidateIds||[]))fail('INVALID_REFERENCE','参考图应为已登记 ID 列表。');this.jobs.registry.get('image').provider.estimate(req,this.store.config('seedream',{mock:true}));}
   const revisions=old?.revisions||[],revision={id:uid('prompt'),number:revisions.length+1,brief:spec.brief,request:req,created:Date.now(),feedback:args.feedback||''};
   const last=revisions.at(-1);if(!last||digest([last.request,last.brief])!==digest([req,spec.brief]))revisions.push(revision);
   items[spec.key]={...old,key:spec.key,kind:spec.kind,speaker:spec.speaker,revisions,candidates:old?.candidates||[]};
  }
  const run=prior?this.jobs.run(prior.runId):args.runId?this.jobs.run(args.runId):await this.jobs.ensureRun({projectRoot:root,conversationId:r.id,runId:uid('creation_run')});if(run.projectRoot!==root)fail('RUN_MISMATCH','额度不属于当前工程。');
  const voiceProfiles={...(prior?.voiceProfiles||{})};for(const item of Object.values(items))if(item.speaker)voiceProfiles[item.speaker]=item.revisions.at(-1).request.voiceId;
  const f={...prior,id:fid,version:2,kind,title,brief,plan,request,target,voiceProfiles,projectRoot:root,session:r.session,conversationId:r.id,roundId:r.round,runId:run.id,fragmentId,
   created:prior?.created||Date.now(),items,retiredItems:{...(prior?.retiredItems||{}),...Object.fromEntries(Object.entries(prior?.items||{}).filter(([key])=>!items[key]))},fixture:run.mode==='mock',
   status:'draft',error:undefined,base:prior?.base||await this.base(r,kind,target,fragmentId),fragmentAccepted:undefined};
  return this.public(await this.update(f,{}));
 }
 async revise(r,{creativeId,itemKey,request,brief,feedback,expectedVersion}){const f=this.get(creativeId,r);if(!f.items[itemKey])fail('INVALID_TARGET','此创作项中没有指定素材。');if(expectedVersion!==undefined&&expectedVersion!==f.editVersion)fail('FS_STALE_VERSION','提示词已有新版本，请比较后再保存。');
  if(f.kind!=='fragment')return this.draft(r,{creativeId,expectedVersion:f.editVersion,kind:f.kind,request:{...f.request,...request},brief:brief??f.brief,feedback});
  const plan=clean(f.plan);if(itemKey==='background')Object.assign(plan.background,request,{brief:brief??f.items[itemKey].revisions.at(-1).brief});else{const line=allLines(plan).find(l=>l.id===itemKey);if(!line)fail('INVALID_TARGET','目标对白不在当前计划中。');line.voice={...line.voice,...request,brief:brief??f.items[itemKey].revisions.at(-1).brief};}
  return this.draft(r,{creativeId,expectedVersion:f.editVersion,kind:'fragment',plan,feedback});
 }
 async materialRequest(f,item,revision,initial){if(item.kind==='voice'){if(!revision.request.director?.trim())fail('DIRECTOR_REQUIRED','请先补全配音导演说明，并转换为支持的控制参数，再生成。');return voiceRequest(revision.request.displayText,revision.request);}
  const req=revision.request,references=[];for(const assetId of req.referenceAssetIds||[]){const resource=initial.project.nativeAssetLibrary?.resources?.find(a=>a.id===assetId);if(!resource)fail('INVALID_REFERENCE','参考图必须为当前工程登记的实际图片。');const file=path.join(f.projectRoot,resource.path);regular(f.projectRoot,file);const data=fs.readFileSync(file);if(data.length>10*1024*1024)fail('INVALID_REFERENCE','参考图超过 10 MiB。');references.push({data,mime:imageInfo(data).mime});}
  for(const candidateId of req.referenceCandidateIds||[]){const candidate=this.findCandidate(f,candidateId);if(candidate.kind!=='image')fail('INVALID_REFERENCE','参考候选必须为图片。');const {data}=this.jobs.artifact(candidate.jobId);if(data.length>10*1024*1024)fail('INVALID_REFERENCE','候选参考图超过 10 MiB。');references.push({data,mime:imageInfo(data).mime});}
  return {prompt:req.prompt,size:req.size||'2048x1152',...(req.watermark===undefined?{}:{watermark:req.watermark}),references};
 }
 findCandidate(f,candidateId){for(const item of [...Object.values(f.items),...Object.values(f.retiredItems||{})]){const c=item.candidates.find(c=>c.id===candidateId);if(c)return c;}fail('CANDIDATE_NOT_FOUND','候选不属于此创作项。');}
 async generate(r,plan,{callId,runId,creativeId,itemKeys,newVariation=false,expectedVersion,newCreative}={}){const f=await this.draft(r,{creativeId,expectedVersion,newCreative,kind:'fragment',plan,runId});return this.generateSelected(r,{creativeId:f.id,itemKeys,newVariation,callId});}
 async generateSelected(r,{creativeId,itemKeys,newVariation=false,callId,expectedVersion}={}){if(!r.current?.mediaGenerationAuthorized)fail('GENERATION_NOT_REQUESTED','提示词已保留；请等用户明确要求生成，再调用媒体生成。');
  const f=this.get(creativeId,r);this.assert(r.session,f.projectRoot);
  if(expectedVersion!==undefined&&expectedVersion!==f.editVersion)fail('FS_STALE_VERSION','生成前提示词或所选候选已变化，请重新查看。');
  if(f.kind==='voice'&&f.target?.nodeId){const state=await this.source.snapshot(r.session),current=await this.request('/api/workspace/analyze',{projectSession:r.session,documents:overlays(state),ide:state.project.ide});const line=current.project.scenes.flatMap(s=>s.lines).find(l=>l.id===f.target.nodeId);if(!line||textHash(line.text.replace(/\[\[/g,'[').replace(/\{\{/g,'{'))!==f.target.textHash||line.speaker!==f.target.speaker)fail('VOICE_STALE','原台词或角色已改变；请先更新导演提示与目标，再决定是否重新配音。');}
  const keys=itemKeys||Object.keys(f.items);if(!Array.isArray(keys)||new Set(keys).size!==keys.length||keys.some(key=>!f.items[key]))fail('INVALID_TARGET','请选择当前创作项内的素材。');
  const signature=digest([keys.slice().sort(),newVariation,r.current.id]);if(this.active.has(f.id)){const active=this.active.get(f.id);if(active.signature!==signature)fail('CREATIVE_BUSY','当前创作项正在生成其他素材，请等待后继续。');return active.promise;}
  f.roundId=r.round;const controller=new AbortController(),promise=this.produce(r,f,keys,{newVariation,callId,signal:controller.signal}).finally(()=>this.active.delete(f.id));this.active.set(f.id,{promise,controller,signature,record:f});return promise;
 }
 async stash(f,c,r){const {job,data}=this.jobs.artifact(c.jobId);this.assert(r.session,f.projectRoot);const registration=await this.requestMedia('/api/generated-media/register',{projectSession:r.session,projectRoot:f.projectRoot,jobId:job.id,kind:job.kind,artifact:job.artifact,destination:'candidate'});
  c.storage=await this.requestMedia('/api/generated-media/import',{projectSession:r.session,projectRoot:f.projectRoot,receipt:registration.receipt,data:data.toString('base64')});return c;
 }
 async produce(r,f,keys,{newVariation,callId,signal}){try{await this.update(f,{status:'generating',error:undefined});const initial=await this.source.snapshot(r.session),todo=[];
   for(const key of keys){const item=f.items[key],revision=item.revisions.at(-1);const recorded=this.jobs.list(f.projectRoot).jobs.find(j=>j.creativeId===f.id&&j.fragmentKey===key&&j.promptRevision===revision.id&&j.artifact&&(!newVariation||j.generationMessageId===r.current.id));if(recorded&&!item.candidates.some(c=>c.jobId===recorded.id))item.candidates.push({id:uid('candidate'),key,kind:item.kind,jobId:recorded.id,promptRevision:revision.id,generationMessageId:recorded.generationMessageId,request:clean(revision.request),artifact:recorded.artifact,created:recorded.created,ttsHash:recorded.ttsHash,fixture:recorded.fixture,estimate:recorded.estimate,usage:recorded.usage});const existing=item.candidates.filter(c=>c.promptRevision===revision.id).at(-1);if(existing&&(!newVariation||existing.generationMessageId===r.current.id)){if(!existing.storage)await this.stash(f,existing,r);item.selectedId=existing.id;continue;}
    const request=await this.materialRequest(f,item,revision,initial),attemptId=digest([f.id,key,revision.id,newVariation?r.current.id:'original']);todo.push({item,revision,request,attemptId});}
   // Validate the entire requested batch before its first paid submission.
   const run=this.jobs.run(f.runId);let cost=0,images=0,voices=0,chars=0;for(const task of todo){const provider=this.jobs.registry.get(task.item.kind),estimate=provider.provider.estimate(task.request,this.store.config(provider.id,{mock:true}));cost+=estimate.cny;if(task.item.kind==='image')images++;else{voices++;chars+=estimate.billableCharacters;}}
   if(run.media.reservedCny+cost>run.limits.estimatedMediaBudgetCny+1e-9||run.media.imageSubmissions+images>run.limits.maxImageSubmissions||run.media.voiceSubmissions+voices>run.limits.maxVoiceSubmissions||run.media.voiceBillableCharacters+chars>run.limits.maxVoiceBillableCharacters)fail('MEDIA_BUDGET_EXCEEDED','本次生成会超过此创作任务的累计额度；未提交新请求。');
   await this.jobs.locked(data=>{data.humanAttempts||={};const key=digest([f.projectRoot,r.id,r.current.id]),grant=data.humanAttempts[key]||{};for(const task of todo){const itemKey=f.id+':'+task.item.key;if(grant[itemKey]&&grant[itemKey]!==task.attemptId)fail('GENERATION_NOT_REQUESTED','本条用户消息已生成过这一项；修改提示词后请等待用户再次要求生成，不能自行反复收费。');}for(const task of todo)grant[f.id+':'+task.item.key]=task.attemptId;data.humanAttempts[key]=grant;});
   for(const task of todo){this.assert(r.session,f.projectRoot,signal);const {item,revision,request,attemptId}=task;const provider=this.jobs.registry.get(item.kind),config=this.store.config(provider.id,{mock:true});const effectiveParameters=item.kind==='voice'?require('./providers/minimax.cjs').parameters(request,config):{...require('./providers/seedream.cjs').parameters({...request,references:[]},config),references:(request.references||[]).map(ref=>({sha256:digest(ref.data),mime:ref.mime}))};const job=await this.jobs.generate({runId:f.runId,kind:item.kind,request,attemptId,identity:{creativeId:f.id,fragmentId:f.id,fragmentKey:item.key,promptRevision:revision.id,generationMessageId:r.current.id,conversationId:r.id,roundId:r.round,ttsHash:item.kind==='voice'?digest(request):undefined},signal});
    let c=item.candidates.find(c=>c.jobId===job.id);if(!c){c={id:uid('candidate'),key:item.key,kind:item.kind,jobId:job.id,promptRevision:revision.id,generationMessageId:r.current.id,request:clean(revision.request),effectiveParameters,artifact:job.artifact,fixture:job.fixture,created:Date.now(),estimate:job.estimate,usage:job.usage,ttsHash:item.kind==='voice'?digest(request):undefined};item.candidates.push(c);}
    item.selectedId=c.id;await this.update(f,{});this.assert(r.session,f.projectRoot,signal);await this.stash(f,c,r);await this.update(f,{});
   }
   return this.public(await this.update(f,{status:'awaiting_review',error:undefined}));
  }catch(error){const jobs=this.jobs.list(f.projectRoot).jobs.filter(j=>j.creativeId===f.id);for(const job of jobs){const item=f.items[job.fragmentKey];if(job.artifact&&item&&!item.candidates.some(c=>c.jobId===job.id)){const revision=item.revisions.find(p=>p.id===job.promptRevision);item.candidates.push({id:uid('candidate'),key:item.key,kind:item.kind,jobId:job.id,promptRevision:job.promptRevision,request:revision?.request,artifact:job.artifact,created:Date.now(),ttsHash:job.ttsHash});}}
   await this.update(f,{status:jobs.some(j=>j.status==='uncertain')?'uncertain':signal.aborted?'cancelled':error.code==='MEDIA_BUDGET_EXCEEDED'?'budget_exhausted':jobs.some(j=>j.artifact||j.downloadAvailable)?'needs_rebind':'failed',error:sanitize(error),code:error.code});throw error;}
 }
 selected(f){return Object.values(f.items).map(item=>{if(!item.selectedId)fail('CANDIDATES_INCOMPLETE','请先生成并选择每项需要的素材。');return this.findCandidate(f,item.selectedId);});}
 validateSelection(f){const candidates=this.selected(f);for(const c of candidates){const item=f.items[c.key],latest=item.revisions.at(-1);if(c.kind==='voice'&&(c.request.displayText!==latest.request.displayText||c.request.voiceId!==latest.request.voiceId))fail('VOICE_STALE','所选配音与当前台词或声线不同，请重新选择或生成。');}return candidates;}
 async select(r,creativeId,itemKey,candidateId){const f=this.get(creativeId,r);if(this.active.has(f.id)||this.applying.has(f.id))fail('CREATIVE_BUSY','当前生成或应用尚未结束。');const c=this.findCandidate(f,candidateId);if(c.key!==itemKey||!f.items[itemKey])fail('INVALID_TARGET','候选不属于当前素材。');f.items[itemKey].selectedId=c.id;f.fragmentAccepted=undefined;return this.public(await this.update(f,{status:'awaiting_review'}));}
 async feedback(r,creativeId,itemKey,text){this.get(creativeId,r);const f=this.active.get(creativeId)?.record||this.applying.get(creativeId)?.record||this.get(creativeId,r);if(typeof text!=='string'||!text.trim()||text.length>8000||!f.items[itemKey])fail('INVALID_REQUEST','请填写对当前素材的修改意见。');f.feedback||=[];f.feedback.push({id:uid('feedback'),itemKey,text,candidateId:f.items[itemKey].selectedId,created:Date.now(),user:true});return this.public(await this.update(f,{}));}
 async accept(r,{creativeId,candidateIds,whole=false,origin='button',messageId}={}){const f=this.get(creativeId,r);this.assert(r.session,f.projectRoot);if(this.active.has(f.id)||this.applying.has(f.id))fail('CREATIVE_BUSY','请先等待当前生成或应用结束。');
  const selected=whole||f.kind!=='fragment'?this.validateSelection(f):Object.values(f.items).filter(i=>i.selectedId).map(i=>this.findCandidate(f,i.selectedId));if(!Array.isArray(candidateIds)||!candidateIds.length&&selected.length||candidateIds.some(id=>!selected.some(c=>c.id===id)))fail('REVIEW_STALE','验收版本已变化，请重新查看候选。');
  if(whole&&(selected.length!==candidateIds.length||!selected.every(c=>candidateIds.includes(c.id))))fail('REVIEW_STALE','片段验收需要当前全部候选。');
  const approval={id:uid('review'),origin,messageId,created:Date.now(),candidateIds:[...candidateIds]};for(const id of candidateIds){const c=this.findCandidate(f,id);f.items[c.key].acceptedId=id;c.acceptance=approval;}
  f.reviews||=[];f.reviews.push(approval);if(whole||f.kind!=='fragment')f.fragmentAccepted={...approval,selectionHash:digest(selected.map(c=>c.id)),planHash:digest(f.plan||f.request)};
  await this.update(f,{status:f.kind==='fragment'&&!whole?'awaiting_review':'accepted_pending_apply'});if(f.kind==='fragment'&&!whole)return this.public(f);return this.apply(r,f.id);
 }
 async apply(r,creativeId){if(this.active.has(creativeId))fail('CREATIVE_BUSY','请先等待当前生成结束，再应用验收结果。');const f=this.get(creativeId,r);this.assert(r.session,f.projectRoot);const candidates=this.validateSelection(f),selectionHash=digest(candidates.map(c=>c.id));
  if(!f.fragmentAccepted||f.fragmentAccepted.selectionHash!==selectionHash||f.fragmentAccepted.planHash!==digest(f.plan||f.request)||candidates.some(c=>f.items[c.key].acceptedId!==c.id))fail('USER_REVIEW_REQUIRED','需要用户验收当前候选；Agent 或自动审核不能代替用户验收。');
  if(this.applying.has(f.id))return this.applying.get(f.id);const promise=this.applySelected(r,f,candidates).finally(()=>this.applying.delete(f.id));promise.record=f;this.applying.set(f.id,promise);return promise;
 }
 async applySelected(r,f,candidates){try{
   const selection=digest([f.plan||f.request,candidates.map(c=>c.id)]);
   if(f.appliedPrepared?.selection===selection){const captured=f.appliedPrepared;const docs=await Promise.all(captured.edits.map(e=>this.source.read(e.path,r.session)));
    if(docs.every((d,i)=>d.value===captured.edits[i].content)){
     await this.finishApply(r,f,captured.prepared,captured.edits,selection,{recoveredCommit:true});return this.public(f);
    }
   }
   const currentBase={};for(const file of Object.keys(f.base))currentBase[file]=await this.source.read(file,r.session);
   if(f.appliedSelection===selection&&Object.entries(f.base).every(([file,base])=>currentBase[file].version===base.version))return this.public(f);
   let prepared=f.pendingPrepared?.selection===selection?f.pendingPrepared.prepared:null;
   if(prepared)for(const edit of prepared.edits){const doc=await this.source.read(edit.path,r.session);if(doc.version!==f.pendingPrepared.versions[edit.path]){prepared=null;f.resolutions={};f.pendingMerge=undefined;break;}}
   if(!prepared){
    const imports=[];for(const c of candidates){const {job,data}=this.jobs.artifact(c.jobId);this.assert(r.session,f.projectRoot);const receipt=await this.requestMedia('/api/generated-media/register',{projectSession:r.session,projectRoot:f.projectRoot,jobId:job.id,kind:job.kind,artifact:job.artifact,destination:'project'});const imported=await this.requestMedia('/api/generated-media/import',{projectSession:r.session,projectRoot:f.projectRoot,receipt:receipt.receipt,data:data.toString('base64')});imports.push(this.importSpec(f,c,imported));}
    await this.source.editor('refresh',{},r.session);const state=await this.source.snapshot(r.session);
    const own='game/creator_fragments/'+f.fragmentId+'.rpy',existing=f.kind==='fragment'?await this.source.read(own,r.session):null;
    prepared=await this.requestMedia('/api/generated-media/prepare',{...this.body(f),projectSession:r.session,projectRoot:f.projectRoot,imports,documents:overlays(state),ide:state.project.ide,replaceHash:existing?.exists?textHash(existing.value):undefined,entryIds:f.entryIds});
    const versions={};const conflicts=[];for(const edit of prepared.edits){const doc=await this.source.read(edit.path,r.session);versions[edit.path]=doc.version;const base=f.base[edit.path];if(base&&base.version!==doc.version)conflicts.push({path:edit.path,version:doc.version,base:{...doc.base,content:base.content},local:doc.value,disk:{...doc.base,content:edit.content}});}
    f.pendingPrepared={selection,prepared,versions};f.pendingMerge=conflicts;f.resolutions={};
    await this.update(f,{});
   }
   const unresolved=(f.pendingMerge||[]).filter(c=>!f.resolutions?.[c.path]||f.resolutions[c.path].version!==c.version);
   if(unresolved.length)fail('BINDING_CONFLICT','相关源码已变化；请点击“比较并合并”，已有验收和产物保留。');
   const edits=[];for(const edit of prepared.edits){const doc=await this.source.read(edit.path,r.session);if(doc.version!==f.pendingPrepared.versions[edit.path])fail('BINDING_CONFLICT','合并期间编辑稿又发生变化，请重新比较：'+edit.path);const resolved=f.resolutions?.[edit.path];edits.push({...edit,content:resolved?resolved.text:edit.content,version:doc.version});}
   const signature=digest(edits),callId='creative-apply:'+f.id+':'+signature;
   await this.update(f,{status:'applying',appliedPrepared:{edits,selection,signature,callId,prepared}});
   const receipt=await this.source.commit(edits,r.session,{conversationId:r.id,roundId:r.round||f.roundId,callId});
   await this.finishApply(r,f,prepared,edits,selection,{batchId:receipt.batchId,transaction:receipt.transaction});return this.public(f);
  }catch(error){await this.update(f,{status:'accepted_pending_apply',error:sanitize(error)});throw error;}
 }
 async finishApply(r,f,prepared,edits,selection,receipt){const source=prepared.path?edits.find(e=>e.path===prepared.path):null;
  f.base=await this.base(r,f.kind,f.target,f.fragmentId);for(const edit of edits){const base=f.base[edit.path];if(!base)continue;if(base.content!==edit.content)base.version='changed-after-save:'+digest([base.version,edit.content]);base.content=edit.content;base.hash=textHash(edit.content);}
  return this.update(f,{status:'bound',error:undefined,entryIds:prepared.entryIds,label:prepared.label,path:prepared.path,sceneId:prepared.sceneId,nodeMap:prepared.nodeMap,...receipt,
   appliedSourceHash:source?textHash(source.content):f.appliedSourceHash,appliedSelection:selection,appliedPrepared:undefined,pendingPrepared:undefined,pendingMerge:undefined,resolutions:undefined});
 }
 async resolveMerge(r,{creativeId,path:relative,version,text}){const f=this.get(creativeId,r);const conflict=f.pendingMerge?.find(c=>c.path===relative);if(!conflict||conflict.version!==version||typeof text!=='string'||Buffer.byteLength(text)>4*1024*1024)fail('REVIEW_STALE','合并版本已失效，请重新比较。');const doc=await this.source.read(relative,r.session);if(doc.version!==version)fail('BINDING_CONFLICT','合并期间源码又有修改，请重新比较。');f.resolutions||={};f.resolutions[relative]={version,text};return this.public(await this.update(f,{}));
 }

 importSpec(f,c,imported={}){return {key:c.key,kind:c.kind,jobId:c.jobId,sha256:c.artifact.sha256,ttsHash:c.ttsHash,candidateId:c.id,promptRevision:c.promptRevision,assetType:c.kind==='voice'?'voice':c.request.assetType||'background',...imported};}
 body(f){return {creativeId:f.id,kind:f.kind,title:f.title,plan:f.plan,request:f.request,target:f.target,fragmentId:f.fragmentId};}
 async preview(r,creativeId){if(this.active.has(creativeId)||this.applying.has(creativeId))fail('CREATIVE_BUSY','请等待当前操作完成后再试玩候选。');const f=this.get(creativeId,r);this.assert(r.session,f.projectRoot);const candidates=this.validateSelection(f);for(const c of candidates)if(!c.storage)await this.stash(f,c,r);
  const state=await this.source.snapshot(r.session),candidateVersion=digest([f.plan||f.request,candidates.map(c=>c.id),overlays(state)]);const result=await this.requestMedia('/api/generated-media/preview',{...this.body(f),projectRoot:f.projectRoot,projectSession:r.session,state,candidateVersion,replaceHash:f.appliedSourceHash,entryIds:f.entryIds,imports:candidates.map(c=>this.importSpec(f,c))});await this.update(f,{candidatePreview:{taskId:result.task.id,version:candidateVersion,label:result.label,viewSignature:candidateSignature(f),sourceVersion:digest([overlays(state),state.metadata,state.project.revision])}});return {...result,state};
 }
 async resume(id,r){const f=this.get(id,r);for(const job of this.jobs.list(f.projectRoot).jobs.filter(j=>j.creativeId===f.id&&!j.artifact&&j.downloadAvailable))await this.jobs.resumeDownload(job.id);for(const job of this.jobs.list(f.projectRoot).jobs.filter(j=>j.creativeId===f.id&&j.artifact)){const item=f.items[job.fragmentKey];if(item&&!item.candidates.some(c=>c.jobId===job.id)){const revision=item.revisions.find(p=>p.id===job.promptRevision);const c={id:uid('candidate'),key:item.key,kind:item.kind,jobId:job.id,promptRevision:job.promptRevision,generationMessageId:job.generationMessageId,request:revision?.request,artifact:job.artifact,created:job.created,ttsHash:job.ttsHash,fixture:job.fixture,estimate:job.estimate,usage:job.usage};item.candidates.push(c);item.selectedId=c.id;}}for(const item of Object.values(f.items))for(const c of item.candidates)if(!c.storage)await this.stash(f,c,r);if(!Object.values(f.items).some(i=>i.candidates.length))fail('RECOVERY_UNAVAILABLE','尚无可恢复的产物；不会通过恢复重新提交收费请求。');return this.public(await this.update(f,{status:f.fragmentAccepted?'accepted_pending_apply':'awaiting_review',error:undefined}));}
 async execution(id,phase,result){const f=this.active.get(id)?.record||this.applying.get(id)?.record||this.get(id);return this.update(f,{[phase]:{status:result.status,contentHash:result.contentHash,candidateVersion:result.candidateVersion||f.candidatePreview?.version,stale:!!result.stale||!!result.candidateVersion&&result.candidateVersion!==f.candidatePreview?.version,exitCode:result.exitCode}});}
 async cancel(id){const f=this.get(id);const active=this.active.get(id);if(active){active.controller.abort();return this.public(f);}if(this.applying.has(id))fail('CREATIVE_BUSY','源码事务正在完成，请等待后再操作。');return this.update(f,{status:'cancelled',error:'已停止后续生成，已有候选保留。'});}
 async stop(root,conversationId){for(const [id,active] of this.active){const f=this.records(root).find(f=>f.id===id);if(f&&(!conversationId||f.conversationId===conversationId))active.controller.abort();}}
}
module.exports={CreativeCoordinator,generationIntent,REGISTRY};
