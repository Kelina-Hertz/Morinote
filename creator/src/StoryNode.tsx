import {useEffect,type ReactNode} from 'react';
import {Handle,Position,useUpdateNodeInternals,type Node,type NodeProps} from '@xyflow/react';
import type {FlowEditPoint} from './native-types';

export type StoryData={content:ReactNode;outputs:FlowEditPoint[];targetable:boolean;busy:boolean;connecting:boolean;destination:(point:FlowEditPoint)=>string;onCreate:(point:FlowEditPoint,x:number,y:number)=>void;onConnect:(point:FlowEditPoint)=>void;onAddOption?:()=>void;onRename:(point:FlowEditPoint,text:string)=>Promise<void>};
export default function StoryNode({id,data}:NodeProps<Node<StoryData,'story'>>){
 const update=useUpdateNodeInternals(),ports=data.outputs.map(p=>p.id).join(',');
 useEffect(()=>update(id),[id,ports,data.connecting,update]);
 const branches=data.outputs.some(p=>p.title);
 return <>
  <Handle type="target" id="entry" position={Position.Top} className={data.connecting&&data.targetable?'flow-entry-surface':undefined} isConnectable={data.targetable&&!data.busy} isConnectableStart={false}/>
  {data.content}
  <Handle type="source" id="display" position={Position.Bottom} isConnectable={false} style={{opacity:0,pointerEvents:'none'}}/>
  {branches?<div className="flow-outlets">{data.outputs.map(point=><div className="flow-outlet" key={point.id}>
   {point.actions.includes('rename')?<input className="flow-option-title nodrag nopan" aria-label={'选项文字：'+point.title} key={point.id+point.title} defaultValue={point.title} disabled={data.busy} onKeyDown={e=>{if(e.key==='Enter')e.currentTarget.blur();if(e.key==='Escape'){e.currentTarget.value=point.title;e.currentTarget.blur();}}} onBlur={e=>{const input=e.currentTarget,text=input.value.trim();if(!text||text===point.title){input.value=point.title;return;}void data.onRename(point,text).catch(()=>{input.value=point.title;});}}/>:<span>{point.title}</span>}
   <button className={'flow-outlet-destination nodrag nopan '+(point.status==='pending'?'is-pending':'')} disabled={data.busy} title="选择后续剧情" onClick={e=>{e.stopPropagation();data.onConnect(point);}}>{data.destination(point)}</button>
   <button className="nodrag nopan" disabled={data.busy} aria-label={'在'+point.title+'后新建'} title="新建或设置出口" onClick={e=>{e.stopPropagation();data.onCreate(point,e.clientX,e.clientY);}}>＋</button>
   <Handle id={point.id} type="source" position={Position.Right} className="flow-edit-handle" isConnectable={!data.busy} isConnectableEnd={false} aria-label={'连接'+point.title} title={'连接'+point.title}/>
  </div>)}</div>:data.outputs.map(point=><div className="flow-next" key={point.id}>
   <span className={point.status==='pending'?'flow-outlet-status is-pending':'flow-outlet-status'}>{data.destination(point)}</span>
   <button className="nodrag nopan" disabled={data.busy} aria-label="添加后续" onClick={e=>{e.stopPropagation();data.onCreate(point,e.clientX,e.clientY);}}>＋ 后续</button>
   <Handle id={point.id} type="source" position={Position.Bottom} className="flow-edit-handle" isConnectable={!data.busy} isConnectableEnd={false} aria-label="连接场景后续" title="连接后续剧情"/>
  </div>)}
  {data.onAddOption&&<button className="flow-add-option nodrag nopan" disabled={data.busy} onClick={e=>{e.stopPropagation();data.onAddOption?.();}}>＋ 选项</button>}
 </>;
}
