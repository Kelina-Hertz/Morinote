import {lazy,Suspense,useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {BookOpen,FolderOpen,Save,Undo2,Redo2,Play,Code2,GitBranch,Image,ChevronDown,ChevronRight,File,Plus,RefreshCw,Square,X,Move,ExternalLink} from 'lucide-react';
import type {Asset,Diagnostic,PreviewStatus,Project,ProjectResponse} from './types';
import type {ConfigField,SourceDocument,SourceLocation,TreeNode,WorkspaceIndex,NativeOperation} from './native-types';
import {api,currentProjectSession} from './api';
import {version} from '../package.json';
import {effective} from './model';
import {audioVolumeChanges,defaultChannels,type NativeAudioState} from './native-audio';
import {reconcileSavedBuffers,type SourceBuffer} from './native-buffers';
import {useNativeRecovery} from './useNativeRecovery';
import {RecoveryHistory,RecoveryConflicts} from './RecoveryDialogs';
import type {RecoveryConflict,RecoveryFiles,RecoveryHistoryItem,RecoveryResult,RecoveryState} from './recovery-types';
import NativeAssets from './NativeAssets';
import {groupedFiles,fileGroupNames} from './file-groups';
import {sceneTitle,sceneOption} from './scene-titles';
import type {LibraryMetadata} from './NativeAssets';
import NativeConfig from './NativeConfig';
import NativeFlow from './NativeFlow';
import NativeTimeline from './NativeTimeline';
import {Media,AudioPlayer} from './Assets';
import {Modal} from './ui';
import DockPanel,{DockScope} from './DockPanel';
import SourceMerge from './SourceMerge';
const SourceEditor=lazy(()=>import('./SourceEditor'));
type Buffer=SourceBuffer;
type Tab={id:string;title:string;kind:'flow'|'code'|'scene'|'config'|'assets'|'media';target?:string;callContext?:{callerLabel:string;source:SourceLocation}};
type UndoFrame={buffers:Record<string,Buffer>;view:Omit<RecoveryState,'documents'>;conflicts:RecoveryConflict[];localOnly?:boolean};
const firstTab:Tab={id:'flow',title:'剧情总图',kind:'flow'};

function Tree({items,onOpen,onRename,onClassify}:{items:TreeNode[];onClassify?:(node:TreeNode)=>void;onOpen:(node:TreeNode)=>void;onRename:(node:TreeNode)=>void}){
 const [closed,setClosed]=useState<string[]>(items.filter(i=>i.children&&i.path!=='game').map(i=>i.path));
 return <>{items.map(item=><div key={item.path}><div className="file-tree-row"><button title={item.path} onClick={()=>{if(item.children)setClosed(v=>v.includes(item.path)?v.filter(p=>p!==item.path):[...v,item.path]);else onOpen(item);}}>{item.children?closed.includes(item.path)?<ChevronRight size={11}/>:<ChevronDown size={11}/>:<File size={12}/>}<span>{item.name}</span></button>{item.text&&<button className="rename-file" aria-label={'重命名 '+item.name} onClick={()=>onRename(item)}>…</button>}{item.text&&onClassify&&<button className="file-purpose-button" title="设置文件用途" onClick={()=>onClassify(item)}>分类</button>}</div>{item.children&&!closed.includes(item.path)&&<div className="file-tree-children"><Tree items={item.children} onOpen={onOpen} onRename={onRename} onClassify={onClassify}/></div>}</div>)}</>;
}

export default function NativeWorkbench({project,root,replace,onOpen,onNew}:{project:Project;root:string;replace:(value:ProjectResponse)=>void;onOpen:()=>void;onNew:()=>void}){
 const savedTest=(project.ide as {testEntry?:{label?:string;args?:string;state?:string;initialize?:string}})?.testEntry;
 const [assetGaps,setAssetGaps]=useState(false),[assetFocus,setAssetFocus]=useState('');
 const [launcherPrompt,setLauncherPrompt]=useState(false),[launcherNotice,setLauncherNotice]=useState('');
 const [systemsOpen,setSystemsOpen]=useState(false),[fileView,setFileView]=useState<'purpose'|'directory'>('purpose'),[classifying,setClassifying]=useState<TreeNode|null>(null);
 const [index,setIndex]=useState<WorkspaceIndex|null>(null),[projection,setProjection]=useState<Project>(project),[buffers,setBuffers]=useState<Record<string,Buffer>>({}),[tabs,setTabs]=useState<Tab[]>([firstTab]),[active,setActive]=useState('flow'),[lastCode,setLastCode]=useState(''),[location,setLocation]=useState<SourceLocation|null>(null),[status,setStatus]=useState(''),[error,setError]=useState(''),[logs,setLogs]=useState(''),[diagnostics,setDiagnostics]=useState<Diagnostic[]>([]),[preview,setPreview]=useState<PreviewStatus>({status:'stopped'}),[showLogs,setShowLogs]=useState(false),[assetField,setAssetField]=useState<ConfigField|null>(null),[media,setMedia]=useState<string>(''),[diff,setDiff]=useState<{path:string;base:SourceDocument;disk:SourceDocument;local:string}|null>(null),[test,setTest]=useState(false),[testLabel,setTestLabel]=useState(savedTest?.label||'start'),[testState,setTestState]=useState(savedTest?.state||'{}'),[testArgs,setTestArgs]=useState(savedTest?.args||'[]'),[testCalls,setTestCalls]=useState(savedTest?.initialize||'[]'),[follow,setFollow]=useState(true),[closing,setClosing]=useState<Tab|null>(null);
 const docs=useRef(buffers),projectRef=useRef(project),queue=useRef(Promise.resolve()),past=useRef<UndoFrame[]>([]),future=useRef<UndoFrame[]>([]),transactions=useRef<string[]>([]),undone=useRef<string[]>([]),analysisSerial=useRef(0),activeRef=useRef(active),lastEvent=useRef(0),followRef=useRef(follow),navigationSerial=useRef(0);
 const [recoveryHistory,setRecoveryHistory]=useState(false),[recoveryConflicts,setRecoveryConflicts]=useState<RecoveryConflict[]>([]),[showRecoveryConflicts,setShowRecoveryConflicts]=useState(false),[closingApp,setClosingApp]=useState(false);
 type SaveNotice={id:string;documents:Buffer[];paths:string[];conflicts:string[]};
 const [saveNotices,setSaveNotices]=useState<SaveNotice[]>([]),[mergingRecovery,setMergingRecovery]=useState('');

 const frozen=useRef(false),closeTask=useRef<Promise<void>|null>(null),viewRef=useRef({tabs,active,lastCode,location}),conflictRef=useRef(recoveryConflicts);
 viewRef.current={tabs,active,lastCode,location};conflictRef.current=recoveryConflicts;
 docs.current=buffers;projectRef.current=project;activeRef.current=active;
 const dirty=Object.values(buffers).some(d=>(!d.base.exists||d.value!==d.base.content)),tab=tabs.find(t=>t.id===active)||firstTab;
 const run=useCallback((fn:()=>Promise<unknown>,label='正在处理')=>{if(frozen.current)return Promise.reject(new Error('正在备份并关闭，请稍候。'));const next=queue.current.then(async()=>{setStatus(label);setError('');try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));throw e;}finally{setStatus('');}});queue.current=next.catch(()=>{});return next;},[]);
 const snapshot=()=>Object.values(docs.current).map(b=>({...b.base,content:b.value}));
 function captureFrame(localOnly=false):UndoFrame{return {buffers:{...docs.current},view:{...viewRef.current},conflicts:[...conflictRef.current],localOnly};}
 function updateBuffers(next:Record<string,Buffer>,record=true,localOnly=false){if(!localOnly&&JSON.stringify(next)===JSON.stringify(docs.current))return;if(record){past.current.push(captureFrame(localOnly));if(past.current.length>100)past.current.shift();future.current=[];}docs.current=next;setBuffers(next);}
 const recoveryState=useMemo<RecoveryState>(()=>({documents:Object.values(buffers),tabs,active,lastCode,location}),[buffers,tabs,active,lastCode,location]);
 const recovery=useNativeRecovery(recoveryState,()=>({documents:Object.values(docs.current),...viewRef.current}),restoreStartup);
 const recoveryRef=useRef(recovery);recoveryRef.current=recovery;
 const recoveryBlocked=recoveryConflicts.length>0;
 useEffect(()=>{if(!recovery.ready)return;let alive=true;void api.request<{items:SaveNotice[]}>('/api/workspace/save-recovery').then(r=>{if(alive)setSaveNotices(r.items);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[recovery.ready]);
 const readRecoveryFiles=useCallback((paths:string[])=>recoveryRef.current.call<RecoveryFiles>('readFiles',{paths}),[]);
 const loadRecoveryHistory=useCallback(()=>recoveryRef.current.call<{items:RecoveryHistoryItem[]}>('history'),[]);
 const loadRecoverySnapshot=useCallback((id:string)=>recoveryRef.current.call<RecoveryResult>('snapshot',{id}),[]);
 function applyRecoveryViews(state:RecoveryState,next:Record<string,Buffer>){
  const restoredTabs=state.tabs.filter(t=>t.id==='flow'||t.kind!=='code'||!!next[t.target||'']);
  if(!restoredTabs.some(t=>t.id==='flow'))restoredTabs.unshift(firstTab);
  const restoredActive=restoredTabs.some(t=>t.id===state.active)?state.active:'flow',restoredCode=next[state.lastCode]?state.lastCode:restoredTabs.find(t=>t.kind==='code')?.target||'';
  viewRef.current={tabs:restoredTabs,active:restoredActive,lastCode:restoredCode,location:state.location};activeRef.current=restoredActive;
  updateFollow(false);setTabs(restoredTabs);setActive(restoredActive);setLastCode(restoredCode);setLocation(state.location);
 }
 async function restoreStartup(state:RecoveryState,isCurrent:()=>boolean=()=>true){
  const files=await readRecoveryFiles(state.documents.map(b=>b.base.path));if(!isCurrent())return;
  const next:Record<string,Buffer>={},conflicts:RecoveryConflict[]=[];
  for(const draft of state.documents){
   const path=draft.base.path,disk=files.documents.find(d=>d.path===path),failure=files.errors.find(d=>d.path===path)?.message;
   if(!disk||failure){next[path]=draft;conflicts.push({path,draft,error:failure||'无法读取磁盘文件。'});continue;}
   if(!disk.exists&&draft.base.exists&&draft.value===draft.base.content)continue;
   if(disk.exists&&disk.content===draft.value){next[path]={base:disk,value:disk.content};continue;}
   if(disk.exists===draft.base.exists&&disk.hash===draft.base.hash){next[path]={...draft,base:disk};continue;}
   if(disk.exists&&draft.base.exists&&draft.value===draft.base.content){next[path]={base:disk,value:disk.content};continue;}
   next[path]=draft;conflicts.push({path,draft,disk});
  }
  updateBuffers(next,false);setRecoveryConflicts(conflicts);conflictRef.current=conflicts;setShowRecoveryConflicts(conflicts.length>0);applyRecoveryViews(state,next);
 }
 async function restoreHistory(state:RecoveryState,paths:string[]){
  await recovery.flush('restore');const files=await readRecoveryFiles(paths),next={...docs.current},conflicts=conflictRef.current.filter(c=>!paths.includes(c.path));
  for(const draft of state.documents.filter(b=>paths.includes(b.base.path))){
   const path=draft.base.path,disk=files.documents.find(d=>d.path===path),failure=files.errors.find(d=>d.path===path)?.message;
   if(!disk||failure||(!disk.exists&&draft.base.exists)){next[path]=draft;conflicts.push({path,draft,disk,error:failure});}
   else next[path]={...draft,base:disk};
  }
  updateBuffers(next,true,true);setRecoveryConflicts(conflicts);conflictRef.current=conflicts;setShowRecoveryConflicts(conflicts.length>0);
  if(paths.length===state.documents.length)applyRecoveryViews(state,next);
  else for(const path of paths)activate({id:'code:'+path,title:path.split('/').pop()!,kind:'code',target:path});
  if(paths.length===1){const path=paths[0],cursor={path,line:1,column:1};activate({id:'code:'+path,title:path.split('/').pop()!,kind:'code',target:path});viewRef.current={...viewRef.current,lastCode:path,location:cursor};setLastCode(path);setLocation(cursor);}
  await recovery.flush();
 }
 async function resolveRecovery(conflict:RecoveryConflict,choice:'disk'|'draft'|'relocate',target?:string){
  const current=docs.current[conflict.path];if(!current)throw new Error('该草稿已变化，请重新打开恢复列表。');
  await recovery.flush('restore');const path=choice==='relocate'?(target||'').replaceAll('\\','/'):conflict.path;
  if(!path)throw new Error('请填写项目内的新文件路径。');
  const files=await readRecoveryFiles([path]),disk=files.documents[0];if(!disk||files.errors.length)throw new Error(files.errors[0]?.message||'无法读取目标位置。');
  if(choice!=='relocate'&&conflict.disk&&(disk.hash!==conflict.disk.hash||disk.exists!==conflict.disk.exists)){
   setRecoveryConflicts(v=>v.map(c=>c.path===path?{...c,disk,error:undefined}:c));throw new Error('磁盘内容又发生了变化，已更新比较内容，请重新选择。');
  }
  if(choice==='relocate'&&(disk.exists||(path!==conflict.path&&docs.current[path])))throw new Error('目标位置已有文件或编辑稿，请使用新的路径。');
  if(choice==='draft'&&!disk.exists)throw new Error('原文件已不存在，请选择新的恢复位置。');
  const next={...docs.current};delete next[conflict.path];
  if(choice!=='disk'||disk.exists)next[path]={...current,base:disk,value:choice==='disk'?disk.content:current.value};
  updateBuffers(next,true,true);const remaining=conflictRef.current.filter(c=>c.path!==conflict.path);conflictRef.current=remaining;setRecoveryConflicts(remaining);
  if(choice==='relocate'){closeTab({id:'code:'+conflict.path,title:conflict.path,kind:'code',target:conflict.path});activate({id:'code:'+path,title:path.split('/').pop()!,kind:'code',target:path});viewRef.current={...viewRef.current,lastCode:path,location:{path,line:1,column:1}};setLastCode(path);setLocation({path,line:1,column:1});}
  else if(!disk.exists)closeTab({id:'code:'+path,title:path,kind:'code',target:path});
  if(choice==='disk')await recovery.discard();else await recovery.flush();
 }
 async function discardFile(t:Tab){
  await recovery.flush('discard');const next={...docs.current};delete next[t.target!];updateBuffers(next,true,true);
  const remaining=conflictRef.current.filter(c=>c.path!==t.target);conflictRef.current=remaining;setRecoveryConflicts(remaining);closeTab(t);await recovery.discard();
 }
 useEffect(()=>{
  if(!api.onPrepareClose)return;
  const stop=api.onPrepareClose(()=>{
   if(closeTask.current)return closeTask.current;
   frozen.current=true;setClosingApp(true);
   const task=(async()=>{await queue.current;await recoveryRef.current.flush('close');})();closeTask.current=task;
   void task.finally(()=>{if(closeTask.current===task)closeTask.current=null;}).catch(()=>{});return task;
  });
  const cancelled=api.onCloseCancelled?.(()=>{frozen.current=false;closeTask.current=null;setClosingApp(false);});
  return()=>{stop();cancelled?.();};
 },[]);
 async function restoreSaveDrafts(){
  await recovery.flush('restore');const pending=saveNotices.flatMap(i=>i.documents),files=await readRecoveryFiles(pending.map(d=>d.base.path));
  const next={...docs.current},conflicts=[...conflictRef.current];let skipped=0;
  for(const draft of pending){const path=draft.base.path,current=next[path],disk=files.documents.find(d=>d.path===path);
   if(current&&(!current.base.exists||current.value!==current.base.content)){skipped++;continue;}
   if(!disk)throw new Error('无法读取恢复位置：'+path);
   if(disk.exists&&disk.content===draft.value){next[path]={base:disk,value:disk.content};continue;}
   if(disk.exists===draft.base.exists&&disk.hash===draft.base.hash)next[path]={base:disk,value:draft.value};
   else {next[path]=draft;conflicts.push({path,draft,disk});}
  }
  updateBuffers(next,true,true);conflictRef.current=conflicts;setRecoveryConflicts(conflicts);setShowRecoveryConflicts(conflicts.length>0);
  for(const draft of pending)activate({id:'code:'+draft.base.path,title:draft.base.path.split('/').pop()!,kind:'code',target:draft.base.path});
  await recovery.flush();await api.request('/api/workspace/save-recovery-ack',{ids:saveNotices.map(i=>i.id)});setSaveNotices([]);
  if(skipped)setError('已保留 '+skipped+' 份较新的编辑稿，未被中断保存稿覆盖。');
 }
 async function refresh(){const response=await api.request<ProjectResponse>('/api/project');if(response.project){replace(response);projectRef.current=response.project;}const data=await api.request<WorkspaceIndex>('/api/workspace');setIndex(data);if(!Object.values(docs.current).some(d=>(!d.base.exists||d.value!==d.base.content)))setProjection(response.project||projectRef.current);}
 useEffect(()=>{if(!recovery.ready||recoveryBlocked)return;let alive=true;void api.request<WorkspaceIndex>('/api/workspace').then(async data=>{if(!alive)return;if(Object.values(docs.current).some(d=>!d.base.exists||d.value!==d.base.content)){const analyzed=await api.request<WorkspaceIndex&{project:Project}>('/api/workspace/analyze',{documents:snapshot()});if(alive){setIndex({...analyzed,tree:data.tree});setProjection(analyzed.project);}}else setIndex(data);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[project.revision,recovery.ready,recoveryBlocked]);
 useEffect(()=>{if(!Object.values(docs.current).some(d=>!d.base.exists||d.value!==d.base.content))setProjection(project);},[project]);
 useEffect(()=>{const serial=++analysisSerial.current;if(!dirty||!recovery.ready||recoveryBlocked)return;const timer=setTimeout(()=>{void api.request<WorkspaceIndex&{project:Project}>('/api/workspace/analyze',{documents:snapshot()}).then(data=>{if(serial!==analysisSerial.current)return;setIndex(previous=>({...data,tree:previous?.tree||[]}));setProjection(data.project);}).catch(e=>{if(serial===analysisSerial.current)setError('编辑稿索引：'+e.message);});},400);return()=>clearTimeout(timer);},[buffers,dirty,recovery.ready,recoveryBlocked]);
 function updateFollow(value:boolean){followRef.current=value;navigationSerial.current++;setFollow(value);}
 function activate(next:Tab,fromRuntime=false){if(!fromRuntime)updateFollow(false);const nextTabs=viewRef.current.tabs.some(t=>t.id===next.id)?viewRef.current.tabs:[...viewRef.current.tabs,next];viewRef.current={...viewRef.current,tabs:nextTabs,active:next.id,...(next.kind==='code'?{lastCode:next.target!}:{})};setTabs(nextTabs);activeRef.current=next.id;setActive(next.id);}
 function openAssetGaps(){setAssetGaps(true);activate({id:'assets',title:'项目素材库',kind:'assets'});}
 async function openSource(source:SourceLocation,fromRuntime=false){
  if(!fromRuntime)updateFollow(false);const navigation=navigationSerial.current;
  if(!docs.current[source.path]){const document=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(source.path));updateBuffers({...docs.current,[source.path]:{base:document,value:document.content}},false);}
  if(navigation!==navigationSerial.current||(fromRuntime&&!followRef.current))return;
  setLocation(source);setLastCode(source.path);activate({id:'code:'+source.path,title:source.path.split('/').pop()!,kind:'code',target:source.path},true);
 }
 function closeTab(t:Tab){updateFollow(false);const nextTabs=viewRef.current.tabs.filter(x=>x.id!==t.id),nextActive=activeRef.current===t.id?'flow':viewRef.current.active;viewRef.current={...viewRef.current,tabs:nextTabs,active:nextActive};setTabs(nextTabs);activeRef.current=nextActive;setActive(nextActive);setClosing(null);}
 const onSource=(source:SourceLocation)=>{updateFollow(false);void run(()=>openSource(source),'打开源码');};
 function openScene(id:string,callContext?:{callerLabel:string;source:SourceLocation},fromRuntime=false){const scene=projection.scenes.find(s=>s.id===id);if(scene)activate({id:'scene:'+id+(callContext?':'+callContext.source.path+':'+callContext.source.line:''),title:sceneTitle(projection,id),kind:'scene',target:id,callContext},fromRuntime);}
 async function saveAll(strict=false){
  if(conflictRef.current.length){setShowRecoveryConflicts(true);throw new Error('请先处理恢复草稿与磁盘文件的差异，再保存源码。');}
  let edits=Object.values(docs.current).filter(d=>(!d.base.exists||d.value!==d.base.content)).map(d=>({path:d.base.path,hash:d.base.hash,content:d.value}));
  if(!edits.length&&(projectRef.current.sourceStatus as {valid?:boolean})?.valid===false){const path=projectRef.current.nativeRenpy!.codeFiles[0];const doc=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(path));edits=[{path,hash:doc.hash,content:doc.content}];}
  if(!edits.length)return;
  const disks=await Promise.all(edits.map(edit=>api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(edit.path))));
  const changed=disks.find(d=>{const b=docs.current[d.path]?.base;return b&&(d.hash!==b.hash||d.exists!==b.exists);});
  if(changed){const b=docs.current[changed.path];setMergingRecovery('');setDiff({path:changed.path,base:b.base,disk:changed,local:b.value});throw new Error('源码有外部修改，请合并后再保存。');}
  await recovery.flush('save');
  let result:ProjectResponse&{documents:SourceDocument[];transaction:string;diagnostics:Diagnostic[]};
  try{result=await api.request('/api/workspace/save',{edits,revision:projectRef.current.revision,strict:strict||edits.every(d=>docs.current[d.path]?.origin==='visual')});}
  catch(error){try{const notices=await api.request<{items:SaveNotice[]}>('/api/workspace/save-recovery');setSaveNotices(notices.items);}catch{}throw error;}
  const next=reconcileSavedBuffers(docs.current,result.documents,edits);updateBuffers(next,false);transactions.current.push(result.transaction);undone.current=[];past.current=Object.values(next).some(d=>!d.base.exists||d.value!==d.base.content)?[{...captureFrame(),buffers:Object.fromEntries(Object.entries(next).map(([path,d])=>[path,{base:d.base,value:d.base.content}]))}]:[];future.current=[];replace(result);if(result.project){projectRef.current=result.project;setProjection(result.project);}setDiagnostics(result.diagnostics||[]);if(result.diagnostics?.length){setLogs(result.diagnostics.map(d=>d.message).join('\n'));setShowLogs(true);}await recovery.flush();await refresh();
 }
 const onOperation:NativeOperation=async(adapter,operation)=>{
  await run(async()=>{
   if(conflictRef.current.length)throw new Error('请先处理恢复草稿的差异，再修改可视化表单。');
   if((projectRef.current.sourceStatus as {valid?:boolean})?.valid===false)throw new Error('请先在源码编辑器中修复并保存错误代码。');
   type Prepared={path:string;hash:string;content:string};
   const submitted=snapshot();
   const prepared=await api.request<Prepared&{edits?:Prepared[]}>('/api/workspace/prepare',{adapter,operation,documents:submitted});
   const changes=prepared.edits||[prepared],bases:Record<string,SourceDocument>={};
   for(const edit of changes)if(!submitted.some(d=>d.path===edit.path))bases[edit.path]=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(edit.path));
   for(const edit of changes){const before=submitted.find(d=>d.path===edit.path),latest=docs.current[edit.path];if((before&&!latest)||(latest&&latest.value!==(before?.content??bases[edit.path]?.content)))throw new Error('准备表单修改时源码又有新输入，请重新执行本次表单操作。');}
   const next={...docs.current};
   for(const edit of changes){const base=bases[edit.path],existing:Buffer=next[edit.path]||{base,value:base.content};const content=edit.content.replace(/\r\n/g,'\n').replace(/\n/g,existing.base.newline||'\n');next[edit.path]={...existing,value:content,origin:existing.origin==='code'?'code':'visual'};}
   updateBuffers(next);
   const analyzed=await api.request<WorkspaceIndex&{project:Project}>('/api/workspace/analyze',{documents:snapshot()});setIndex(previous=>({...analyzed,tree:previous?.tree||[]}));setProjection(analyzed.project);
   if(adapter==='config'&&operation.operation!== 'delete'&&operation.operation!=='append'){
    const field=index?.config.bindings[String(operation.binding)];
    if(field&&preview.mode==='edit'&&!field.name.startsWith('preferences.')&&index?.config.groups.some(g=>g.fields.some(f=>f.id===field.id)))void api.request('/api/preview/native',{command:{operation:'variable',name:field.name,value:operation.value}}).catch(e=>setError(e.message));
   }
  },'更新编辑稿');
 };
 async function restoreLiveBuffer(){
  if(preview.mode!=='edit'||preview.status!=='running')return;
  await api.request('/api/preview/native',{command:{operation:'reset'}});
  const analyzed=await api.request<WorkspaceIndex&{project:Project}>('/api/workspace/analyze',{documents:snapshot()});
  setIndex(previous=>({...analyzed,tree:previous?.tree||[]}));setProjection(analyzed.project);
  const source=preview.runtime?.source as SourceLocation|undefined;
  if(!source)return;
  const original=projectRef.current.scenes.find(s=>s.lines.some(l=>'game/'+l.source?.file===source.path&&Number(l.source?.line)===source.line));
  const oldIndex=original?.lines.findIndex(l=>Number(l.source?.line)===source.line)??-1;
  if(!original||oldIndex<0)return;
  const candidate=analyzed.project.scenes.find(s=>s.id===original.id),nextIndex=candidate?.lines.findIndex(l=>l.id===original.lines[oldIndex].id)??-1;
  if(!candidate||nextIndex<0)return;
  const before=effective(original.lines,oldIndex,'visual'),after=effective(candidate.lines,nextIndex,'visual');
  for(const actor of after?.sprites||[]){
   const old=before?.sprites.find(s=>s.id===actor.id);if(!old)continue;
   const props={xpos:actor.x,ypos:actor.y,zoom:actor.scale,xanchor:actor.anchorX,yanchor:actor.anchorY,xzoom:actor.flip?-1:1};
   const bases={xpos:old.x,ypos:old.y,zoom:old.scale,xanchor:old.anchorX,yanchor:old.anchorY,xzoom:old.flip?-1:1};
   if(actor.asset!==old.asset){const image=(actor as typeof actor&{nativeOriginal?:{image:string}}).nativeOriginal?.image;if(image)await api.request('/api/preview/native',{command:{operation:'image',tag:actor.id,image}});}
   if(JSON.stringify(props)!==JSON.stringify(bases))await api.request('/api/preview/native',{command:{operation:'properties',tag:actor.id,values:props,bases}});
  }
  const beforeAudio=effective(original.lines,oldIndex,'audio'),afterAudio=effective(candidate.lines,nextIndex,'audio');
  for(const command of audioVolumeChanges(beforeAudio as unknown as NativeAudioState,afterAudio as unknown as NativeAudioState,analyzed.project.nativeRenpy?.audioChannels||defaultChannels))await api.request('/api/preview/native',{command});
 }
 async function undo(redo=false){
  const stack=redo?future:past,other=redo?past:future;
  if(stack.current.length){const frame=stack.current.pop()!;other.current.push(captureFrame(frame.localOnly));updateBuffers(frame.buffers,false);conflictRef.current=frame.conflicts;setRecoveryConflicts(frame.conflicts);applyRecoveryViews({...frame.view,documents:Object.values(frame.buffers)},frame.buffers);if(!frame.localOnly)await restoreLiveBuffer();return;}
  const committed=redo?undone:transactions,opposite=redo?transactions:undone;
  const id=committed.current.at(-1);if(!id)return;
  const result=await api.request<ProjectResponse>('/api/workspace/restore',{transaction:id,revision:projectRef.current.revision,redo});committed.current.pop();opposite.current.push(id);replace(result);
  for(const path of Object.keys(docs.current)){const document=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(path));if(document.exists)docs.current[path]={base:document,value:document.content};else{delete docs.current[path];setTabs(v=>v.filter(t=>t.target!==path));if(activeRef.current==='code:'+path)setActive('flow');}}setBuffers({...docs.current});await refresh();
 }
 const saveRef=useRef(saveAll),undoRef=useRef(undo);saveRef.current=saveAll;undoRef.current=undo;
 useEffect(()=>{const listener=(e:KeyboardEvent)=>{if(e.defaultPrevented||frozen.current)return;const modifier=e.ctrlKey||e.metaKey;if(modifier&&e.key.toLowerCase()==='s'){e.preventDefault();void run(()=>saveRef.current(),'保存并检查源码');}if(modifier&&e.key.toLowerCase()==='z'&&!(e.target as HTMLElement)?.closest('.monaco-editor,input,textarea')){e.preventDefault();void run(()=>undoRef.current(e.shiftKey),'撤销／重做');}};const leave=(e:BeforeUnloadEvent)=>{if(!api.onPrepareClose&&Object.values(docs.current).some(d=>(!d.base.exists||d.value!==d.base.content))){e.preventDefault();e.returnValue='';}};window.addEventListener('keydown',listener);window.addEventListener('beforeunload',leave);return()=>{window.removeEventListener('keydown',listener);window.removeEventListener('beforeunload',leave);};},[run]);
 useEffect(()=>{if(!recovery.ready||closingApp)return;let alive=true,pending=false;const poll=async()=>{if(pending)return;pending=true;try{const result=await api.request<PreviewStatus&{projectRevision?:number}>('/api/preview/status?after='+lastEvent.current);if(!alive)return;setPreview(result);if(result.projectRevision&&result.projectRevision!==projectRef.current.revision)await refresh();for(const event of result.events||[]){lastEvent.current=Math.max(lastEvent.current,Number(event.seq||0));if(event.type==='error'&&event.message)setError(String(event.message));if(event.message)setLogs(v=>(v+'\n'+String(event.message)).slice(-30000));if(event.type==='native_drag'&&event.source){const source=event.source as SourceLocation;const doc=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(source.path));await onOperation('stage',{...source,hash:doc.hash,operation:'properties',values:{xpos:event.x,ypos:event.y}});}if(event.type==='project_changed'&&!event.taskId&&event.project){replace({project:event.project as Project,root,session:currentProjectSession()});await refresh();}}const source=result.runtime?.source as SourceLocation|undefined;if(alive&&source&&followRef.current&&result.status==='running'&&!result.runtime?.fragmentDone&&!result.runtime?.motionPreview){setLocation(source);if(activeRef.current.startsWith('code:')&&activeRef.current!=='code:'+source.path&&projectRef.current.nativeRenpy?.codeFiles.includes(source.path))await openSource(source,true);if(alive&&followRef.current&&activeRef.current.startsWith('scene:')){const label=projectRef.current.nativeRenpy?.labels.find(l=>l.name===(result.runtime?.context as {nativeLabel?:string})?.nativeLabel);if(label)openScene(label.id,undefined,true);}}}catch{}finally{pending=false;}};void poll();const timer=setInterval(poll,500);return()=>{alive=false;clearInterval(timer);};},[root,follow,recovery.ready,closingApp]);
 async function metadata(patch:Record<string,unknown>,assets?:Asset[]){await run(async()=>{if(!assets&&Object.entries(patch).every(([key,value])=>JSON.stringify((projectRef.current.ide as Record<string,unknown>||{})[key])===JSON.stringify(value)))return;const result=await api.request<ProjectResponse>('/api/workspace/metadata',{revision:projectRef.current.revision,ide:{...(projectRef.current.ide as object||{}),...patch},...(assets?{assets}:{})});replace(result);if(result.project)projectRef.current=result.project;},'保存项目配置');}
 async function actorSource(nodeId:string,tag:string,action:boolean){
  await run(async()=>{const result=await api.request<{source:SourceLocation;actionSource:SourceLocation}>('/api/workspace/motion-source',{nodeId,tag,documents:snapshot()});await openSource(action?result.actionSource:result.source);},'打开立绘源码');
 }
 async function motionPreview(nodeId:string,tag:string){
  await run(async()=>{await saveAll();if((projectRef.current.sourceStatus as {valid?:boolean})?.valid===false)throw new Error('请先修复源码错误，再播放动作。');setPreview(await api.request<PreviewStatus>('/api/preview/motion',{nodeId,tag,revision:projectRef.current.revision}));lastEvent.current=0;},'播放立绘动作');
 }
 async function start(label='start',mode:'edit'|'play'='play',clean=false,scope:'fragment'|'continue'='fragment'){try{if(clean&&projectRef.current.nativeRenpy?.inPlace){const result=await api.request<PreviewStatus>('/api/preview/start',{entry:{clean:true},mode:'play'});setPreview(result);lastEvent.current=0;return;}const missing=projectRef.current.assets.filter(a=>a.status==='missing');if(missing.length&&!projectRef.current.nativeRenpy?.inPlace)throw new Error('素材待补：'+missing.map(a=>a.requirement||a.name).join('；'));await saveAll();if(projectRef.current.sourceStatus&&(projectRef.current.sourceStatus as {valid:boolean}).valid===false)throw new Error('请先修复源码错误，再启动新预览。');const args=JSON.parse(testArgs),state=JSON.parse(testState),initialize=JSON.parse(testCalls);const result=await api.request<PreviewStatus>('/api/preview/start',{entry:{nativeLabel:label,args,state,initialize,clean,scope},mode});setPreview(result);lastEvent.current=0;}catch(e){const message=e instanceof Error?e.message:String(e);if(/素材待补|请先补充或明确选择占位素材/.test(message)){openAssetGaps();throw new Error('试玩尚未启动：项目仍有缺失素材。请在清单中添加／更新文件，或逐项选择“暂时没有，使用占位符”。');}throw e;}}
 function live(command:Record<string,unknown>){if(preview.status!=='running'||preview.mode!=='edit')return;void api.request('/api/preview/native',{command}).catch(e=>setError(e.message));}
 useEffect(()=>{if(preview.status==='running'&&preview.mode==='edit')void api.request('/api/preview/native',{command:{operation:'document_state',dirty}}).catch(()=>{});},[dirty,preview.sessionId,preview.status,preview.mode]);
 async function newFile(){const path=prompt('新文件路径，例如 game/chapter2.rpy','game/new_scene.rpy');if(!path)return;await openSource({path,line:1});}
 async function renameFile(item:TreeNode){const next=prompt('新文件路径',item.path);if(!next||next===item.path)return;await saveAll();const doc=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(item.path));const result=await api.request<ProjectResponse>('/api/workspace/rename',{path:item.path,newPath:next,hash:doc.hash,revision:projectRef.current.revision});replace(result);if((result as ProjectResponse&{transaction?:string}).transaction)transactions.current.push((result as ProjectResponse&{transaction:string}).transaction);const nextDocs={...docs.current};delete nextDocs[item.path];updateBuffers(nextDocs,false);setTabs(v=>v.filter(t=>t.target!==item.path));await refresh();await openSource({path:next,line:1});}
 async function compare(){const path=tab.kind==='code'?tab.target:lastCode;if(!path||!docs.current[path])return;const disk=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(path));setMergingRecovery('');setDiff({path,base:docs.current[path].base,disk,local:docs.current[path].value});}
 async function openRenpy(){
  if(!api.openRenpy)throw new Error('请使用桌面版 IDE 打开 Ren’Py 启动器。');
  const session=currentProjectSession(),result=await api.openRenpy({projectSession:session});
  if(session!==currentProjectSession())throw new Error('项目已切换，忽略旧项目的启动器响应。');
  setLauncherPrompt(false);
  setLauncherNotice(result.status==='already-open'?(result.selectedProject===root?'Ren’Py 启动器已打开，请在其中选择“构建发行版”。':'Ren’Py 启动器已打开，请在其中选择当前工程：'+root):'已打开 Ren’Py 启动器并选中当前工程，请选择“构建发行版”。');
 }
 const errorSources=[...new Map(Array.from((error+'\n'+logs).matchAll(/File "([^"\n]+)", line (\d+)/g)).flatMap(m=>{const file=m[1].replaceAll('\\','/'),pos=file.indexOf('game/');return pos>=0?[[file.slice(pos)+':'+m[2],{path:file.slice(pos),line:Number(m[2])}] as const]:[];})).values()];
 const assetNeeds=projection.nativeAssetLibrary?projection.assets.filter(a=>a.virtual&&a.virtualStatus!=='bound'):project.assets.filter(a=>a.status!=='ready');
 const scene=projection.scenes.find(s=>s.id===tab.target),group=index?.config.groups.find(g=>g.id===tab.target),codeDocument=lastCode&&buffers[lastCode],mediaAsset=project.assets.find(a=>a.id===media);
 return <DockScope scope={root}><div className="app native-ide" inert={closingApp||!recovery.ready}><header className="app-header"><div className="brand"><BookOpen size={21}/><strong>Morinote IDE</strong><small>{version}</small></div><span className="project-title" title={root}>{project.title}<small>{dirty?'源码未保存':'源码已保存'} · {project.revision}</small></span><div className="header-actions"><button aria-label="撤销" onClick={()=>void run(()=>undo(),'撤销')}><Undo2 size={15}/></button><button aria-label="重做" onClick={()=>void run(()=>undo(true),'重做')}><Redo2 size={15}/></button><button disabled={!!status} onClick={()=>void run(()=>saveAll(),'保存并检查源码')}><Save size={14}/>{dirty?'保存全部':'检查／保存'}</button><button className="primary" onClick={()=>void run(()=>start('start','play',true),'启动原工程磁盘版本')}><Play size={13}/>原游戏试玩</button><button onClick={()=>{setTestLabel(project.nativeRenpy!.labels.find(l=>l.id===tab.target)?.name||'start');setTest(true);}}>片段测试</button><button disabled={!recovery.available} onClick={()=>setRecoveryHistory(true)}>恢复历史</button></div></header><div className="app-body"><DockPanel id="project-navigation" title="项目导航" side="left" initialSize={230}><aside className="sidebar native-sidebar"><div className="project-operations"><button onClick={()=>void run(async()=>{await saveAll();onOpen();},'保存当前工程')}><FolderOpen size={14}/>打开项目</button><button aria-label="新建项目" onClick={()=>void run(async()=>{await saveAll();onNew();},'保存当前工程')}><Plus size={13}/></button></div><nav><button className={tab.kind==='flow'?'active':''} onClick={()=>activate(firstTab)}><GitBranch size={14}/>剧情总图</button><button className={tab.kind==='assets'?'active':''} onClick={()=>{setAssetGaps(false);activate({id:'assets',title:'项目素材库',kind:'assets'});}}><Image size={14}/>项目素材库</button></nav><div className="sidebar-label"><button onClick={()=>setSystemsOpen(v=>!v)}>{systemsOpen?<ChevronDown size={12}/>:<ChevronRight size={12}/>}系统配置</button></div><nav>{systemsOpen&&[...(index?.config.groups||[])].sort((a,b)=>Number(b.id==='sessions')-Number(a.id==='sessions')).map(g=><button key={g.id} className={tab.id==='config:'+g.id?'active':''} onClick={()=>activate({id:'config:'+g.id,title:g.title,kind:'config',target:g.id})}><Settings2 size={12}/>{g.title}</button>)}</nav><div className="sidebar-label">项目文件<button aria-label="新增源码文件" onClick={()=>void run(newFile,'新建文件')}><Plus size={12}/></button></div><div className="project-file-tree">{index&&<><div className="file-view-switch"><button className={fileView==='purpose'?'active':''} onClick={()=>setFileView('purpose')}>按用途</button><button className={fileView==='directory'?'active':''} onClick={()=>setFileView('directory')}>原始目录</button></div><Tree key={fileView} items={fileView==='purpose'?groupedFiles(index.tree,projection,index):index.tree} onClassify={setClassifying} onOpen={item=>{if(item.text)onSource({path:item.path,line:1});else{const a=project.assets.find(a=>a.path===item.path);if(a){setMedia(a.id);activate({id:'media:'+a.id,title:item.name,kind:'media',target:a.id});}else setError('此二进制文件请使用外部工具编辑。');}}} onRename={item=>void run(()=>renameFile(item),'重命名文件')}/></>}</div><div className="sidebar-bottom"><button disabled={!!status||!api.openRenpy} onClick={()=>{if(dirty)setLauncherPrompt(true);else void run(openRenpy,'打开 Ren’Py 启动器');}}><ExternalLink size={13}/>打开 Ren’Py 启动器</button><small>Ren’Py 8.5.3 · {root}</small></div></aside></DockPanel><main className="native-workspace">{saveNotices.length>0&&<div className="error-banner"><span>上次保存中断，已恢复可恢复文件；未完成的修改已保留。{saveNotices.some(n=>n.conflicts.length>0)&&' 外部修改的文件未覆盖。'}</span><button onClick={()=>void run(restoreSaveDrafts,'恢复未完成保存的草稿')}>恢复保存草稿</button></div>}<div className="document-tabs" role="tablist">{tabs.map(t=><div className={active===t.id?'active':''} key={t.id}><button role="tab" aria-selected={active===t.id} onClick={()=>{updateFollow(false);activeRef.current=t.id;setActive(t.id);if(t.kind==='code')setLastCode(t.target!);}}>{t.kind==='code'?<Code2 size={12}/>:t.kind==='flow'?<GitBranch size={12}/>:null}{t.kind==='scene'?sceneTitle(projection,t.target!):t.title}{t.kind==='code'&&buffers[t.target!]?.value!==buffers[t.target!]?.base.content?' •':''}</button>{t.id!=='flow'&&<button aria-label={'关闭 '+(t.kind==='scene'?sceneTitle(projection,t.target!):t.title)} onClick={()=>{if(t.kind==='code'&&buffers[t.target!]&&(!buffers[t.target!].base.exists||buffers[t.target!].value!==buffers[t.target!].base.content))setClosing(t);else closeTab(t);}}><X size={11}/></button>}</div>)}</div>{error&&<div className="error-banner" role="alert"><span>{error}</span>{error.includes('外部修改')&&<button onClick={()=>void run(compare,'比较差异')}>比较差异</button>}<button aria-label="关闭错误" onClick={()=>setError('')}><X size={12}/></button></div>}{launcherNotice&&<div className="review-banner" role="status"><span>{launcherNotice}</span><button aria-label="关闭启动器提示" onClick={()=>setLauncherNotice('')}><X size={12}/></button></div>}{recovery.failure&&<div className="error-banner" role="alert"><span>{recovery.failure}</span><button onClick={recovery.retry}>重试备份</button></div>}{recovery.warning&&<div className="review-banner" role="status">{recovery.warning}</div>}{recoveryBlocked&&<div className="review-banner"><span>{recoveryConflicts.length} 个恢复文件待处理</span><button onClick={()=>setShowRecoveryConflicts(true)}>比较并处理</button></div>}{(project.sourceStatus as {valid?:boolean})?.valid===false&&<div className="review-banner">源码含错误，当前显示上一次有效索引与预览。<button onClick={()=>{setLogs(String((project.sourceStatus as {message?:string})?.message));setShowLogs(true);}}>查看错误</button></div>}<div className="native-document">{assetNeeds.length>0&&<div className="review-banner"><span>{assetNeeds.length} 项素材待补</span>{assetNeeds.some(a=>a.kind==='background')&&<span>背景待补：{assetNeeds.filter(a=>a.kind==='background').map(a=>a.requirement||a.name).join('、')}</span>}<button onClick={openAssetGaps}>查看并处理</button></div>}<div className="code-document" style={{display:tab.kind==='code'?'flex':'none'}}>{codeDocument&&<><div className="code-toolbar"><code>{lastCode}</code><button onClick={()=>void run(compare,'比较源码')}>与磁盘比较</button><button onClick={()=>{const matching=projection.scenes.find(s=>s.lines.some(l=>'game/'+l.source?.file===lastCode&&Number(l.source?.line)===location?.line));if(matching)openScene(matching.id);else setError('当前行没有对应的三轨文字节点，可在总图中查看所属标签。');}}>定位三轨</button></div><Suspense fallback={<p>载入本地代码编辑器…</p>}><SourceEditor document={{...codeDocument.base,content:codeDocument.value}} location={location} onChange={value=>{if(!frozen.current&&docs.current[lastCode]&&docs.current[lastCode].value!==value)updateBuffers({...docs.current,[lastCode]:{...docs.current[lastCode],value,origin:'code'}});}} onSave={()=>void run(()=>saveAll(),'保存并检查源码')} onLocation={(line,column)=>{if(!frozen.current)setLocation({path:lastCode,line,column});}}/></Suspense></>}</div>{tab.kind==='flow'&&index&&<NativeFlow flow={index.flow} project={projection} onOperation={onOperation} onSource={onSource} onScene={openScene} onPreview={label=>{setTestLabel(label);setTest(true);}} onLayout={metadata} currentLabel={(preview.runtime?.context as {nativeLabel?:string})?.nativeLabel}/>} {tab.kind==='scene'&&scene&&<NativeTimeline onAsset={id=>{setAssetFocus(id);setAssetGaps(false);activate({id:'assets',title:'项目素材库',kind:'assets'});}} key={tab.id} callContext={tab.callContext} scene={scene} project={projection} onOperation={onOperation} onSource={onSource} onActorSource={actorSource} onMotionPreview={motionPreview} onPreview={(label,edit,scope)=>void run(()=>start(label,edit?'edit':'play',false,scope),'启动场景预览')} onLive={live} current={follow?preview.runtime?.source as SourceLocation:undefined} onMetadata={(m,a)=>metadata(m as unknown as Record<string,unknown>,a)} onRefresh={refresh}/>} {tab.kind==='config'&&group&&<NativeConfig group={group} project={projection} onScene={openScene} onOperation={onOperation} onSource={onSource} onAsset={setAssetField} onPreview={(label,state)=>{setTestLabel(label);if(state)setTestState(JSON.stringify(state));setTest(true);}}/>}{tab.kind==='assets'&&<NativeAssets initialSelectedId={assetFocus} onOperation={onOperation} key={project.id+(assetGaps?':gaps':':all')} initialMissingOnly={assetGaps} project={projection} onMetadata={(m,a)=>metadata(m as unknown as Record<string,unknown>,a)} onRefresh={refresh} onSource={onSource}/>} {tab.kind==='media'&&mediaAsset&&<div className="media-document"><h2>{mediaAsset.name}</h2>{mediaAsset.kind==='audio'?<AudioPlayer id={mediaAsset.id}/>:<Media asset={mediaAsset}/>}<code>{mediaAsset.path}</code></div>}</div>{preview.status!=='stopped'&&<div className="preview-bar"><strong>{preview.status==='running'?(preview.runtime?.original?'原游戏运行中':preview.runtime?.motionPreview?'立绘动作预览':preview.runtime?.fragmentDone?'片段已结束':'原引擎已连接'):preview.status}</strong><small>{preview.runtime?.original?'原工程磁盘版本 · 独立试玩存档':<>运行版本 {preview.revision} / 源码 {project.revision}</>}</small>{!preview.runtime?.original&&<>{!preview.runtime?.motionPreview&&<button onClick={()=>void run(async()=>{if(preview.mode==='edit')await saveAll(true);setPreview(await api.request('/api/preview/mode',{mode:preview.mode==='edit'?'play':'edit'}));},'切换预览模式')}><Move size={12}/>{preview.mode==='edit'?'进入试玩':'暂停编辑'}</button>}<button onClick={()=>void run(async()=>{await saveAll();setPreview(await api.request('/api/preview/reload',{}));},'检查并重载')}><RefreshCw size={12}/>{preview.runtime?.motionPreview?'重播动作':'重新载入'}</button><label hidden={!!preview.runtime?.motionPreview}><input type="checkbox" checked={follow} onChange={e=>updateFollow(e.target.checked)}/>跟随运行</label><button onClick={()=>void api.request('/api/preview/screenshot',{}).catch(e=>setError(e.message))}>截图</button></>}<button aria-label="停止预览" onClick={()=>void run(async()=>setPreview(await api.request('/api/preview/stop',{})),'关闭预览')}><Square size={12}/></button></div>}{showLogs&&<DockPanel id="run-log" title="运行记录" side="bottom" initialSize={240} minSize={100}><section className="native-log"><header><strong>检查与运行记录</strong><button onClick={()=>setShowLogs(false)}>收起</button></header>{diagnostics.map((d,i)=><p key={i}>{d.message}</p>)}{preview.error&&<p role="alert">{preview.error}</p>}{errorSources.map(s=><button key={s.path+':'+s.line} onClick={()=>onSource(s)}>{s.path}:{s.line}</button>)}<pre>{logs||JSON.stringify(preview.runtime,null,2)}</pre>{location&&<button onClick={()=>onSource(location)}>当前源码：{location.path}:{location.line}</button>}</section></DockPanel>}</main></div><footer className="statusbar"><span>{status||error||'就绪'}</span><span>{dirty?'源码未保存':'源码已保存'} · {recovery.available?(recovery.failure?'草稿备份失败':recovery.pending?'草稿等待备份':recovery.savedAt?'草稿已备份 '+new Date(recovery.savedAt).toLocaleTimeString('zh-CN',{hour12:false}):'尚无草稿备份'):'桌面版支持草稿备份'} <button onClick={()=>{setLogs(JSON.stringify(preview.runtime,null,2));setShowLogs(true);}}>运行状态</button><button onClick={()=>void run(async()=>{await saveAll();const r=await api.request<{log:string;diagnostics:Diagnostic[]}>('/api/build',{lint:true});setLogs(r.log);setDiagnostics(r.diagnostics);setShowLogs(true);},'Ren’Py lint')}>检查</button></span></footer>{classifying&&<Modal title="文件用途" onClose={()=>setClassifying(null)}><div className="modal-body"><code>{classifying.path}</code>{fileGroupNames.map(name=><button key={name} onClick={()=>void metadata({fileGroups:{...((project.ide as {fileGroups?:Record<string,string>})?.fileGroups||{}),[classifying.path]:name}}).then(()=>setClassifying(null)).catch(e=>setError(e.message))}>{name}</button>)}</div></Modal>}{assetField&&<Modal title={'选择 '+assetField.label+' 素材'} wide onClose={()=>setAssetField(null)}><NativeAssets project={projection} onOperation={onOperation} runtimeMode={typeof assetField.value==='string'&&assetField.value.includes('/')?'file':undefined} pickKind={assetField.assetKind} onMetadata={(m,a)=>metadata(m as unknown as Record<string,unknown>,a)} onRefresh={refresh} onSource={onSource} onPick={asset=>{const a=asset as Asset&{nativeGamePath?:string;nativeAliases?:string[]};const value=typeof assetField.value==='string'&&!assetField.value.includes('/')&&a.nativeAliases?.length?a.nativeAliases[0]:a.nativeGamePath||a.path;void onOperation('config',{binding:assetField.id,hash:assetField.hash,value}).then(()=>setAssetField(null));}}/></Modal>}{diff&&<SourceMerge base={diff.base} local={diff.local} disk={diff.disk} onClose={()=>{setDiff(null);setMergingRecovery('');}} onApply={(text,disk)=>run(async()=>{
 const current=docs.current[diff.path];if(!current||current.value!==diff.local||current.base.hash!==diff.base.hash)throw new Error('编辑稿又发生了变化，请重新比较。');
 const fresh=await api.request<SourceDocument>('/api/workspace/document?path='+encodeURIComponent(diff.path));
 if(fresh.hash!==disk.hash||fresh.exists!==disk.exists)throw new Error('磁盘又发生了变化，请关闭后重新比较。');
 await recovery.flush('restore');const latest=docs.current[diff.path];if(!latest||latest.value!==diff.local||latest.base.hash!==diff.base.hash)throw new Error('编辑稿又发生了变化，请重新比较。');updateBuffers({...docs.current,[diff.path]:{base:fresh,value:text,origin:'code'}},true,true);
 if(mergingRecovery){const remaining=conflictRef.current.filter(c=>c.path!==mergingRecovery);conflictRef.current=remaining;setRecoveryConflicts(remaining);}
 await recovery.flush();
 },'合并源码').then(()=>{})}/>} {closing&&<Modal title="文件有未保存更改" onClose={()=>setClosing(null)}><div className="modal-body"><p>{closing.target}</p><button onClick={()=>void run(async()=>{await saveAll();closeTab(closing);},'保存并关闭')}>保存全部并关闭</button><button onClick={()=>void run(()=>discardFile(closing),'放弃文件编辑')}>放弃该文件编辑</button><button onClick={()=>setClosing(null)}>取消</button></div></Modal>}{launcherPrompt&&<Modal title="打开 Ren’Py 启动器" onClose={()=>{if(!status)setLauncherPrompt(false);}}><div className="modal-body"><p>存在未保存修改。Ren’Py 构建发行版使用磁盘上的源码。</p><button disabled={!!status} onClick={()=>void run(async()=>{await saveAll();if(Object.values(docs.current).some(d=>!d.base.exists||d.value!==d.base.content))throw new Error('保存期间有新输入，请再次保存，或选择打开磁盘版本。');await openRenpy();},'保存源码并打开 Ren’Py 启动器')}>保存全部并打开</button><button disabled={!!status} onClick={()=>void run(openRenpy,'打开 Ren’Py 启动器')}>打开磁盘版本</button><button disabled={!!status} onClick={()=>setLauncherPrompt(false)}>取消</button></div></Modal>}{recoveryHistory&&<RecoveryHistory onClose={()=>setRecoveryHistory(false)} loadHistory={loadRecoveryHistory} loadSnapshot={loadRecoverySnapshot} readFiles={readRecoveryFiles} buffers={buffers} onRestore={(state,paths)=>run(()=>restoreHistory(state,paths),'恢复历史草稿').then(()=>{})}/>} {showRecoveryConflicts&&<RecoveryConflicts onMerge={conflict=>{const draft=docs.current[conflict.path]||conflict.draft;if(!conflict.disk)return;setShowRecoveryConflicts(false);setMergingRecovery(conflict.path);setDiff({path:conflict.path,base:draft.base,disk:conflict.disk,local:draft.value});}} conflicts={recoveryConflicts.map(c=>({...c,draft:buffers[c.path]||c.draft}))} onClose={()=>setShowRecoveryConflicts(false)} onResolve={(conflict,choice,target)=>run(()=>resolveRecovery(conflict,choice,target),'处理恢复草稿').then(()=>{})}/>} {test&&<Modal title="片段测试入口" onClose={()=>setTest(false)}><div className="modal-body"><label>入口标签<select aria-label="入口标签" value={testLabel} onChange={e=>setTestLabel(e.target.value)}>{project.nativeRenpy!.labels.map(l=><option key={l.id} value={l.name}>{sceneOption(project,l.id)}{l.parameters}</option>)}</select></label><label>标签参数（JSON 数组）<input value={testArgs} onChange={e=>setTestArgs(e.target.value)}/></label><label>测试状态（JSON 对象）<textarea value={testState} onChange={e=>setTestState(e.target.value)}/></label><label>前置标签调用（JSON 数组）<input value={testCalls} onChange={e=>setTestCalls(e.target.value)}/></label><button onClick={()=>void metadata({testEntry:{label:testLabel,args:testArgs,state:testState,initialize:testCalls}})}>保存测试入口</button><button className="primary" onClick={()=>void run(async()=>{await start(testLabel,'edit');setTest(false);},'启动片段预览')}>打开编辑预览</button><button onClick={()=>void run(async()=>{await start(testLabel,'play');setTest(false);},'启动片段试玩')}>仅试玩此片段</button><button onClick={()=>void run(async()=>{await start(testLabel,'play',false,'continue');setTest(false);},'从此入口继续游戏')}>从这里继续游戏</button></div></Modal>}</div>{(closingApp||!recovery.ready)&&<div className="recovery-lock" role="status"><strong>{closingApp?'正在备份并关闭…':'正在读取恢复草稿…'}</strong><p>{closingApp?'等待进行中的保存与最后一次草稿备份完成。':recovery.failure||'正在比较项目文件与草稿。'}</p>{!closingApp&&recovery.failure&&<button onClick={recovery.retry}>重试读取</button>}</div>}</DockScope>;
}
