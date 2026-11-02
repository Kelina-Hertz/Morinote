'use strict';
const {MediaStore}=require('./media-store.cjs');
const {ProviderRegistry}=require('./provider-registry.cjs');
const {JobManager}=require('./job-manager.cjs');
const {CreativeCoordinator}=require('./creative-coordinator.cjs');
const {LLMBudgetProxy}=require('./llm-budget-proxy.cjs');
const {fail}=require('./common.cjs');
const {DEFAULTS}=require('./media-store.cjs');
const {textHash,digest}=require('./common.cjs');
const {overlays}=require('./fragment-coordinator.cjs');
class MediaService{
 constructor(options){Object.assign(this,{context:options.context,source:options.source});this.registry=new ProviderRegistry(options);try{this.store=new MediaStore(options.directory,options.safeStorage);this.jobs=new JobManager({...options,store:this.store,registry:this.registry});this.fragments=new CreativeCoordinator({...options,jobs:this.jobs,store:this.store});this.ready=this.jobs.recover().catch(error=>{this.error=error.message;});}catch(error){this.error=error.message;this.ready=Promise.resolve();}}
 assertReady(){if(this.error)fail('MEDIA_STORAGE_UNAVAILABLE',this.error+' 媒体生成已暂停，原记录保留；源码编辑和文字对话可以继续。');}
 settings(){if(this.error){const settings={mode:'mock',taskBudgetCny:.5,secureStorage:false,error:this.error,providers:Object.fromEntries(Object.entries(DEFAULTS).map(([id,value])=>[id,{...value,hasKey:false,credentialStatus:'unavailable'}]))};return {...settings,capabilities:this.registry.describe(settings)};}const settings=this.store.settings();return {...settings,providers:settings.providers,capabilities:this.registry.describe(settings)};}
 status(){const root=this.context()?.root;if(!root||this.error)return {settings:this.settings(),jobs:[],runs:[],fragments:[],creations:[]};try{const records=this.fragments.records(root);return {settings:this.settings(),...this.jobs.list(root),fragments:records.filter(f=>f.legacy).map(({plan,...record})=>record),creations:records.filter(f=>!f.legacy).map(f=>this.fragments.public(f))};}catch(error){this.error=error.message;return {settings:this.settings(),jobs:[],runs:[],fragments:[],creations:[]};}}
 async currentStatus(){const result=this.status();if(!result.creations.some(f=>f.candidatePreview||f.kind==='voice'&&f.target?.nodeId))return result;
  const state=await this.source.snapshot(this.context().session),sourceVersion=digest([overlays(state),state.metadata,state.project.revision]),lines=state.project.scenes?.flatMap(s=>s.lines)||[];
  for(const f of result.creations){if(f.kind==='voice'&&f.target?.nodeId){const line=lines.find(l=>l.id===f.target.nodeId);f.targetStale=!line||textHash(line.text.replace(/\[\[/g,'[').replace(/\{\{/g,'{'))!==f.target.textHash||line.speaker!==f.target.speaker;}
   if(f.candidatePreview?.sourceVersion&&f.candidatePreview.sourceVersion!==sourceVersion){if(f.preview)f.preview.stale=true;if(f.lint)f.lint.stale=true;}}
  return result;
 }

 modelResult(f){const run=this.jobs.run(f.runId);return {id:f.id,creativeId:f.id,kind:f.kind,title:f.title,status:f.status,editVersion:f.editVersion,runId:f.runId,fixture:f.fixture,error:f.error,
  items:Object.values(f.items||{}).map(item=>({key:item.key,kind:item.kind,promptRevision:item.revisions.at(-1)?.id,selectedId:item.selectedId,acceptedId:item.acceptedId,candidateCount:item.candidates.length,candidates:item.candidates.slice(-3).map(c=>({id:c.id,sha256:c.artifact?.sha256,fixture:c.fixture,voiceSetting:c.effectiveParameters?.voice_setting}))})),usage:run.media,
  message:f.status==='bound'?'已验收并应用。':f.status==='draft'?'提示词已保存，未提交生成。':Object.values(f.items||{}).some(i=>i.candidates.length)?'已有候选保留，等待用户验收；缺少的项目请查看各项状态。':'尚未生成候选，请查看错误或额度状态。'};}
 modelQuery(f,{itemKey,includePlan=false,includeHistory=false}={}){const result=this.modelResult(f);return {...result,items:result.items.filter(item=>!itemKey||item.key===itemKey).map(item=>{const source=f.items[item.key],last=source.revisions.at(-1);return {...item,prompt:last?{id:last.id,number:last.number,brief:last.brief,request:last.request}:undefined,...(includeHistory&&itemKey?{history:source.revisions.slice(-5).map(r=>({id:r.id,number:r.number,request:r.request,feedback:r.feedback})),historyTotal:source.revisions.length}:{})};}),...(includePlan?{plan:f.plan}:{}),hint:'Latest prompts only; use itemKey to focus, includePlan for full fragment text, includeHistory with itemKey for the last five prompt versions. Disk paths and repeated historical payloads are omitted.'};}
 async configure(payload){await this.ready;this.assertReady();this.store.configure(payload);return this.settings();}
 async acceptance(conversationId){await this.ready;this.assertReady();const run=await this.jobs.ensureRun({projectRoot:this.context().root,profile:'acceptance-low-cost',conversationId,mode:this.store.data.mode});return {runId:run.id,profile:run.profile,mode:run.mode};}
 async proxy(runId,credentials){await this.ready;this.assertReady();return new LLMBudgetProxy({jobs:this.jobs,runId,credentials}).start();}
 async generate(r,plan,callId,runId,args={}){await this.ready;this.assertReady();return this.fragments.generate(r,plan,{...args,callId,runId});}
 async resume(id,r){await this.ready;this.assertReady();return this.fragments.resume(id,r);}
 async stop(conversationId){const root=this.context()?.root;if(root)await this.fragments?.stop(root,conversationId);}
}
module.exports={MediaService};
