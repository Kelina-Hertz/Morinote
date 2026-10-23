import {useState} from 'react';
import type {Project} from './types';
import type {FlowEditPoint,NativeFlow,NativeOperation} from './native-types';
import {Modal} from './ui';
import ScenePicker from './ScenePicker';
import {sceneTitle} from './scene-titles';
import {sceneFieldErrors} from './creation-model';
import {flowHashes,formsCycle,freshScene,type BranchRow,type FlowIntent,type NewFlowScene} from './flow-authoring';
import './creation-dialogs.css';

type Props={mode:FlowIntent;point:FlowEditPoint;flow:NativeFlow;project:Project;initialTarget?:string;onOperation:NativeOperation;onClose:()=>void;onComplete:(result:{scene?:string;branchOwner?:string;message:string})=>void};
function SceneFields({value,onChange,project,disabled}:{value:NewFlowScene;onChange:(value:NewFlowScene)=>void;project:Project;disabled:boolean}){
 const errors=sceneFieldErrors(value.title,value.name,value.path,project.nativeRenpy?.labels||[]);
 return <><label>新场景名称<input aria-label="新场景名称" maxLength={120} disabled={disabled} value={value.title} onChange={e=>onChange({...value,title:e.target.value})}/></label><details className="creation-advanced"><summary>高级设置</summary><label>标签名称<input disabled={disabled} value={value.name} onChange={e=>onChange({...value,name:e.target.value})}/></label>{errors.name&&<small className="creation-error">{errors.name}</small>}<label>源码文件<input disabled={disabled} value={value.path} onChange={e=>onChange({...value,path:e.target.value})}/></label>{errors.path&&<small className="creation-error">{errors.path}</small>}</details></>;
}

export default function FlowAuthoringDialog({mode,point,flow,project,initialTarget,onOperation,onClose,onComplete}:Props){
 const labels=project.nativeRenpy?.labels||[],owner=flow.nodes.find(n=>n.id===point.owner),group=owner?.group||'剧情';
 const allowed=(flow.authoring?.targets||[]).filter(t=>!t.reason).map(t=>t.id);
 const labelName=(id?:string|null)=>labels.find(l=>l.id===id)?.name||'';
 const [scene,setScene]=useState(()=>freshScene(project,group)),[target,setTarget]=useState(()=>labelName(initialTarget));
 const [rows,setRows]=useState<BranchRow[]>(()=>{
  const make=(text='',kind:BranchRow['kind']='new',target=''):BranchRow=>({id:crypto.randomUUID(),text,kind,target,scene:freshScene(project,group)});
  return point.kind==='menu'?[make()]:[make(point.target?'继续原剧情':'结束此段',point.target?'existing':'return',labelName(point.target)),make()];
 });
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const allowedTarget=(name:string)=>labels.find(l=>l.name===name&&allowed.includes(l.id));
 const sceneValid=(s:NewFlowScene)=>!Object.values(sceneFieldErrors(s.title,s.name,s.path,labels)).some(Boolean);
 const valid=!!flow.authoring?.points[point.id]&&(mode==='connect'?!!allowedTarget(target):mode==='insert'?sceneValid(scene):rows.length>0&&rows.every(row=>row.text.trim()&&(row.kind==='return'||row.kind==='new'&&sceneValid(row.scene)||row.kind==='existing'&&allowedTarget(row.target))));
 const current=point.target?sceneTitle(project,point.target):point.status==='pending'?'待连接':'结束此段';
 const cyclic=mode==='connect'&&allowedTarget(target)&&formsCycle(flow,point.owner,allowedTarget(target)!.id)||mode==='branch'&&rows.some(r=>r.kind==='existing'&&allowedTarget(r.target)&&formsCycle(flow,point.owner,allowedTarget(r.target)!.id));
 function update(id:string,patch:Partial<BranchRow>){setRows(v=>v.map(r=>r.id===id?{...r,...patch}:r));}
 function move(index:number,offset:number){setRows(v=>{const next=[...v];[next[index],next[index+offset]]=[next[index+offset],next[index]];return next;});}
 async function submit(){
  if(!valid||busy)return;setBusy(true);setError('');
  try{
   const created=mode==='insert'?[scene]:mode==='branch'?rows.filter(r=>r.kind==='new').map(r=>r.scene):[];
   const base={point:point.id,hashes:flowHashes(flow.authoring!.documents,created)};
   if(mode==='connect')await onOperation('flow',{...base,operation:'connect_exit',target:allowedTarget(target)!.id});
   else if(mode==='insert')await onOperation('flow',{...base,operation:'insert_after',scene:{...scene,title:scene.title.trim()}});
   else await onOperation('flow',{...base,operation:'branch_exit',options:rows.map(row=>({text:row.text,destination:row.kind==='return'?{kind:'return'}:row.kind==='existing'?{kind:'existing',label:allowedTarget(row.target)!.id}:{kind:'new',scene:{...row.scene,title:row.scene.title.trim()}}}))});
   onComplete(mode==='branch'?{branchOwner:point.owner,message:point.kind==='menu'?'已追加分支，现有选项保持不变。':'已在场景结尾建立分支，新建分支场景独立结束。'}:mode==='insert'?{scene:scene.name,message:`已插入“${scene.title}”，之后继续${current}。`}:{scene:target,message:`已连接到“${sceneTitle(project,target)}”。`});
   onClose();
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <Modal title={{connect:'连接已有场景',insert:'在此之后插入场景',branch:'新增分支'}[mode]} wide={mode==='branch'} onClose={()=>{if(!busy)onClose();}}><form className="modal-body creation-form" onSubmit={e=>{e.preventDefault();void submit();}}>
  <p className="creation-note">{sceneTitle(project,point.owner)}{point.title?' · '+point.title:''} · 当前去向：{point.kind==='menu'?'现有选项保持不变':current}</p>
  {mode==='insert'?<><SceneFields value={scene} onChange={setScene} project={project} disabled={busy}/><p className="creation-note">播放新场景后继续原去向。创建到“{group}”。</p></>:mode==='connect'?<><ScenePicker project={project} value={target} onChange={setTarget} allowedIds={allowed} disabled={busy}/><p className="creation-note">{current} → {target?sceneTitle(project,target):'选择目标'}</p></>:<>
   {point.kind==='menu'&&<div className="creation-note">已有选项：{point.options?.map(id=>flow.authoring?.points[id]?.title).join(' ／ ')}</div>}
   {rows.map((row,index)=><fieldset className="choice-row" key={row.id} disabled={busy}><legend>新增选项 {index+1}</legend><label>选项文字<input aria-label={`分支 ${index+1} 文字`} value={row.text} onChange={e=>update(row.id,{text:e.target.value})}/></label>{!row.text.trim()&&<small className="creation-error">请填写选项文字。</small>}<label>选项去向<select aria-label={`分支 ${index+1} 去向`} value={row.kind} onChange={e=>update(row.id,{kind:e.target.value as BranchRow['kind']})}><option value="existing">连接已有场景</option><option value="new">新建场景</option><option value="return">结束此段／返回</option></select></label>{row.kind==='existing'?<ScenePicker project={project} value={row.target} onChange={target=>update(row.id,{target})} allowedIds={allowed} label={`分支 ${index+1} 目标场景`} error={allowedTarget(row.target)?'':'请选择可连接的场景。'}/>:row.kind==='new'?<><SceneFields value={row.scene} onChange={scene=>update(row.id,{scene})} project={project} disabled={busy}/><small className="creation-note">新场景结束后返回，不自动接回原后续。</small></>:null}<div className="choice-row-actions"><button type="button" disabled={index===0} onClick={()=>move(index,-1)}>上移</button><button type="button" disabled={index===rows.length-1} onClick={()=>move(index,1)}>下移</button><button type="button" disabled={rows.length===1} onClick={()=>setRows(v=>v.filter(r=>r.id!==row.id))}>删除</button></div></fieldset>)}
   <button type="button" disabled={busy} onClick={()=>setRows(v=>[...v,{id:crypto.randomUUID(),text:'',kind:'new',target:'',scene:freshScene(project,group)}])}>＋ 添加分支选项</button>
  </>}
  {cyclic&&<p className="flow-cycle-warning" role="status">此连接会形成循环路径，请确认这是预期的剧情走向。</p>}
  {!flow.authoring?.points[point.id]&&<p role="alert" className="creation-error">出口已变化，请关闭后重新选择。</p>}{error&&<p role="alert" className="creation-error">{error}</p>}
  <div className="creation-actions"><button type="button" disabled={busy} onClick={onClose}>取消</button><button type="submit" className="primary" disabled={busy||!valid}>{busy?'正在更新…':mode==='connect'?'连接':'应用'}</button></div>
 </form></Modal>;
}
