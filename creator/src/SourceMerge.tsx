import {useEffect,useRef,useState} from 'react';
import type {SourceDocument} from './native-types';
import {api} from './api';
import {Modal} from './ui';
import './source-merge.css';

type Part={text:string;conflict:boolean;base?:string;local?:string;disk?:string;line?:number};
export default function SourceMerge({base,local,disk,onApply,onClose}:{base:SourceDocument;local:string;disk:SourceDocument;onApply:(text:string,disk:SourceDocument)=>Promise<void>;onClose:()=>void}){
 const [parts,setParts]=useState<Part[]|null>(null),[choices,setChoices]=useState<Record<number,string>>({}),[result,setResult]=useState<string|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[restoreMissing,setRestoreMissing]=useState(false);
 const request=useRef(0);
 useEffect(()=>{const serial=++request.current;setParts(null);setError('');setChoices({});setResult(null);
  void api.request<{parts:Part[]}>('/api/workspace/merge',{path:base.path,base:base.content,local,diskHash:disk.hash,diskExists:disk.exists}).then(r=>{if(serial===request.current)setParts(r.parts);}).catch(e=>{if(serial===request.current)setError(e.message);});
  return()=>{request.current++;};
 },[base,local,disk]);
 const conflicts=parts?.map((p,i)=>p.conflict?i:-1).filter(i=>i>=0)||[],remaining=conflicts.filter(i=>choices[i]===undefined).length;
 const assembled=parts?.map((p,i)=>p.conflict?(choices[i]??p.text):p.text).join('')||'';
 async function apply(){setBusy(true);setError('');try{await onApply(result??assembled,disk);onClose();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 return <Modal title={'合并源码 · '+base.path} wide onClose={()=>{if(!busy)onClose();}}><div className="source-merge">
  <div className="merge-status">{parts?conflicts.length?`${remaining} 处冲突待处理`:'无冲突，已合并双方修改':'正在比较…'}</div>
  {error&&<p role="alert">{error}</p>}{!disk.exists&&<label><input type="checkbox" checked={restoreMissing} onChange={e=>setRestoreMissing(e.target.checked)}/>原文件已删除，以新文件恢复到编辑器</label>}
  {result===null?conflicts.map((i,n)=><section className="merge-hunk" key={i}><header>冲突 {n+1} · 原第 {parts![i].line} 行</header><div className="merge-versions">{(['base','local','disk'] as const).map((key,j)=><div key={key}><strong>{['共同基础','编辑稿','磁盘'][j]}</strong><pre>{parts![i][key]||'（空）'}</pre></div>)}</div><div className="actions"><button onClick={()=>setChoices(v=>({...v,[i]:parts![i].local||''}))}>采用编辑稿</button><button onClick={()=>setChoices(v=>({...v,[i]:parts![i].disk||''}))}>采用磁盘</button><button onClick={()=>setChoices(v=>({...v,[i]:(parts![i].local||'')+(parts![i].disk||'')}))}>保留两者</button></div><textarea aria-label={'冲突 '+(n+1)+' 的合并内容'} placeholder="选择版本，或直接编辑本块" value={choices[i]??''} onChange={e=>setChoices(v=>({...v,[i]:e.target.value}))}/>{choices[i]!==undefined&&<small>已处理</small>}</section>):null}
  {parts&&<><button disabled={remaining>0||busy} onClick={()=>setResult(result===null?assembled:null)}>{result===null?'查看并编辑完整结果':'返回冲突块'}</button>{result!==null&&<textarea className="merge-result" aria-label="完整合并结果" value={result} onChange={e=>setResult(e.target.value)}/>}</>}
  <div className="modal-actions"><button disabled={busy} onClick={onClose}>取消</button><button className="primary" disabled={!parts||remaining>0||busy||(!disk.exists&&!restoreMissing)} onClick={()=>void apply()}>应用到编辑器</button></div>
 </div></Modal>;
}
