import {useCallback,useEffect,useRef,useState} from 'react';
import {Modal} from './ui';

type LeaveRequest={save:()=>Promise<void>;discard:()=>Promise<void>;resolve:(leave:boolean)=>void};

export function useUnsavedChanges(){
 const request=useRef<LeaveRequest|null>(null),task=useRef<Promise<boolean>|null>(null),working=useRef(false);
 const [open,setOpen]=useState(false),[busyAction,setBusyAction]=useState<'save'|'discard'|null>(null),[error,setError]=useState('');
 const busy=busyAction!==null;
 const finish=useCallback((leave:boolean)=>{
  const current=request.current;request.current=null;task.current=null;setOpen(false);setError('');current?.resolve(leave);
 },[]);
 useEffect(()=>()=>{request.current?.resolve(false);},[]);
 const confirm=useCallback((save:()=>Promise<void>,discard:()=>Promise<void>)=>{
  if(task.current)return task.current;
  task.current=new Promise<boolean>(resolve=>{request.current={save,discard,resolve};});
  setError('');setOpen(true);return task.current;
 },[]);
 async function choose(action:'save'|'discard'){
  if(!request.current||working.current)return;
  working.current=true;setBusyAction(action);setError('');
  try{await request.current[action]();finish(true);}
  catch(e){setError(e instanceof Error?e.message:String(e));}
  finally{working.current=false;setBusyAction(null);}
 }
 return {confirm,pending:open,dialog:open&&<Modal title="有未保存的修改" onClose={()=>{if(!working.current)finish(false);}}><div className="modal-body"><p>要保存修改吗？</p>{error&&<><p role="alert">{/外部修改|冲突|差异/.test(error)?'文件冲突，暂时无法保存。':'操作未完成，请重试。'}</p><details><summary>查看详情</summary><p>{error}</p></details></>}<div className="modal-actions"><button disabled={busy} onClick={()=>finish(false)}>取消</button><button disabled={busy} onClick={()=>void choose('discard')}>{busyAction==='discard'?'正在放弃…':'不保存'}</button><button className="primary" disabled={busy} onClick={()=>void choose('save')}>{busyAction==='save'?'正在保存…':'保存'}</button></div></div></Modal>};
}
