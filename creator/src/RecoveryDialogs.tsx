import {useEffect,useRef,useState} from 'react';
import {Modal} from './ui';
import type {SourceBuffer} from './native-buffers';
import type {SourceDocument} from './native-types';
import type {RecoveryConflict,RecoveryFiles,RecoveryHistoryItem,RecoveryResult,RecoveryState} from './recovery-types';
import './recovery.css';

const reasonNames:Record<string,string>={auto:'自动备份',save:'保存源码前',restore:'恢复版本前',close:'关闭前',discard:'放弃修改前'};
function message(error:unknown){return error instanceof Error?error.message:String(error);}
function timeLabel(value:string){const date=new Date(value);return Number.isNaN(date.getTime())?value:date.toLocaleString('zh-CN',{hour12:false});}
function formatLabel(document?:SourceDocument){return document?`${document.bom?'UTF-8 BOM':'UTF-8'} · ${document.newline==='\r\n'?'CRLF':document.newline==='\r'?'CR':document.newline==='\n'?'LF':document.newline||'LF'}`:'';}

// Mark the changed range without an unbounded quadratic diff on large scripts.
function changedRange(before:string,after:string){
 const left=before.split('\n'),right=after.split('\n');let start=0,end=0;
 while(start<left.length&&start<right.length&&left[start]===right[start])start++;
 while(end<left.length-start&&end<right.length-start&&left[left.length-1-end]===right[right.length-1-end])end++;
 return {before:[start,left.length-end] as const,after:[start,right.length-end] as const};
}
function TextVersion({title,text,range,metadata,empty}:{title:string;text:string;range?:readonly [number,number];metadata?:string;empty?:string}){
 const lines=text.split('\n'),start=range?.[0]??lines.length,end=range?.[1]??lines.length;
 const part=(from:number,to:number)=>lines.slice(from,to).map((line,index)=>line+(from+index<lines.length-1?'\n':'')).join('');
 return <section className="recovery-version" aria-label={title}>
  <h3>{title}{metadata&&<small>{metadata}</small>}</h3>
  {empty?<div className="recovery-empty-file">{empty}</div>:<pre tabIndex={0} aria-label={title+'内容'}><span>{part(0,start)}</span><mark>{part(start,end)}</mark><span>{part(end,lines.length)}</span></pre>}
 </section>;
}

export interface RecoveryHistoryProps {
 onClose:()=>void;
 loadHistory:()=>Promise<{items:RecoveryHistoryItem[]}>;
 loadSnapshot:(id:string)=>Promise<RecoveryResult>;
 readFiles:(paths:string[])=>Promise<RecoveryFiles>;
 buffers:Record<string,SourceBuffer>;
 onRestore:(state:RecoveryState,paths:string[])=>Promise<void>;
}

export function RecoveryHistory({onClose,loadHistory,loadSnapshot,readFiles,buffers,onRestore}:RecoveryHistoryProps){
 const [items,setItems]=useState<RecoveryHistoryItem[]>([]),[selectedId,setSelectedId]=useState('');
 const [snapshot,setSnapshot]=useState<RecoveryState|null>(null),[selectedPath,setSelectedPath]=useState('');
 const [disk,setDisk]=useState<RecoveryFiles>({documents:[],errors:[]});
 const [loading,setLoading]=useState(true),[loadingSnapshot,setLoadingSnapshot]=useState(false),[restoring,setRestoring]=useState(false);
 const [error,setError]=useState(''),[warning,setWarning]=useState('');
 const callbacks=useRef({loadHistory,loadSnapshot,readFiles,onRestore,onClose});callbacks.current={loadHistory,loadSnapshot,readFiles,onRestore,onClose};
 const alive=useRef(true),listRequest=useRef(0),snapshotRequest=useRef(0),restorePending=useRef(false);
 useEffect(()=>{alive.current=true;void refresh();return()=>{alive.current=false;listRequest.current++;snapshotRequest.current++;};},[]);

 async function selectSnapshot(id:string){
  if(restorePending.current)return;
  const request=++snapshotRequest.current;
  setSelectedId(id);setSnapshot(null);setSelectedPath('');setDisk({documents:[],errors:[]});setLoadingSnapshot(true);setWarning('');setError('');
  try{
   const result=await callbacks.current.loadSnapshot(id);
   if(!alive.current||request!==snapshotRequest.current)return;
   if(!result.state)throw new Error('此快照没有可恢复的文档。');
   const state=result.state,paths=state.documents.map(document=>document.base.path);
   const files=await callbacks.current.readFiles(paths).catch(caught=>({documents:[],errors:paths.map(path=>({path,message:message(caught)}))}));
   if(!alive.current||request!==snapshotRequest.current)return;
   setSnapshot(state);setSelectedPath(paths[0]||'');setDisk(files);setWarning(result.warning||'');
  }catch(caught){if(alive.current&&request===snapshotRequest.current)setError(message(caught));}
  finally{if(alive.current&&request===snapshotRequest.current)setLoadingSnapshot(false);}
 }
 async function refresh(){
  if(restorePending.current)return;
  const request=++listRequest.current;++snapshotRequest.current;setLoading(true);setLoadingSnapshot(false);setSnapshot(null);setError('');
  try{
   const result=await callbacks.current.loadHistory();
   if(!alive.current||request!==listRequest.current)return;
   setItems(result.items);
   if(result.items.length)void selectSnapshot(result.items[0].id);else{setSelectedId('');setSelectedPath('');}
  }catch(caught){if(alive.current&&request===listRequest.current)setError(message(caught));}
  finally{if(alive.current&&request===listRequest.current)setLoading(false);}
 }
 async function restore(paths:string[]){
  if(!snapshot||!paths.length||restorePending.current||loadingSnapshot)return;
  restorePending.current=true;setRestoring(true);setError('');
  try{await callbacks.current.onRestore(snapshot,paths);if(alive.current)callbacks.current.onClose();}
  catch(caught){if(alive.current)setError(message(caught));}
  finally{restorePending.current=false;if(alive.current)setRestoring(false);}
 }
 const saved=snapshot?.documents.find(document=>document.base.path===selectedPath);
 const currentBuffer=buffers[selectedPath],currentDisk=disk.documents.find(document=>document.path===selectedPath);
 const currentText=currentBuffer?.value??currentDisk?.content??'';
 const readError=disk.errors.find(item=>item.path===selectedPath)?.message||(!currentBuffer&&!currentDisk&&saved?'未取得当前文件内容':undefined);
 const currentMissing=!currentBuffer&&currentDisk?.exists===false;
 const range=saved?changedRange(currentText,saved.value):null;
 const equal=!!saved&&(!!currentBuffer||!readError)&&!currentMissing&&currentText===saved.value;
 const close=()=>{if(!restorePending.current)onClose();};
 return <Modal title="恢复历史" onClose={close} wide>
  <div className="recovery-intro"><span>恢复到编辑器后，可继续修改或保存源码。</span><button className="secondary small" disabled={loading||restoring} onClick={()=>void refresh()}>刷新</button></div>
  {error&&<p className="recovery-message error" role="alert">{error}</p>}
  {warning&&<p className="recovery-message" role="status">{warning}</p>}
  <div className="recovery-history-layout" aria-busy={loading||loadingSnapshot||restoring}>
   <nav className="recovery-history-list" aria-label="历史快照">
    {loading?<p className="recovery-placeholder" role="status">读取历史…</p>:items.length?items.map(item=><button key={item.id} type="button" className={selectedId===item.id?'active':''} aria-pressed={selectedId===item.id} disabled={restoring} onClick={()=>void selectSnapshot(item.id)}><time dateTime={item.time}>{timeLabel(item.time)}</time><span>{reasonNames[item.reason]||item.reason} · {item.paths.length} 个文件</span><small title={item.paths.join('\n')}>{item.paths.join('、')||'编辑布局'}</small></button>):<p className="recovery-placeholder">暂无历史快照</p>}
   </nav>
   <div className="recovery-history-detail">
    {loadingSnapshot?<p className="recovery-placeholder" role="status">读取快照与当前文件…</p>:snapshot?<>
     <label className="recovery-file-picker"><span>文件</span><select value={selectedPath} disabled={restoring} onChange={event=>setSelectedPath(event.target.value)}>{snapshot.documents.map(document=><option key={document.base.path} value={document.base.path}>{document.base.path}</option>)}</select></label>
     {saved?<><p className="recovery-comparison-caption">{equal?'与当前内容相同':'变更范围已标记'}</p><div className="recovery-versions"><TextVersion title={currentBuffer?'当前编辑内容':'磁盘内容'} text={currentText} range={range?.before} metadata={formatLabel(currentBuffer?.base||currentDisk)} empty={!currentBuffer&&readError?`读取失败：${readError}`:currentMissing?'文件当前不存在':undefined}/><TextVersion title="历史草稿" text={saved.value} range={range?.after} metadata={formatLabel(saved.base)}/></div></>:<p className="recovery-placeholder">此快照没有文档内容。</p>}
    </>:<p className="recovery-placeholder">选择一个快照查看内容。</p>}
   </div>
  </div>
  <div className="modal-actions recovery-actions"><span role="status">{restoring?'正在备份当前草稿并恢复…':''}</span><button className="secondary" disabled={restoring} onClick={close}>关闭</button><button className="secondary" disabled={!saved||loadingSnapshot||restoring} onClick={()=>void restore([selectedPath])}>恢复此文件</button><button className="primary" disabled={!snapshot?.documents.length||loadingSnapshot||restoring} onClick={()=>void restore(snapshot!.documents.map(document=>document.base.path))}>恢复整个快照</button></div>
 </Modal>;
}

export interface RecoveryConflictsProps {
 onMerge?:(conflict:RecoveryConflict)=>void;
 conflicts:RecoveryConflict[];
 onClose:()=>void;
 onResolve:(conflict:RecoveryConflict,choice:'disk'|'draft'|'relocate',target?:string)=>Promise<void>;
}

function relativePathError(value:string){
 const path=value.trim().replace(/\\/g,'/');
 if(!path)return '请输入项目内的文件路径。';
 if(path.startsWith('/')||/^[A-Za-z]:/.test(path)||path.split('/').some(part=>!part||part==='.'||part==='..')||/[\u0000-\u001f<>:"|?*]/.test(path))return '请使用项目内的相对路径，例如 game/recovered_scene.rpy。';
 return '';
}

export function RecoveryConflicts({conflicts,onClose,onResolve,onMerge}:RecoveryConflictsProps){
 const [selectedPath,setSelectedPath]=useState(conflicts[0]?.path||''),[target,setTarget]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const alive=useRef(true),pending=useRef(false),callbacks=useRef({onResolve,onClose});callbacks.current={onResolve,onClose};
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const conflict=conflicts.find(item=>item.path===selectedPath)||conflicts[0];
 useEffect(()=>{setSelectedPath(conflict?.path||'');setTarget(conflict?.path||'');setError('');},[conflict?.path]);
 async function resolve(choice:'disk'|'draft'|'relocate'){
  if(!conflict||pending.current)return;
  const path=target.trim().replace(/\\/g,'/');
  if(choice==='relocate'){
   const invalid=relativePathError(path);
   if(invalid){setError(invalid);return;}
   if(conflict.error&&path.toLocaleLowerCase()===conflict.path.toLocaleLowerCase()){setError('原路径无法读取，请选择一个新的文件路径。');return;}
  }
  pending.current=true;setBusy(true);setError('');
  try{await callbacks.current.onResolve(conflict,choice,choice==='relocate'?path:undefined);}
  catch(caught){if(alive.current)setError(message(caught));}
  finally{pending.current=false;if(alive.current)setBusy(false);}
 }
 const close=()=>{if(!pending.current)onClose();};
 const missing=conflict?.disk?.exists===false,canUseDraft=!!conflict?.disk&&!missing&&!conflict.error;
 const draftRange=conflict?changedRange(conflict.draft.base.content,conflict.draft.value):null;
 const diskRange=conflict?changedRange(conflict.draft.base.content,conflict.disk?.content??''):null;
 return <Modal title="恢复草稿 · 处理文件变化" onClose={close} wide>
  <div className="recovery-intro"><span>原文件保留当前状态。选择要恢复到编辑器的内容。</span><span>{conflicts.length} 项待处理</span></div>
  {error&&<p className="recovery-message error" role="alert">{error}</p>}
  {conflict?<div className="recovery-conflict-body" aria-busy={busy}>
   <nav className="recovery-conflict-list" aria-label="待处理文件">{conflicts.map(item=><button key={item.path} className={item.path===conflict.path?'active':''} aria-pressed={item.path===conflict.path} disabled={busy} onClick={()=>setSelectedPath(item.path)}>{item.path}<small>{item.error?'读取失败':item.disk?.exists===false?'文件已删除或移动':'文件已变化'}</small></button>)}</nav>
   {conflict.error?<p className="recovery-message error" role="alert">无法读取当前文件：{conflict.error}。可以稍后处理，或恢复到一个新路径。</p>:missing?<p className="recovery-message">原文件已删除或移动。选择恢复位置后，草稿将作为新文件标签打开。</p>:null}
   <div className="recovery-versions recovery-three-versions">
    <TextVersion title="开始编辑时" text={conflict.draft.base.content} metadata={formatLabel(conflict.draft.base)} empty={conflict.draft.base.exists===false?'当时尚未创建文件':undefined}/>
    <TextVersion title="当前磁盘" text={conflict.disk?.content??''} range={diskRange?.after} metadata={formatLabel(conflict.disk)} empty={conflict.error?'无法读取当前内容':missing?'文件不存在':undefined}/>
    <TextVersion title="恢复草稿" text={conflict.draft.value} range={draftRange?.after} metadata={formatLabel(conflict.draft.base)}/>
   </div>
   <div className="recovery-relocate"><label htmlFor="recovery-target-path">恢复位置</label><input id="recovery-target-path" value={target} disabled={busy} spellCheck={false} placeholder="game/recovered_scene.rpy" onChange={event=>setTarget(event.target.value)} onKeyDown={event=>{if(event.key==='Enter')void resolve('relocate');}}/><button className="secondary" disabled={busy||!target.trim()} onClick={()=>void resolve('relocate')}>恢复到此路径</button></div>
  </div>:<p className="recovery-placeholder" role="status">所有文件已处理。</p>}
  <div className="modal-actions recovery-actions"><span role="status">{busy?'正在处理…':''}</span><button className="secondary" disabled={busy} onClick={close}>{conflicts.length?'稍后处理':'关闭'}</button>{conflict&&<>{onMerge&&conflict.disk?.exists&&!conflict.error&&<button className="secondary" disabled={busy} onClick={()=>onMerge(conflict)}>分块合并</button>}<button className="secondary" disabled={busy||!!conflict.error} onClick={()=>void resolve('disk')}>{missing?'保留删除状态':'保留磁盘版本'}</button><button className="primary" disabled={busy||!canUseDraft} onClick={()=>void resolve('draft')}>使用草稿继续编辑</button></>}</div>
 </Modal>;
}
