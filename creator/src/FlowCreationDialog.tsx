import {useEffect,useRef,useState} from 'react';
import type {Project} from './types';
import type {NativeFlowNode,NativeOperation} from './native-types';
import {Modal} from './ui';
import ScenePicker from './ScenePicker';
import {choiceErrors,newSceneLabel,parseChoiceJson,sceneFieldErrors,type ChoiceOption} from './creation-model';
import {api} from './api';
import './creation-dialogs.css';

type Props={kind:'scene'|'choice';project:Project;node?:NativeFlowNode;group:string;onOperation:NativeOperation;onClose:()=>void;onCreated:(name:string)=>void};
type Row=ChoiceOption&{id:string};
const row=(option:ChoiceOption={text:'',target:''}):Row=>({...option,id:crypto.randomUUID()});

export default function FlowCreationDialog({kind,project,node,group,onOperation,onClose,onCreated}:Props){
 const labels=project.nativeRenpy?.labels||[];
 const [title,setTitle]=useState(''),[name,setName]=useState(()=>newSceneLabel(labels)),[path,setPath]=useState('game/creator_scenes.rpy');
 const [rows,setRows]=useState<Row[]>(()=>[row(),row()]),[json,setJson]=useState<string|null>(null),[jsonError,setJsonError]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[touched,setTouched]=useState<Record<string,boolean>>({});
 const titleInput=useRef<HTMLInputElement>(null);
 useEffect(()=>{if(kind==='scene')titleInput.current?.focus();},[kind]);
 const fields=sceneFieldErrors(title,name,path,labels),errors=choiceErrors(rows,labels);
 const invalid=kind==='scene'?Object.values(fields).some(Boolean):!!jsonError||errors.some(e=>e.text||e.target)||!node;
 const options=rows.map(({text,target})=>({text,target}));
 function updateRows(next:Row[]){setRows(next);setJson(null);setJsonError('');}
 function editJson(value:string){setJson(value);try{setRows(parseChoiceJson(value).map(row));setJsonError('');}catch(e){setJsonError((e as Error).message);}}
 function move(index:number,offset:number){const next=[...rows];[next[index],next[index+offset]]=[next[index+offset],next[index]];updateRows(next);}
 async function submit(){
  if(invalid||busy)return;setBusy(true);setError('');
  try{
   if(kind==='scene'){
    const doc=await api.request<{hash:string}>('/api/workspace/document?path='+encodeURIComponent(path));
    await onOperation('flow',{operation:'scene',title:title.trim(),group,name,path,hash:doc.hash});
    onCreated(name);
   }else if(node)await onOperation('flow',{operation:'choice',node:node.id,hash:node.source.hash,options});
   onClose();
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <Modal title={kind==='scene'?'新增场景':'新增选项'} wide={kind==='choice'} onClose={()=>{if(!busy)onClose();}}><form className="modal-body creation-form" onSubmit={e=>{e.preventDefault();void submit();}}>
  {kind==='scene'?<>
   <label>场景名称<input ref={titleInput} aria-label="场景名称" maxLength={120} value={title} disabled={busy} onChange={e=>setTitle(e.target.value)} onBlur={()=>setTouched(v=>({...v,title:true}))} aria-invalid={!!fields.title&&!!touched.title}/></label>
   {touched.title&&fields.title&&<small className="creation-error">{fields.title}</small>}
   <p className="creation-note">创建到“{group}”。新场景独立创建，不改变现有剧情连接。</p>
   <details className="creation-advanced"><summary>高级设置</summary><label>标签名称<input aria-label="标签名称" value={name} disabled={busy} onChange={e=>setName(e.target.value)}/></label>{fields.name&&<small className="creation-error">{fields.name}</small>}<label>源码文件<input aria-label="源码文件" value={path} disabled={busy} onChange={e=>setPath(e.target.value)}/></label>{fields.path&&<small className="creation-error">{fields.path}</small>}</details>
  </>:<>
   <p className="creation-note">{node?.type==='scene'?'在所选场景的开头插入选项。':'在所选流程节点之前插入选项。'}选项选择后跳转到对应场景。</p>
   {rows.map((option,index)=><fieldset className="choice-row" key={option.id} disabled={busy||!!jsonError}><legend>选项 {index+1}</legend><label>选项文字<input aria-label={`选项 ${index+1} 文字`} value={option.text} aria-invalid={!!errors[index].text} onChange={e=>updateRows(rows.map((r,i)=>i===index?{...r,text:e.target.value}:r))}/></label>{errors[index].text&&<small className="creation-error">{errors[index].text}</small>}<ScenePicker project={project} label={`选项 ${index+1} 目标场景`} value={option.target} onChange={target=>updateRows(rows.map((r,i)=>i===index?{...r,target}:r))} error={errors[index].target}/><div className="choice-row-actions"><button type="button" aria-label={`上移选项 ${index+1}`} disabled={index===0} onClick={()=>move(index,-1)}>上移</button><button type="button" aria-label={`下移选项 ${index+1}`} disabled={index===rows.length-1} onClick={()=>move(index,1)}>下移</button><button type="button" aria-label={`删除选项 ${index+1}`} disabled={rows.length===1} onClick={()=>updateRows(rows.filter((_,i)=>i!==index))}>删除</button></div></fieldset>)}
   <button type="button" disabled={busy||!!jsonError} onClick={()=>updateRows([...rows,row()])}>＋ 添加选项</button>
   <details className="creation-advanced"><summary>高级设置</summary><label>选项列表（JSON）<textarea aria-label="选项列表 JSON" rows={8} disabled={busy} value={json??JSON.stringify(options,null,2)} onChange={e=>editJson(e.target.value)}/></label></details>
   {jsonError&&<div className="creation-error" role="alert">{jsonError}<button type="button" disabled={busy} onClick={()=>{setJson(null);setJsonError('');}}>放弃无效 JSON，恢复表单</button></div>}
  </>}
  {error&&<p role="alert" className="creation-error">{error}</p>}
  <div className="creation-actions"><button type="button" disabled={busy} onClick={onClose}>取消</button><button type="submit" className="primary" disabled={busy||invalid}>{busy?'正在添加…':'添加到编辑稿'}</button></div>
 </form></Modal>;
}
