import {useCallback,useEffect,useRef,useState} from 'react';
import {api,currentProjectSession} from './api';
import type {RecoveryReason,RecoveryReceipt,RecoveryResult,RecoveryState} from './recovery-types';

// This channel intentionally bypasses the Python request/compilation queue.
export function useNativeRecovery(state:RecoveryState,getState:()=>RecoveryState,onRestore:(state:RecoveryState,isCurrent:()=>boolean)=>Promise<void>){
 const session=useRef(currentProjectSession()).current,available=!!api.recovery;
 const latest=useRef({getState,onRestore});latest.current={getState,onRestore};
 const mounted=useRef(false),initialized=useRef(false),sequence=useRef(0),writes=useRef(Promise.resolve()),firstPending=useRef(0),acknowledged=useRef('');
 const [ready,setReady]=useState(!available),[savedAt,setSavedAt]=useState(''),[failure,setFailure]=useState(''),[warning,setWarning]=useState(''),[pending,setPending]=useState(false),[attempt,setAttempt]=useState(0),[checkpointAt,setCheckpointAt]=useState(0);
 const call=useCallback(async<T,>(method:string,payload:Record<string,unknown>={}):Promise<T>=>{
  if(!api.recovery)throw new Error('草稿恢复需要桌面版 IDE。');
  if(currentProjectSession()!==session)throw new Error('项目已切换，已停止旧项目的恢复操作。');
  const result=await api.recovery<T>(method,{...payload,projectSession:session});
  if(currentProjectSession()!==session)throw new Error('项目已切换，忽略旧项目的恢复响应。');
  return result;
 },[session]);
 useEffect(()=>{mounted.current=true;let alive=true;
  if(available){initialized.current=false;setReady(false);void call<RecoveryResult>('current').then(async result=>{
   if(!alive)return;sequence.current=result.sequence;
   if(result.state)await latest.current.onRestore(result.state,()=>alive&&currentProjectSession()===session);
   if(!alive)return;
   // Reconciliation can change base versions. Back up the reconciled state again.
   acknowledged.current=result.state?JSON.stringify(result.state):'';
   setSavedAt(result.savedAt||'');setWarning(result.warning||'');setFailure('');initialized.current=true;setReady(true);
  }).catch(e=>{if(alive)setFailure('读取恢复草稿失败：'+String(e.message||e));});}
  return()=>{alive=false;mounted.current=false;initialized.current=false;};
 },[available,call,attempt]);
 const flush=useCallback((reason:RecoveryReason='auto',discard=false):Promise<void>=>{
  if(!available)return Promise.resolve();
  if(!initialized.current)return Promise.reject(new Error('恢复草稿尚未载入，请先完成恢复或重试。'));
  const snapshot=latest.current.getState(),fingerprint=JSON.stringify(snapshot),serial=++sequence.current;
  firstPending.current=0;
  const task=writes.current.then(async()=>{
   const receipt=await call<RecoveryReceipt>(discard?'discard':'write',{state:snapshot,sequence:serial,reason});
   if(mounted.current){acknowledged.current=fingerprint;setSavedAt(receipt.savedAt);setCheckpointAt(receipt.nextSnapshotAt?Date.parse(receipt.nextSnapshotAt):0);setFailure('');if(receipt.warning)setWarning(receipt.warning);setPending(JSON.stringify(latest.current.getState())!==fingerprint);}
  });
  writes.current=task.catch(e=>{if(mounted.current){setFailure('草稿备份失败：'+String(e.message||e));setPending(true);}});
  return task;
 },[available,call]);
 useEffect(()=>{
  if(!available||!ready)return;
  if(JSON.stringify(state)===acknowledged.current){setPending(false);return;}
  setPending(true);if(!firstPending.current)firstPending.current=Date.now();
  const delay=Math.max(0,Math.min(1000,5000-(Date.now()-firstPending.current)));
  const timer=setTimeout(()=>{void flush().catch(()=>{});},delay);
  return()=>clearTimeout(timer);
 },[state,ready,available,flush]);
 useEffect(()=>{if(!ready||!available)return;const timer=setInterval(()=>{void flush().catch(()=>{});},60000);return()=>clearInterval(timer);},[ready,available,flush]);
 useEffect(()=>{if(!ready||!checkpointAt)return;const timer=setTimeout(()=>{void flush().catch(()=>{});},Math.max(0,checkpointAt-Date.now()));return()=>clearTimeout(timer);},[ready,checkpointAt,flush]);
 const retry=useCallback(()=>{if(initialized.current)void flush().catch(()=>{});else setAttempt(v=>v+1);},[flush]);
 return {available,ready,pending,savedAt,failure,warning,call,flush,retry,discard:()=>flush('discard',true)};
}
