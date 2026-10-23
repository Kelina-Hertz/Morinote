import {useEffect} from 'react';
import {Handle,Position,useUpdateNodeInternals,type Node,type NodeProps} from '@xyflow/react';
import type {ChapterEntry,ChapterPort} from './chapter-ports';
import './chapter-ports.css';

export type ChapterData={
 label:string;title:string;collapsed:boolean;busy:boolean;connecting:boolean;
 ports:ChapterPort[];entries:ChapterEntry[];entry?:ChapterEntry;entryReason?:string;exit?:ChapterPort;exitReason?:string;
 entryPreference:string;exitPreference:string;nextTitle?:string;chapters:{id:string;title:string;ready:boolean}[];
 onEntry:(id:string)=>void;onExit:(id:string)=>void;onNext:(group:string)=>void;onOpen:()=>void;onToggle:()=>void;
};

export default function ChapterNode({id,data}:NodeProps<Node<ChapterData,'group'>>){
 const update=useUpdateNodeInternals();
 const handles=data.ports.map(port=>port.point.id).join('|');
 const extraPorts=data.ports.filter(port=>port.point.id!==data.exit?.point.id);
 useEffect(()=>{update(id);},[id,data.collapsed,data.connecting,data.entry?.sceneId,data.exit?.point.id,handles,update]);
 return <>
  <Handle type="source" id="display-source" position={Position.Bottom} isConnectable={false} className="chapter-display-handle"/>
  <Handle type="target" id="display-target" position={Position.Top} isConnectable={false} className="chapter-display-handle"/>
  {data.entry&&<Handle type="target" id={'chapter-entry:'+data.entry.sceneId} position={Position.Top} isConnectable={!data.busy} isConnectableStart={false} className="chapter-main-entry" aria-label={'进入'+data.title} title={'章节入口：'+data.entry.caption}/>}
  <div className="flow-chapter-label"><div className="flow-chapter-heading">
   <strong><span className="chapter-container-badge">章节</span>{data.label}</strong>
   <button type="button" className="nodrag nopan" aria-expanded={!data.collapsed} aria-label={(data.collapsed?'展开':'折叠')+data.title} onClick={event=>{event.stopPropagation();if(event.detail<2)data.onToggle();}} onDoubleClick={event=>event.stopPropagation()}><span className="flow-triangle" aria-hidden="true">{data.collapsed?'▸':'▾'}</span></button>
  </div><div className="chapter-navigation nodrag nopan">
   <button type="button" className="chapter-open" disabled={!data.entry||data.busy} title={data.entry?.caption||data.entryReason} onClick={event=>{event.stopPropagation();data.onOpen();}}>进入章节</button>
   <details className="chapter-endpoint-settings" onClick={event=>event.stopPropagation()}>
    <summary title={data.entry?.caption||data.entryReason}>入口设置</summary><div>
     <label>本章入口<select aria-label={data.title+'入口'} value={data.entryPreference} disabled={data.busy} onChange={event=>data.onEntry(event.target.value)}><option value="">自动选择</option>{data.entryPreference&&!data.entries.some(entry=>entry.sceneId===data.entryPreference)&&<option value={data.entryPreference}>原入口已失效</option>}{data.entries.map(entry=><option key={entry.sceneId} value={entry.sceneId}>{entry.caption}</option>)}</select></label>
     <small>{data.entry?'当前入口：'+data.entry.caption:data.entryReason}</small>
     <label>后续出口<select aria-label={data.title+'后续出口'} value={data.exitPreference} disabled={data.busy} onChange={event=>data.onExit(event.target.value)}><option value="">自动选择</option>{data.exitPreference&&!data.ports.some(port=>port.point.id===data.exitPreference)&&<option value={data.exitPreference}>原出口已失效</option>}{data.ports.map(port=><option key={port.point.id} value={port.point.id}>{port.caption}</option>)}</select></label>
     <small>{data.exit?'当前出口：'+data.exit.caption:data.exitReason}</small><small>设置用于新连接，已有跳转保持原去向。</small>
    </div>
   </details>
   <div className="chapter-next" title={data.exit?.caption||data.exitReason}>
    <select aria-label={data.title+'下一章'} value="" disabled={data.busy||!data.exit} onChange={event=>{event.stopPropagation();if(event.target.value)data.onNext(event.target.value);}}><option value="">{data.nextTitle?'→ '+data.nextTitle:'连接下一章'}</option>{data.chapters.filter(chapter=>'group:'+chapter.id!==id).map(chapter=><option key={chapter.id} value={chapter.id} disabled={!chapter.ready}>{chapter.title}{!chapter.ready?'（需设置入口）':''}</option>)}</select>
    {data.exit&&<Handle type="source" id={'chapter-exit:'+data.exit.point.id} position={Position.Right} isConnectable={!data.busy} isConnectableEnd={false} className="flow-edit-handle chapter-main-exit" aria-label={'连接'+data.title+'下一章'} title="拖到下一章的入口"/>}
   </div>
  </div></div>
  {data.collapsed&&<div className="chapter-proxy-ports">
   {data.entry?<div className={'chapter-proxy-entry'+(data.connecting?' is-connecting':'')}>
    <span>入口</span><strong>{data.entry.caption}</strong>
   </div>:<small className="chapter-no-exits">{data.entryReason}</small>}
   <div className="chapter-proxy-exits">
    {extraPorts.length?extraPorts.map(port=><div className="chapter-proxy-exit" key={port.point.id}>
     <span title={port.caption}>{port.caption}</span>
     <small title={port.targetCaption}>{port.targetCaption?'→ '+port.targetCaption:port.point.status==='pending'?'待连接':'结束此段'}</small>
     <Handle type="source" id={port.point.id} position={Position.Right} isConnectable={!data.busy} isConnectableEnd={false} className="flow-edit-handle" aria-label={'连接'+port.caption} title={'连接后续：'+port.caption}/>
    </div>):!data.exit&&<span className="chapter-no-exits">{data.exitReason}</span>}
   </div>
  </div>}
 </>;
}
