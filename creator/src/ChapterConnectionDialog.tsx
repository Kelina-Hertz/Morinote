import {useState} from 'react';
import {ArrowRight} from 'lucide-react';
import type {Project} from './types';
import type {NativeFlow,NativeOperation,FlowEditPoint} from './native-types';
import {chapterConnectionEndpoints,flowHashes,formsCycle} from './flow-authoring';
import {sceneTitle} from './scene-titles';
import {Modal} from './ui';

export interface ChapterConnection {from:string;to:string;point?:FlowEditPoint;target?:string}
export default function ChapterConnectionDialog({connection,flow,project,onOperation,onClose,onComplete,onInspect}:{connection:ChapterConnection;flow:NativeFlow;project:Project;onOperation:NativeOperation;onClose:()=>void;onComplete:(message:string)=>void;onInspect:()=>void}){
 const {exits,targets,point:defaultPoint,target:defaultTarget}=chapterConnectionEndpoints(flow,connection);
 const [pointId,setPointId]=useState(defaultPoint?.id||'');
 const [targetId,setTargetId]=useState(connection.target||defaultTarget?.id||'');
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const point=exits.find(p=>p.id===pointId),target=targets.find(n=>n.id===targetId);
 const original=point?.target?sceneTitle(project,point.target):'结束／返回';
 const reasons=[...new Set(flow.nodes.filter(n=>n.type==='scene'&&[connection.from,connection.to].includes(n.group)&&n.blockedReason).map(n=>n.blockedReason!))];
 const exitTitle=(p:FlowEditPoint)=>sceneTitle(project,p.owner)+(p.title?' · '+p.title:'');
 async function submit(){
  if(!point||!target||busy)return;setBusy(true);setError('');
  try{await onOperation('flow',{operation:'connect_exit',point:point.id,target:target.id,hashes:flowHashes(flow.authoring!.documents,[])});onComplete(`已连接：${connection.from} · ${exitTitle(point)} → ${connection.to} · ${sceneTitle(project,target.id)}`);onClose();}
  catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <Modal title="连接章节" onClose={()=>{if(!busy)onClose();}}><form className="modal-body creation-form" onSubmit={e=>{e.preventDefault();void submit();}}>
  <div className="chapter-connection-heading"><strong>{connection.from}</strong><ArrowRight size={16}/><strong>{connection.to}</strong></div>
  <p className="creation-note">这个章节有多个可用连接位置，请选择本次要连接的位置。</p>
  <label>从哪个剧情出口离开<select aria-label="章节连接出口" value={pointId} disabled={busy||!!connection.point} onChange={e=>setPointId(e.target.value)}><option value="">选择出口</option>{exits.map(p=><option key={p.id} value={p.id}>{exitTitle(p)} → {p.target?sceneTitle(project,p.target):'结束／返回'}</option>)}</select></label>
  <label>进入哪个场景<select aria-label="章节连接入口" value={targetId} disabled={busy||!!connection.target} onChange={e=>setTargetId(e.target.value)}><option value="">选择入口场景</option>{targets.map(n=><option key={n.id} value={n.id}>{sceneTitle(project,n.id)}</option>)}</select></label>
  {point&&target&&<p className="creation-note">将“{exitTitle(point)}”的去向从“{original}”改为“{sceneTitle(project,target.id)}”。</p>}
  {point&&target&&formsCycle(flow,point.owner,target.id)&&<p className="flow-cycle-warning" role="status">此连接会形成循环路径，请确认这是预期的剧情走向。</p>}
  {!exits.length&&<p className="creation-error">这个章节没有可直接连接的简单出口，请展开章节查看具体剧情。</p>}
  {!targets.length&&<p className="creation-error">这个章节没有可连接的场景入口，请展开章节查看详情。</p>}
  {(!exits.length||!targets.length)&&<>{reasons.slice(0,3).map(reason=><p key={reason} className="creation-error">{reason}</p>)}<button type="button" onClick={onInspect}>展开章节查看具体剧情</button></>}
  {error&&<p className="creation-error" role="alert">{error}</p>}
  <div className="creation-actions"><button type="button" disabled={busy} onClick={onClose}>取消</button><button type="submit" className="primary" disabled={busy||!point||!target}>{busy?'正在连接…':'确认连接'}</button></div>
 </form></Modal>;
}
