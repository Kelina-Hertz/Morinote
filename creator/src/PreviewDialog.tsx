import {useState} from 'react';
import type {Project} from './types';
import {Modal} from './ui';
import ScenePicker from './ScenePicker';
import {hasPreviewSettings,parsePreviewFields,type PreviewFields} from './creation-model';
import './creation-dialogs.css';

export default function PreviewDialog({project,label,onLabel,fields,onFields,onSave,onStart,onClose}:{project:Project;label:string;onLabel:(label:string)=>void;fields:PreviewFields;onFields:(fields:PreviewFields)=>void;onSave:()=>Promise<void>;onStart:(mode:'edit'|'play',scope:'fragment'|'continue')=>Promise<void>;onClose:()=>void}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const targetError=project.nativeRenpy?.labels.filter(l=>l.name===label).length===1?'':'请选择存在且标签唯一的起始场景。';
 let configError='';
 try{const parsed=parsePreviewFields(fields);if(parsed.initialize.some(name=>project.nativeRenpy?.labels.filter(l=>l.name===name).length!==1))configError='前置调用包含不存在或标签重复的场景，请打开高级设置修正。';}catch(e){configError=(e as Error).message;}
 async function perform(action:()=>Promise<void>,close:boolean){if(busy||targetError||configError)return;setBusy(true);setError('');setNotice('');try{await action();if(close)onClose();else setNotice('测试入口已保存。');}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 const invalid=!!targetError||!!configError;
 return <Modal title="片段测试" onClose={()=>{if(!busy)onClose();}}><div className="modal-body creation-form">
  <ScenePicker project={project} label="起始场景" value={label} onChange={onLabel} error={targetError} disabled={busy}/>
  {hasPreviewSettings(fields)&&<span className="preview-config-badge">已使用高级配置</span>}
  <details className="creation-advanced"><summary>高级设置</summary>
   {project.nativeRenpy?.labels.find(l=>l.name===label)?.parameters&&<small className="creation-note">场景参数声明：{project.nativeRenpy.labels.find(l=>l.name===label)?.parameters}</small>}
   <label>标签参数（JSON 数组）<input aria-label="标签参数 JSON" disabled={busy} value={fields.args} onChange={e=>onFields({...fields,args:e.target.value})}/></label>
   <label>测试状态（JSON 对象）<textarea aria-label="测试状态 JSON" rows={5} disabled={busy} value={fields.state} onChange={e=>onFields({...fields,state:e.target.value})}/></label>
   <label>前置标签调用（JSON 数组）<input aria-label="前置调用 JSON" disabled={busy} value={fields.initialize} onChange={e=>onFields({...fields,initialize:e.target.value})}/></label>
  </details>
  {configError&&<p role="alert" className="creation-error">{configError}</p>}{error&&<p role="alert" className="creation-error">{error}</p>}{notice&&<p role="status">{notice}</p>}
  <button disabled={busy||invalid} onClick={()=>void perform(onSave,false)}>保存测试入口</button>
  <p className="creation-note">从所选场景开头运行，启动前保存当前编辑稿。</p>
  <div className="creation-actions"><button disabled={busy||invalid} onClick={()=>void perform(()=>onStart('edit','fragment'),true)}>打开编辑预览</button><button className="primary" disabled={busy||invalid} onClick={()=>void perform(()=>onStart('play','fragment'),true)}>仅试玩此片段</button><button disabled={busy||invalid} onClick={()=>void perform(()=>onStart('play','continue'),true)}>从这里继续游戏</button></div>
 </div></Modal>;
}
