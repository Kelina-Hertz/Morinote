import type {AIEvent} from './ai-types';

export type ToolEntry={event:AIEvent;result?:AIEvent};
export type TranscriptItem=
 | {kind:'tools';key:string;tools:ToolEntry[]}
 | {kind:'message';key:string;event:AIEvent};

export const eventData=(event:AIEvent):Record<string,unknown>=>
 event.data&&typeof event.data==='object'?event.data as Record<string,unknown>:{};
const ignored=new Set(['result','step','usage','reviewer_usage','approval','thinking','failure','change_checkpoint','checkpoint_result']);
const id=(value:unknown)=>value===undefined||value===null?'':String(value);

// Keep one group across internal events, but never fold user messages or replies into it.
export function transcriptItems(events:AIEvent[]):TranscriptItem[]{
 const results=new Map<string,AIEvent>(),legacyResults:AIEvent[]=[],usedLegacy=new Set<AIEvent>();
 for(const event of events)if(event.type==='result'){
  const callId=id(eventData(event).callId);
  if(callId)results.set(callId,event);else legacyResults.push(event);
 }
 let lastTextOrUser=-1;
 events.forEach((event,index)=>{if(event.type==='text'||event.type==='user')lastTextOrUser=index;});
 const items:TranscriptItem[]=[];
 events.forEach((event,index)=>{
  const data=eventData(event),key=event.messageId||String(event.seq);
  if(ignored.has(event.type)||event.type==='status'&&['running','idle','回复完成。'].includes(String(event.data)))return;
  if(event.type==='stream'&&index<lastTextOrUser)return;
  if(event.type==='tool'){
   if(data.name==='catalog')return;
   const callId=id(data.callId);
   // Repeated reads must match their own result, never another read's completion.
   const result=callId?results.get(callId):legacyResults.find(candidate=>!usedLegacy.has(candidate)&&candidate.seq>event.seq&&eventData(candidate).name===data.name);
   if(result&&!callId)usedLegacy.add(result);
   const previous=items[items.length-1];
   if(previous?.kind==='tools')previous.tools.push({event,result});
   else items.push({kind:'tools',key,tools:[{event,result}]});
  }else items.push({kind:'message',key,event});
 });
 return items;
}

export function toolFailed(result?:AIEvent):boolean{
 if(!result)return false;
 const data=eventData(result),value=data.result&&typeof data.result==='object'?data.result as Record<string,unknown>:data;
 return !!(data.error||value.error||value.isError)||value.loaded===false||['failed','error','timeout','denied','sandbox_unavailable','not_run'].includes(String(value.status));
}

export function toolName(event:AIEvent):string{
 const name=String(eventData(event).name||'操作').replace(/^morinote_/,'');
 const names:Record<string,string>={generate_fragment:'生成片段候选',generate_media:'生成素材候选',creative_draft:'完善创作提示',creative_revise:'修改提示词',creative_candidates:'查看创作版本',creative_generate:'生成所选素材',creative_apply:'应用已验收结果',creative_preview:'试玩候选片段',creative_lint:'检查候选片段',read_candidate:'查看候选素材',read:'读取源码',write:'保存源码',edit:'修改源码',workspace:'查询剧情与演出',operate:'更新编辑稿',assets:'查询素材',files:'读取目录',project:'读取项目概览',checkpoint:'确认修改',catalog:'初始化工具',lint:'Ren’Py lint',test:'运行测试',preview:'启动试玩',skill:'读取制作指南',guide:'读取操作指南',terminal:'执行终端命令',analyze:'分析源码',validate:'检查源码',screenshot:'获取截图',preview_status:'查询试玩状态',stop_preview:'停止试玩',read_image:'读取图片'};
 return names[name]||name;
}
