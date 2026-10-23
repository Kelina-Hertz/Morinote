import type {FlowEditPoint,NativeFlow,NativeFlowNode} from './native-types';
import type {FlowIntent} from './flow-authoring';
import type {Project} from './types';
import {ArrowRight,GitBranch,Plus,Settings2,Unplug} from 'lucide-react';
import {sceneTitle} from './scene-titles';

export default function FlowAuthoringActions({node,flow,project,onIntent,onCondition,onAddOption}:{node:NativeFlowNode;flow:NativeFlow;project:Project;onIntent:(mode:FlowIntent,point:FlowEditPoint)=>void;onCondition:(point:FlowEditPoint)=>void;onAddOption:(point:string)=>void}){
 const points=flow.authoring?.points||{},exit=node.editPoint?points[node.editPoint]:undefined;
 const menu=node.branchPoint?points[node.branchPoint]:Object.values(points).find(p=>p.kind==='menu'&&p.owner===node.id);
 const condition=node.conditionPoint?points[node.conditionPoint]:undefined;
 if(!['scene','choice','condition'].includes(node.type))return null;
 return <section className="flow-authoring-actions">
  <div className="flow-section-heading"><h3>{node.optionPoints?.length?'分支与连接':'剧情创作'}</h3>{node.optionPoints?.length?<span>{node.optionPoints.length} 个出口</span>:null}</div>
  <div className="flow-action-stack">
   {node.type==='scene'&&!node.blockKind&&<><button disabled={!exit?.actions.includes('insert')} onClick={()=>exit&&onIntent('insert',exit)}><Plus size={15}/>在此之后插入场景</button><button disabled={!exit?.actions.includes('connect')} onClick={()=>exit&&onIntent('connect',exit)}><ArrowRight size={15}/>连接已有场景</button></>}
   {condition&&<button onClick={()=>onCondition(condition)}><Settings2 size={15}/>修改判断条件</button>}
   {!menu&&!condition&&<button disabled={!exit?.actions.includes('branch')} onClick={()=>{if(exit)onIntent('branch',exit);}}><GitBranch size={15}/>新增分支</button>}
  </div>
  {!!node.optionPoints?.length&&<div className="flow-destination-list">{node.optionPoints.map((id,index)=>{const point=points[id];return point?<button className={'flow-destination'+(!point.target?' is-unconnected':'')} key={id} onClick={()=>onIntent('connect',point)} aria-label={`连接“${point.title}”的目标`}><span className="flow-outlet-index">{index+1}</span><span className="flow-destination-copy"><strong>{point.title}</strong><small>{point.target?sceneTitle(project,point.target):'未连接 · 点击选择去向'}</small></span>{point.target?<ArrowRight size={15}/>:<Unplug size={15}/>}</button>:null;})}</div>}
  {menu&&<button className="flow-add-outlet" onClick={()=>onAddOption(menu.id)}><Plus size={15}/>添加选项</button>}
  {node.blockedReason&&!node.blockKind&&<p className="flow-inspector-note">{node.blockedReason}</p>}
  <p className="flow-inspector-note">拖动节点出口连接剧情，选中连线后按 Delete 断开。</p>
 </section>;
}
