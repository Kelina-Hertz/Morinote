import {useEffect,useMemo,useRef,useState} from 'react';
import {ReactFlow,Background,Controls,MiniMap,MarkerType,Position,type Node,type Viewport,type ReactFlowInstance,type Connection} from '@xyflow/react';
import {Plus,Code2,Play,ChevronDown,Workflow,X,Settings2} from 'lucide-react';
import type {Project} from './types';
import type {NativeFlow as Flow,NativeOperation,SourceLocation,FlowEditPoint,NativeFlowNode} from './native-types';
import {Modal} from './ui';
import {storyLayout,type LayoutDirection} from './story-layout';
import {sceneTitle} from './scene-titles';
import DockPanel from './DockPanel';
import {sceneInfo} from './story-profile';
import FlowAuthoringDialog from './FlowAuthoringDialog';
import {flowHashes,formsCycle,freshScene,insertionProblem,pointsForNode,type NewFlowScene,type FlowBlockKind,type FlowIntent} from './flow-authoring';
import CanvasQuickCreate from './CanvasQuickCreate';
import './flow-inspector.css';
import ChapterNode from './ChapterNode';
import {chapterPorts,chapterCollapsedHeight} from './chapter-ports';
import StoryNode from './StoryNode';
import {initialCondition,conditionResult,type FlowConditionDraft} from './flow-condition';
import './flow-canvas.css';
type CanvasPosition={x:number;y:number};
type CanvasMenu={x:number;y:number;position:CanvasPosition;group:string;point?:FlowEditPoint};
type BlockRequest={kind:FlowBlockKind;group:string;point?:FlowEditPoint;position?:CanvasPosition;edit?:FlowEditPoint;scene?:NewFlowScene;options?:string[]};
type QuickDraft=BlockRequest&{scene:NewFlowScene;options:string[];position:CanvasPosition;condition:FlowConditionDraft;optionTargets?:(string|null)[]};
type InsertPreview={edge:string;point:FlowEditPoint;scene:string;scenePoint:string;message:string};
type ChapterSettings={chapterEntries?:Record<string,string>;chapterExitPoints?:Record<string,string>};
const nodeTypes={group:ChapterNode,story:StoryNode,quickCreate:CanvasQuickCreate};

export default function NativeFlow({flow:sourceFlow,project,onOperation,onSource,onScene,onPreview,onLayout,currentLabel}:{flow:Flow;project:Project;onOperation:NativeOperation;onSource:(s:SourceLocation)=>void;onScene:(id:string,context?:{callerLabel:string;source:SourceLocation})=>void;onPreview:(label:string)=>void;onLayout:(patch:Record<string,unknown>,undoable?:boolean)=>Promise<void>;currentLabel?:string}){
 const [detailed,setDetailed]=useState(false),[focusGroup,setFocusGroup]=useState(''),[copiesOpen,setCopiesOpen]=useState(false),[pendingScene,setPendingScene]=useState(''),[notice,setNotice]=useState('');
 const [connectionFeedback,setConnectionFeedback]=useState<{message:string}|null>(null);
 useEffect(()=>{
  if(!connectionFeedback)return;
  const timer=window.setTimeout(()=>setConnectionFeedback(null),3500);
  return ()=>window.clearTimeout(timer);
 },[connectionFeedback]);
 useEffect(()=>{if(!notice)return;const timer=window.setTimeout(()=>setNotice(''),3000);return()=>window.clearTimeout(timer);},[notice]);
 const canvas=useRef<Pick<ReactFlowInstance,'fitView'|'getNodes'|'screenToFlowPosition'>|null>(null),changing=useRef(false);
 const canvasElement=useRef<HTMLElement|null>(null),connectionRef=useRef<string|null>(null),hoveredRef=useRef(''),dragFrame=useRef(0),lastDragCheck=useRef(0);
 const [measurements,setMeasurements]=useState<Record<string,{width:number;height:number}>>({}),[quick,setQuick]=useState<QuickDraft|null>(null),[quickError,setQuickError]=useState(''),[connecting,setConnecting]=useState<string|null>(null),[hovered,setHovered]=useState(''),[insertPreview,setInsertPreview]=useState<InsertPreview|null>(null),[selectedNodes,setSelectedNodes]=useState<string[]>([]);
 const [selectedEdges,setSelectedEdges]=useState<string[]>([]),[graphBusy,setGraphBusy]=useState(false),[menu,setMenu]=useState<CanvasMenu|null>(null),[placement,setPlacement]=useState<{name:string;position:CanvasPosition}|null>(null);
 const [unlinkedOnly,setUnlinkedOnly]=useState(false),[intent,setIntent]=useState<{mode:FlowIntent;point:FlowEditPoint;target?:string}|null>(null),[focusNode,setFocusNode]=useState('');
 const rawFlow=detailed?(sourceFlow.storyDetail||sourceFlow.story||sourceFlow):(sourceFlow.story||sourceFlow);
 const flow=useMemo(()=>{
  const extraGroups=new Set(rawFlow.groups.filter(g=>g.title==='番外').map(g=>g.id));
  const orphanLabels=new Set(rawFlow.nodes.filter(n=>n.type==='scene'&&n.reachability==='disconnected').map(n=>n.id));
  const nodes=rawFlow.nodes.filter(n=>!(!detailed&&n.type==='return'&&n.editPoint)&&!extraGroups.has(n.group)&&!/(?:^|\/)ova[^/]*\.rpy$/i.test(n.source.path)&&(!unlinkedOnly||orphanLabels.has(n.label)));
  const ids=new Set(nodes.map(n=>n.id)),groups=new Set(nodes.map(n=>n.group));
  return {...rawFlow,nodes,edges:rawFlow.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)),groups:rawFlow.groups.filter(g=>groups.has(g.id))};
 },[rawFlow,unlinkedOnly,detailed]);
 const ide=(project.ide||{}) as {collapsedGroups?:string[];flowPositions?:Record<string,{x:number;y:number}>;flowViewport?:Viewport;flowLayoutVersion?:number;storyFlowPositions?:Record<string,{x:number;y:number}>;storyFlowViewport?:Viewport;storyFlowLayoutVersion?:number;detailFlowPositions?:Record<string,{x:number;y:number}>;detailFlowViewport?:Viewport;detailFlowLayoutVersion?:number;storyFlowDirections?:Record<string,LayoutDirection>;detailFlowDirections?:Record<string,LayoutDirection>};
 const layoutVersion=detailed?ide.detailFlowLayoutVersion:ide.storyFlowLayoutVersion,viewport=detailed?ide.detailFlowViewport:ide.storyFlowViewport;
 const [collapsed,setCollapsed]=useState<string[]>((ide.storyFlowLayoutVersion===5?ide.collapsedGroups:undefined)||flow.groups.filter(g=>g.id!==(flow.groups.find(x=>x.title.startsWith('第一章')||x.title==='第1章')||flow.groups[0])?.id).map(g=>g.id)),[selected,setSelected]=useState(''),[positions,setPositions]=useState(ide.storyFlowLayoutVersion===5?ide.storyFlowPositions||{}:{}),[error,setError]=useState('');
 const savedPositions=detailed?ide.detailFlowPositions:ide.storyFlowPositions,savedDirections=detailed?ide.detailFlowDirections:ide.storyFlowDirections;
 const [directions,setDirections]=useState<Record<string,LayoutDirection>>(savedDirections||{}),[arrangeDirection,setArrangeDirection]=useState<LayoutDirection>('vertical');
 const savedLayout=JSON.stringify({positions:savedPositions||{},directions:savedDirections||{}});
 useEffect(()=>{const layout=JSON.parse(savedLayout) as {positions:Record<string,CanvasPosition>;directions:Record<string,LayoutDirection>};setPositions(layout.positions);setDirections(layout.directions);},[savedLayout,detailed]);
 const node=flow.nodes.find(n=>n.id===selected);
 const selectedGroup=flow.groups.find(g=>'group:'+g.id===selected);
 useEffect(()=>{
  if(!pendingScene)return;
  const created=flow.nodes.find(n=>n.type==='scene'&&project.nativeRenpy?.labels.some(l=>l.id===n.label&&l.name===pendingScene));
  if(!created)return;
  setSelected(created.id);setSelectedNodes([created.id]);setCollapsed(v=>v.filter(g=>g!==created.group));setPendingScene('');
 },[pendingScene,flow,project]);
 function destination(point:FlowEditPoint){return point.target?'→ '+sceneTitle(project,point.target):point.status==='pending'?'待连接':'结束此段';}
 function showIntent(mode:FlowIntent,point:FlowEditPoint,target?:string){
  if(mode==='connect'){setIntent({mode,point,target});setError('');return;}
  newBlock(mode==='insert'?'scene':'choice',creationContext(0,0,point,nodePosition(point.node||point.owner)));
 }
 function nodePosition(id:string):CanvasPosition{
  const current=canvas.current?.getNodes().find(n=>n.id===id),parent=canvas.current?.getNodes().find(n=>n.id===current?.parentId);
  return {x:(current?.position.x||0)+(parent?.position.x||0)+340,y:(current?.position.y||0)+(parent?.position.y||0)};
 }
 function editCondition(point:FlowEditPoint){
  if(changing.current||quick)return;
  const owner=sourceFlow.nodes.find(n=>n.id===point.owner),label=project.nativeRenpy?.labels.find(l=>l.id===point.owner);
  setQuickError('');setMenu(null);
  setQuick({kind:'condition',group:owner?.group||'剧情',edit:point,position:nodePosition(point.node||point.owner),scene:{name:label?.name||'',path:point.source.path,title:'',group:owner?.group||'剧情'},options:[],condition:initialCondition(project,point.title)});
 }
 function targetFor(connection:{target:string|null;targetHandle?:string|null}){
  if(!connection.target)return undefined;
  if(connection.target.startsWith('group:')){
   const entry=chapterModel(connection.target.slice(6)).entry;
   return entry&&connection.targetHandle==='chapter-entry:'+entry.sceneId?entry.sceneId:undefined;
  }
  return connection.targetHandle==='entry'&&sourceFlow.authoring?.targets.some(t=>t.id===connection.target&&!t.reason)?connection.target:undefined;
 }
 function chapterModel(group:string){const settings=project.ide as ChapterSettings|undefined;return chapterPorts(sourceFlow,group,id=>sceneTitle(project,id),{entry:settings?.chapterEntries?.[group],exit:settings?.chapterExitPoints?.[group]});}
 function sourcePoint(source:string|null,handle?:string|null){
  if(!source||!handle)return undefined;
  if(source.startsWith('group:')){
   const model=chapterModel(source.slice(6));
   if(handle.startsWith('chapter-exit:'))return model.exit?.point.id===handle.slice(13)?model.exit.point:undefined;
   return collapsed.includes(source.slice(6))?model.ports.find(port=>port.point.id===handle)?.point:undefined;
  }
  return pointsForNode(sourceFlow,source).find(point=>point.id===handle);
 }
 function validConnection(connection:{source:string|null;target:string|null;sourceHandle?:string|null;targetHandle?:string|null}){
  if(!connection.source||!targetFor(connection))return false;
  return !!sourcePoint(connection.source,connection.sourceHandle);
 }
 function creationContext(x:number,y:number,point?:FlowEditPoint,dropped?:CanvasPosition):CanvasMenu{
  const position=dropped||canvas.current?.screenToFlowPosition({x,y})||{x:0,y:0};
  const containing=canvas.current?.getNodes().find(n=>n.type==='group'&&!collapsed.includes(n.id.slice(6))&&position.x>=n.position.x&&position.y>=n.position.y&&position.x<=n.position.x+Number(n.style?.width||0)&&position.y<=n.position.y+Number(n.style?.height||0));
  const group=point?sourceFlow.nodes.find(n=>n.id===point.owner)?.group||'剧情':containing?.id.slice(6)||selectedGroup?.title||node?.group||'剧情';
  return {x:Math.max(8,Math.min(x,window.innerWidth-230)),y:Math.max(8,Math.min(y,window.innerHeight-190)),position:point&&!dropped?{x:position.x+330,y:position.y+100}:position,point,group};
 }
 function openPalette(x:number,y:number,point?:FlowEditPoint,dropped?:CanvasPosition){if(quick)return;setMenu(creationContext(x,y,point,dropped));setError('');}
 function vacantPosition(position:CanvasPosition){
  const all=canvas.current?.getNodes()||[];
  const boxes=all.filter(n=>n.type==='story').map(n=>{const parent=all.find(p=>p.id===n.parentId);return {x:n.position.x+(parent?.position.x||0),y:n.position.y+(parent?.position.y||0),width:n.measured?.width||282,height:n.measured?.height||220};});
  const free=(p:CanvasPosition)=>boxes.every(b=>p.x+340<=b.x||p.x>=b.x+b.width+28||p.y+400<=b.y||p.y>=b.y+b.height+28);
  if(free(position))return position;
  for(let ring=1;ring<=12;ring++)for(const [x,y] of [[1,0],[0,1],[-1,0],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]]){const p={x:position.x+x*360*ring,y:position.y+y*420*ring};if(free(p))return p;}
  return position;
 }
 function newBlock(kind:FlowBlockKind,context?:CanvasMenu){
  if(changing.current||quick)return;
  const bounds=canvasElement.current?.getBoundingClientRect();
  const ctx=context||creationContext((bounds?.left||0)+(bounds?.width||800)/2,(bounds?.top||0)+(bounds?.height||500)/2);
  setMenu(null);setError('');setQuickError('');setCollapsed(v=>v.filter(g=>g!==ctx.group));
  let title=kind==='scene'?'新剧情':kind==='choice'?'剧情分支':'',index=2;const base=title;
  while(project.nativeRenpy?.labels.some(l=>sceneTitle(project,l.id)===title))title=base+' '+index++;
  setQuick({kind,group:ctx.group,point:ctx.point,position:vacantPosition(ctx.position),scene:{...freshScene(project,ctx.group),title},options:kind==='choice'?['选项一','选项二']:[],condition:initialCondition(project)});
 }
 async function submitQuick(){
  if(!quick||changing.current)return;
  if(quick.kind!=='condition'&&!quick.scene.title.trim()||quick.options.some(text=>!text.trim()))return;
  const draft=quick;setQuickError('');
  try{
   const condition=conditionResult(project,draft.condition);
   if(draft.kind==='condition'&&condition.error){setQuickError(condition.error);return;}
   if(draft.edit)await graphChange({operation:'update_condition',point:draft.edit.id,condition:condition.expression,hashes:flowHashes(sourceFlow.authoring!.documents,[])},'已修改判断');
   else {
    const targets=draft.optionTargets?.map(name=>{if(name===null)return null;const match=project.nativeRenpy?.labels.find(label=>label.name===name&&sourceFlow.authoring?.targets.some(target=>target.id===label.id&&!target.reason));if(!match)throw new Error('目标剧情不存在或不可连接：'+name);return match.id;});
    await graphChange({operation:'create_block',kind:draft.kind,point:draft.point?.id,scene:{...draft.scene,title:draft.kind==='condition'?condition.title:draft.scene.title.trim()},condition:condition.expression,options:draft.options,targets,hashes:flowHashes(sourceFlow.authoring!.documents,[draft.scene])},draft.point?'已创建并连接后续':'已创建节点');
   }
   setQuick(null);setUnlinkedOnly(false);if(!draft.edit){setPendingScene(draft.scene.name);setPlacement({name:draft.scene.name,position:draft.position});}
  }catch(e){setQuickError(e instanceof Error?e.message:String(e));}
 }
 function clearConnection(){connectionRef.current=null;hoveredRef.current='';setConnecting(null);setHovered('');}
 async function graphChange(operation:Record<string,unknown>,message:string){
  if(changing.current)throw new Error('正在更新剧情图，请稍候。');
  changing.current=true;setGraphBusy(true);setError('');
  try{await onOperation('flow',operation);setSelectedEdges([]);setNotice(message+' · 未保存');}
  finally{changing.current=false;setGraphBusy(false);}
 }
 function connect(connection:Connection){
  if(changing.current||!validConnection(connection))return;
  const point=sourcePoint(connection.source,connection.sourceHandle),target=targetFor(connection);
  if(!point||!target||point.target===target)return;
  if(formsCycle(sourceFlow,point.owner,target)){showIntent('connect',point,target);return;}
  const from=connection.source.startsWith('group:')?connection.source.slice(6):sceneTitle(project,point.owner),to=connection.target.startsWith('group:')?connection.target.slice(6):sceneTitle(project,target);
  void graphChange({operation:'connect_exit',point:point.id,target,hashes:flowHashes(sourceFlow.authoring!.documents,[])},`已连接：${from} → ${to}`).catch(e=>setError(e.message));
 }
 function openContent(original:NativeFlowNode){
  if(detailed&&original.type!=='scene'){onSource(original.source);return;}
  if(original.conditionPoint){const point=sourceFlow.authoring?.points[original.conditionPoint];if(point)editCondition(point);return;}
  if(original.blockKind==='choice'||original.type==='choice'){
   const input=canvasElement.current?.querySelector<HTMLInputElement>(`.react-flow__node[data-id="${CSS.escape(original.id)}"] .flow-option-title`);
   if(input){input.focus({preventScroll:true});input.select();return;}
  }
  onScene(original.label);
 }
 function addOption(branchPoint:string){
  const point=sourceFlow.authoring?.points[branchPoint];if(!point)return;
  const count=point.options?.length||0;
  void graphChange({operation:'branch_exit',point:point.id,hashes:flowHashes(sourceFlow.authoring!.documents,[]),options:[{text:`新选项 ${count+1}`,destination:{kind:'pending'}}]},'已添加选项').catch(e=>setError(e.message));
 }
 async function renameOption(point:FlowEditPoint,text:string){
  try{await graphChange({operation:'rename_option',point:point.id,text,hashes:flowHashes(sourceFlow.authoring!.documents,[])},'已修改选项文字');}
  catch(e){setError(e instanceof Error?e.message:String(e));throw e;}
 }
 function disconnect(ids:string[]){
  if(!ids.length)return;
  void graphChange({operation:'disconnect_exits',points:ids,hashes:flowHashes(sourceFlow.authoring!.documents,[])},'已断开，等待连接').catch(e=>setError(e.message));
 }
 async function endOutlet(point:FlowEditPoint){setMenu(null);await graphChange({operation:'end_exits',points:[point.id],hashes:flowHashes(sourceFlow.authoring!.documents,[])},'已设为结束此段');}
 function insertAtNode(dragged:Node):InsertPreview|null{
  if(changing.current||selectedNodes.filter(id=>!id.startsWith('group:')).length>1||insertionProblem(sourceFlow,project,dragged.id))return null;
  const box=canvasElement.current?.querySelector<HTMLElement>(`.react-flow__node[data-id="${CSS.escape(dragged.id)}"]`)?.getBoundingClientRect();
  if(!box)return null;
  let best:InsertPreview|null=null,score=Infinity;
  for(const edge of flow.edges){
   const point=edge.editPoint?sourceFlow.authoring?.points[edge.editPoint]:undefined;
   if(!point||!pointsForNode(sourceFlow,edge.source).some(p=>p.id===point.id))continue;
   const path=canvasElement.current?.querySelector<SVGPathElement>(`.react-flow__edge[data-id="${CSS.escape(edge.id)}"] .react-flow__edge-path`);
   if(!path)continue;
   const bounds=path.getBoundingClientRect();
   if(bounds.right<box.left+box.width*.2||bounds.left>box.right-box.width*.2||bounds.bottom<box.top+box.height*.2||bounds.top>box.bottom-box.height*.2)continue;
   if(insertionProblem(sourceFlow,project,dragged.id,point))continue;
   const matrix=path.getScreenCTM();if(!matrix)continue;
   const length=path.getTotalLength(),samples=Math.min(300,Math.max(2,Math.ceil(length/12)));
   for(let i=0;i<=samples;i++){
    const p=path.getPointAtLength(length*i/samples).matrixTransform(matrix);
    if(p.x<box.left+box.width*.2||p.x>box.right-box.width*.2||p.y<box.top+box.height*.2||p.y>box.bottom-box.height*.2)continue;
    const distance=Math.hypot(p.x-box.left-box.width/2,p.y-box.top-box.height/2);
    if(distance<score){score=distance;const scene=sourceFlow.nodes.find(n=>n.id===dragged.id)!;best={edge:edge.id,point,scene:dragged.id,scenePoint:scene.editPoint!,message:`松开插入：${sceneTitle(project,point.owner)} → ${sceneTitle(project,dragged.id)} → ${point.target?sceneTitle(project,point.target):point.status==='pending'?'待连接':'结束此段'}`};}
   }
  }
  return best;
 }
 function previewInsertion(dragged:Node){
  if(performance.now()-lastDragCheck.current<60)return;
  cancelAnimationFrame(dragFrame.current);
  dragFrame.current=requestAnimationFrame(()=>{
   lastDragCheck.current=performance.now();const next=insertAtNode(dragged);
   setInsertPreview(current=>current?.edge===next?.edge&&current?.scene===next?.scene?current:next);
  });
 }
 async function stopNodeDrag(dragged:Node,moved:Node[]){
  cancelAnimationFrame(dragFrame.current);setInsertPreview(null);
  if(dragged.id.startsWith('group:')||dragged.id==='quick-draft')return;
  const candidate=insertAtNode(dragged),next={...positions};
  for(const n of moved.length?moved:[dragged])if(!n.id.startsWith('group:'))next[n.id]=n.position;
  setPositions(next);
  try{
   if(candidate)await graphChange({operation:'insert_existing',point:candidate.point.id,scene:candidate.scene,scenePoint:candidate.scenePoint,hashes:flowHashes(sourceFlow.authoring!.documents,[])},`已插入：${sceneTitle(project,candidate.point.owner)} → ${sceneTitle(project,candidate.scene)} → ${candidate.point.target?sceneTitle(project,candidate.point.target):candidate.point.status==='pending'?'待连接':'结束此段'}`);
   await onLayout(detailed?{detailFlowPositions:next,detailFlowLayoutVersion:5}:{storyFlowPositions:next,storyFlowLayoutVersion:5},!candidate);
  }catch(e){setError(e instanceof Error?e.message:String(e));}
 }
 async function arrange(){
  if(changing.current||quick)return;
  const measured=canvas.current?.getNodes()||[],chosen=selectedNodes.filter(id=>flow.nodes.some(n=>n.id===id));
  const subset=chosen.length>=2,group=node?.group||selectedGroup?.id;
  const groups=subset?flow.groups.filter(g=>flow.nodes.some(n=>n.group===g.id&&chosen.includes(n.id))):group?flow.groups.filter(g=>g.id===group):flow.groups;
  const next={...positions},nextDirections={...directions};
  const sizes=Object.fromEntries(measured.filter(n=>n.type==='story').map(n=>[n.id,{width:n.measured?.width||282,height:n.measured?.height||220}]));
  for(const g of groups){
   const part=subset?{...flow,nodes:flow.nodes.filter(n=>chosen.includes(n.id))}:flow;
   const layout=storyLayout(part,g.id,{direction:arrangeDirection,sizes});
   const originals=measured.filter(n=>n.parentId==='group:'+g.id&&chosen.includes(n.id));
   const anchor=subset&&originals.length?{x:Math.min(...originals.map(n=>n.position.x)),y:Math.min(...originals.map(n=>n.position.y))}:{x:24,y:66};
   for(const [id,position] of Object.entries(layout.positions))next[id]={x:position.x+anchor.x-24,y:position.y+anchor.y-66};
   if(!subset)nextDirections[g.id]=arrangeDirection;
  }
  try{
   await onLayout(detailed?{detailFlowPositions:next,detailFlowDirections:nextDirections,detailFlowLayoutVersion:5}:{storyFlowPositions:next,storyFlowDirections:nextDirections,storyFlowLayoutVersion:5},true);
   setPositions(next);setDirections(nextDirections);setNotice(`已${arrangeDirection==='horizontal'?'横向':'纵向'}整理${subset?'所选节点':group?'当前章节':'全部章节'}，可用 Ctrl+Z 撤销。`);
   requestAnimationFrame(()=>void canvas.current?.fitView({nodes:subset?chosen.map(id=>({id})):measured.filter(n=>n.type==='story'&&groups.some(g=>n.parentId==='group:'+g.id)),padding:.25,minZoom:.25,maxZoom:1}));
  }catch(e){setError(e instanceof Error?e.message:String(e));}
 }
 const layouts=useMemo(()=>new Map(flow.groups.map(g=>[g.id,storyLayout(flow,g.id,{direction:directions[g.id],sizes:measurements})])),[flow,directions,measurements]);
 function caption(text:string){try{const value=JSON.parse(text);return typeof value==='string'?value:text;}catch{return text.length>1&&["'",'"'].includes(text[0])&&text.at(-1)===text[0]?text.slice(1,-1):text;}}
 function displayTitle(n:NativeFlowNode){
  if(n.conditionPoint||n.blockKind==='condition'||n.type==='condition')return detailed?n.conditionExpression||n.title:conditionResult(project,initialCondition(project,n.conditionExpression||n.title)).title;
  if(n.type==='scene')return sceneTitle(project,n.label);
  return n.type==='choice'?'选项分支':n.type==='return'?'结束此段':n.type==='loop'?'循环判断':n.type==='call'?'子剧情':'自定义逻辑';
 }
 const chapterModels=useMemo(()=>new Map(flow.groups.map(g=>[g.id,chapterModel(g.id)])),[flow.groups,sourceFlow,project]);
 function setChapterEndpoint(group:string,key:keyof ChapterSettings,value:string){void onLayout({[key]:{...((project.ide as ChapterSettings)?.[key]||{}),[group]:value}},true).catch(e=>setError(e.message));}
 function connectChapters(from:string,to:string){const source=chapterModels.get(from),target=chapterModels.get(to);if(!source?.exit||!target?.entry){setError(source?.exitReason||target?.entryReason||'请先设置章节入口和出口');return;}connect({source:'group:'+from,sourceHandle:'chapter-exit:'+source.exit.point.id,target:'group:'+to,targetHandle:'chapter-entry:'+target.entry.sceneId});}
 function openChapter(group:string){const model=chapterModels.get(group);if(!model?.entry)return;setCollapsed(current=>current.filter(id=>id!==group));setFocusNode(model.entry.sceneId);setSelected(model.entry.sceneId);}
 const nodes=useMemo(()=>{
  const result:Node[]=[];
  const ordered=[...flow.groups].sort((a,b)=>{const rank=(title:string)=>title==='序章'?0:title.startsWith('第')?1:2;return rank(a.title)-rank(b.title);});
  const frames=new Map(ordered.map(g=>{const base=layouts.get(g.id)!;const children=flow.nodes.filter(n=>n.group===g.id);return [g.id,{width:Math.max(base.width,...children.map(n=>(positions[n.id]?.x||0)+330)),height:Math.max(base.height,...children.map(n=>(positions[n.id]?.y||0)+(n.optionPoints?.length?180+n.optionPoints.length*42:180)+40))}];}));
  const laneWidth=Math.max(320,...ordered.map(g=>collapsed.includes(g.id)?310:frames.get(g.id)!.width));
  let offset=20;
  for(const group of ordered){
   const children=flow.nodes.filter(n=>n.group===group.id),small=collapsed.includes(group.id),layout=layouts.get(group.id)!,frame=frames.get(group.id)!,model=chapterModels.get(group.id)!,width=small?310:frame.width,height=small?chapterCollapsedHeight(model):frame.height;
   const preferences=project.ide as ChapterSettings|undefined,configuredEntry=preferences?.chapterEntries?.[group.id]||'';
   const entryPreference=model.entries.find(entry=>entry.sceneId===configuredEntry||sourceFlow.nodes.find(n=>n.id===entry.sceneId)?.title===configuredEntry)?.sceneId||configuredEntry;
   result.push({id:'group:'+group.id,type:'group',measured:measurements['group:'+group.id],deletable:false,className:connecting&&small&&model.entry?'flow-chapter-connection-target'+(hovered==='group:'+group.id?' flow-connection-hover':''):undefined,data:{label:group.title+(small?` · ${children.filter(n=>n.type==='scene').length} 场景`:''),title:group.title,collapsed:small,busy:graphBusy,connecting:!!connecting,...model,entryPreference,exitPreference:preferences?.chapterExitPoints?.[group.id]||'',nextTitle:sourceFlow.nodes.find(n=>n.id===model.exit?.point.target)?.group,chapters:flow.groups.map(g=>({id:g.id,title:g.title,ready:!!chapterModels.get(g.id)?.entry})),onEntry:(id:string)=>setChapterEndpoint(group.id,'chapterEntries',sourceFlow.nodes.find(n=>n.id===id)?.title||id),onExit:(id:string)=>setChapterEndpoint(group.id,'chapterExitPoints',id),onNext:(id:string)=>connectChapters(group.id,id),onOpen:()=>openChapter(group.id),onToggle:()=>void toggle(group.id).catch(e=>setError(e.message))},position:{x:(laneWidth-width)/2,y:offset},selected:selectedNodes.includes('group:'+group.id),draggable:false,style:{background:'#1a33302e',border:'1px solid #35514d',width,height},selectable:true});
   offset+=height+64;
   if(small)continue;
   for(const n of children){
    const info=sceneInfo(project,n.label),scene=project.scenes.find(x=>x.id===n.label),isCondition=n.type==='condition'||n.blockKind==='condition';
    const summary=info?.summary||scene?.lines.find(line=>line.text.trim())?.text;
    result.push({id:n.id,type:'story',measured:measurements[n.id],deletable:false,selected:selectedNodes.includes(n.id),className:connecting?(sourceFlow.authoring?.targets.some(t=>t.id===n.id&&!t.reason)?'flow-connection-target'+(hovered===n.id?' flow-connection-hover':''):'flow-connection-blocked'):undefined,parentId:'group:'+group.id,
     data:{busy:graphBusy,connecting:!!connecting,onRename:renameOption,onCreate:(point:FlowEditPoint,x:number,y:number)=>openPalette(x,y,point),onConnect:(point:FlowEditPoint)=>showIntent('connect',point),onAddOption:n.branchPoint?()=>addOption(n.branchPoint!):undefined,targetable:!!sourceFlow.authoring?.targets.some(t=>t.id===n.id&&!t.reason),outputs:pointsForNode(sourceFlow,n.id),destination,
      content:<div className="flow-node-content" title={isCondition?'双击编辑条件':n.type==='scene'?'双击编辑内容':undefined}>
       <small>{n.blockKind==='choice'||n.type==='choice'?'选项':isCondition?'判断':n.type==='scene'?'剧情':n.type==='return'?'结束':'自定义逻辑'}</small>
       <strong>{displayTitle(n)}</strong>
       {n.type==='scene'&&!n.blockKind&&summary&&<small className="flow-scene-summary">{summary.slice(0,100)}</small>}
       {n.type==='scene'&&n.reachability==='disconnected'&&<em className="flow-unlinked">未接入主线</em>}
       {detailed&&<small className="flow-technical-caption">{n.title}</small>}
       {n.unresolved&&<span className="flow-custom-logic" title="包含需要在高级设置中查看的自定义逻辑">自定义逻辑</span>}
      </div>},position:positions[n.id]||layout.positions[n.id],sourcePosition:Position.Bottom,targetPosition:Position.Top,
     style:{background:selectedNodes.includes(n.id)?'#263f42':n.blockKind==='choice'||n.type==='choice'?'#29293c':isCondition?'#302e28':'#1a2733',color:'#e7f4ee',border:n.title===currentLabel?'2px solid #a6e8d0':isCondition?'1px solid #a38c5a':'1px solid #466b65',width:282,padding:14}});
   }
  }
  if(quick)result.push({id:'quick-draft',type:'quickCreate',measured:measurements['quick-draft'],deletable:false,draggable:false,selectable:false,position:quick.position,zIndex:1000,
   data:{kind:quick.kind,project,scene:quick.scene,options:quick.options,optionTargets:quick.optionTargets,condition:quick.condition,editing:!!quick.edit,busy:graphBusy,error:quickError,attached:!!quick.point,onScene:(scene:NewFlowScene)=>setQuick(v=>v?{...v,scene}:v),onOptions:(options:string[])=>setQuick(v=>v?{...v,options}:v),onOptionTargets:(optionTargets:(string|null)[])=>setQuick(v=>v?{...v,optionTargets}:v),onCondition:(condition:FlowConditionDraft)=>setQuick(v=>v?{...v,condition}:v),onSubmit:()=>void submitQuick(),onCancel:()=>{setQuick(null);setQuickError('');}},style:{width:320}});
  return result;
 },[flow,collapsed,positions,selectedNodes,currentLabel,layouts,project,detailed,sourceFlow,graphBusy,connecting,hovered,quick,quickError,measurements,chapterModels]);
 const quickKey=quick?'draft:'+(quick.edit?.id||'new'):'';
 useEffect(()=>{if(!quickKey)return;const frame=requestAnimationFrame(()=>void canvas.current?.fitView({nodes:[{id:'quick-draft'}],padding:.3,minZoom:.6,maxZoom:1}));return()=>cancelAnimationFrame(frame);},[quickKey]);
 const edges=useMemo(()=>flow.edges.map(e=>{
  const from=flow.nodes.find(n=>n.id===e.source),to=flow.nodes.find(n=>n.id===e.target);if(!from||!to)return null;
  const highlighted=insertPreview?.edge===e.id,point=e.editPoint?sourceFlow.authoring?.points[e.editPoint]:undefined;
  const foldedSource=collapsed.includes(from.group),foldedTarget=collapsed.includes(to.group),crossing=from.group!==to.group;
  const chapterSource=!detailed&&crossing&&!!point&&chapterModels.get(from.group)?.exit?.point.id===point.id;
  const entry=chapterModels.get(to.group)?.entry,chapterTarget=!detailed&&crossing&&entry?.sceneId===e.target;
  const source=foldedSource||chapterSource?'group:'+from.group:from.id,target=foldedTarget||chapterTarget?'group:'+to.group:to.id;
  if(source===target&&(source!==e.source||target!==e.target))return null;
  const editable=!!point&&(foldedSource?chapterModels.get(from.group)?.ports.some(p=>p.point.id===point.id):pointsForNode(sourceFlow,e.source).some(p=>p.id===point.id));
  return {id:e.id,selected:selectedEdges.includes(e.id),source,target,sourceHandle:chapterSource?'chapter-exit:'+point!.id:editable?point!.id:foldedSource?'display-source':'display',targetHandle:foldedTarget||chapterTarget?entry?.sceneId===e.target?'chapter-entry:'+entry.sceneId:'display-target':'entry',reconnectable:editable?'target' as const:false as const,deletable:editable&&!!point?.target,data:{point:editable?point!.id:undefined},label:caption(e.title)||(detailed?({call:'调用',return:'返回',continuation:'返回后继续'}[e.kind]||''):''),type:'smoothstep',markerEnd:{type:MarkerType.ArrowClosed},style:{stroke:highlighted?'#f4ce85':'#8fc5b5',strokeWidth:highlighted?4:1.5,strokeDasharray:['return','continuation'].includes(e.kind)?'6 5':undefined},labelStyle:{fill:'#bdd7cd',fontSize:11},labelBgStyle:{fill:'#10201e'}};
 }).filter((e):e is NonNullable<typeof e>=>!!e),[flow,collapsed,sourceFlow,selectedEdges,insertPreview,chapterModels,detailed]);
 useEffect(()=>{if(!focusGroup||collapsed.includes(focusGroup)||!canvas.current)return;const targets=nodes.filter(n=>n.parentId==='group:'+focusGroup).sort((a,b)=>a.position.y-b.position.y).slice(0,3);if(targets.length)void canvas.current.fitView({nodes:targets,padding:.2,minZoom:.65,maxZoom:1});setFocusGroup('');},[focusGroup,collapsed,nodes]);
 async function toggle(group:string){const next=collapsed.includes(group)?collapsed.filter(g=>g!==group):[...collapsed,group];setCollapsed(next);if(collapsed.includes(group))setFocusGroup(group);await onLayout({collapsedGroups:next,...(detailed?{detailFlowLayoutVersion:5}:{storyFlowLayoutVersion:5})});}
 useEffect(()=>{
  if(!placement)return;
  const created=nodes.find(n=>n.id===project.nativeRenpy?.labels.find(l=>l.name===placement.name)?.id);
  if(!created)return;
  const parent=nodes.find(n=>n.id===created.parentId),position={x:placement.position.x-(parent?.position.x||0),y:placement.position.y-(parent?.position.y||0)};
  const next={...positions,[created.id]:position};setPositions(next);setPlacement(null);setFocusGroup('');setFocusNode(created.id);
  void onLayout(detailed?{detailFlowPositions:next,detailFlowLayoutVersion:5}:{storyFlowPositions:next,storyFlowLayoutVersion:5}).catch(e=>setError(e.message));
 },[placement,nodes,project,positions,detailed,onLayout]);
 useEffect(()=>{
  if(!focusNode||!measurements[focusNode])return;
  let finalFrame=0;
  const firstFrame=requestAnimationFrame(()=>{finalFrame=requestAnimationFrame(()=>{void canvas.current?.fitView({nodes:[{id:focusNode}],padding:.5,minZoom:.6,maxZoom:1});setFocusNode('');});});
  return()=>{cancelAnimationFrame(firstFrame);cancelAnimationFrame(finalFrame);};
 },[focusNode,nodes,measurements]);
 return <div className="native-global-flow">
  <div className="view-heading"><div><h1>剧情总图</h1></div><div className="actions">
   <button className="primary" disabled={graphBusy||!!quick} onClick={event=>{const bounds=canvasElement.current?.getBoundingClientRect();setMenu({...creationContext((bounds?.left||0)+(bounds?.width||800)/2,(bounds?.top||0)+(bounds?.height||500)/2),x:Math.min(event.clientX,window.innerWidth-230),y:event.clientY+18});}}><Plus size={14}/>新建</button>
   <button disabled={graphBusy||!!quick} onClick={()=>void arrange()}>{selectedNodes.filter(id=>!id.startsWith('group:')).length>=2?'整理所选':'整理布局'}</button>
   <details className="flow-view-options"><summary aria-label="画布视图设置"><Settings2 size={14}/>视图</summary><div>
    <label><input type="checkbox" checked={unlinkedOnly} onChange={e=>{setUnlinkedOnly(e.target.checked);setSelected('');}}/>仅看未接入主线的剧情</label>
    <label>排列方向<select aria-label="整理方向" value={arrangeDirection} onChange={e=>setArrangeDirection(e.target.value as LayoutDirection)}><option value="vertical">纵向</option><option value="horizontal">横向</option></select></label>
    <label><input type="checkbox" checked={detailed} onChange={e=>{setDetailed(e.target.checked);setPositions(e.target.checked?(ide.detailFlowLayoutVersion===5?ide.detailFlowPositions||{}:{}):(ide.storyFlowLayoutVersion===5?ide.storyFlowPositions||{}:{}));setSelected('');}}/>源码结构</label>
    {!!sourceFlow.sourceCopies?.length&&<button onClick={()=>setCopiesOpen(true)}>查看剧本副本</button>}
   </div></details>
  </div></div>
  {error&&<div className="flow-connection-error" role="alert"><span>{error}</span><button className="icon-button" aria-label="关闭错误提示" onClick={()=>setError('')}><X size={13}/></button></div>}
  <div className="global-flow-body"><section className="global-flow-canvas" ref={canvasElement} tabIndex={0} onKeyDown={event=>{
   if(!event.altKey||!['ArrowDown','ArrowRight'].includes(event.key)||(event.target as HTMLElement).closest('input,textarea,select,[role=dialog]'))return;
   event.preventDefault();const outputs=node?pointsForNode(sourceFlow,node.id):[];
   if(outputs.length!==1){setConnectionFeedback({message:'请使用具体出口旁的＋'});return;}
   newBlock('scene',creationContext(0,0,outputs[0],nodePosition(node!.id)));
  }}>
   {insertPreview&&<p className="flow-canvas-hint" role="status">{insertPreview.message}</p>}
   {(connectionFeedback||notice)&&<div className="flow-connection-feedback" role="status"><span>{connectionFeedback?.message||notice}</span><button className="icon-button" aria-label="关闭提示" onClick={()=>{setConnectionFeedback(null);setNotice('');}}><X size={13}/></button></div>}
   {unlinkedOnly&&!flow.nodes.length&&<p className="flow-empty" role="status">没有未接入主线的剧情</p>}
<ReactFlow autoPanOnNodeFocus={false} key={detailed?'detail':'story'} onInit={instance=>{canvas.current=instance;if(layoutVersion!==5||!viewport){const targets=nodes.filter(n=>n.parentId).sort((a,b)=>a.position.y-b.position.y).slice(0,3);requestAnimationFrame(()=>void instance.fitView({nodes:targets.length?targets:nodes,padding:.25,minZoom:.55,maxZoom:1}));}}} nodes={nodes} edges={edges} nodeTypes={nodeTypes} minZoom={0.05} defaultViewport={layoutVersion===5?viewport:undefined} fitView={false} onNodesChange={changes=>{if(changes.some(c=>c.type==='dimensions'&&c.dimensions))setMeasurements(current=>{let next=current;for(const c of changes)if(c.type==='dimensions'&&c.dimensions&&(current[c.id]?.width!==c.dimensions.width||current[c.id]?.height!==c.dimensions.height))next={...next,[c.id]:c.dimensions};return next;});const selection=changes.find(c=>c.type==='select'&&c.selected);if(selection?.type==='select')setSelected(selection.id);if(changes.some(change=>change.type==='select'))setSelectedNodes(current=>{const next=new Set(current);for(const change of changes)if(change.type==='select'){if(change.selected)next.add(change.id);else next.delete(change.id);}return next.size===current.length&&current.every(id=>next.has(id))?current:[...next];});setPositions(current=>{let next=current;for(const c of changes)if(c.type==='position'&&c.position&&!c.id.startsWith('group:')&&(current[c.id]?.x!==c.position.x||current[c.id]?.y!==c.position.y)){next={...next,[c.id]:c.position};}return next;});}} nodesConnectable={!graphBusy} deleteKeyCode={['Backspace','Delete']} isValidConnection={connection=>validConnection(connection)} onConnectStart={(_,params)=>{setConnectionFeedback(null);connectionRef.current=params.handleId||null;setConnecting(params.handleId||null);setHovered('');hoveredRef.current='';}} onReconnectStart={(_,edge,type)=>{setConnectionFeedback(null);if(type==='target'&&typeof edge.data?.point==='string'){connectionRef.current=edge.data.point;setConnecting(edge.data.point);}}} onReconnectEnd={()=>clearConnection()} onNodeMouseEnter={(_,n)=>{if(connectionRef.current){hoveredRef.current=n.id;setHovered(n.id);}}} onNodeMouseLeave={(_,n)=>{if(hoveredRef.current===n.id){hoveredRef.current='';setHovered('');}}} connectionRadius={40} nodesDraggable={!graphBusy} onConnect={connect} onReconnect={(edge,connection)=>{const point=edge.data?.point;const sourceHandle=edge.sourceHandle||String(point||'');if(typeof point==='string'&&validConnection({...connection,sourceHandle}))connect({...connection,sourceHandle});}} zoomOnDoubleClick={false} onNodeClick={(event,n)=>{setSelected(n.id);if(!event.ctrlKey&&!event.metaKey&&!event.shiftKey)setSelectedNodes(current=>current.length===1&&current[0]===n.id?current:[n.id]);setSelectedEdges([]);}} onPaneClick={event=>{setConnectionFeedback(null);setSelected('');setSelectedNodes([]);setSelectedEdges([]);if(event.detail===2&&!quick)openPalette(event.clientX,event.clientY);else setMenu(null);}} onPaneContextMenu={event=>{event.preventDefault();if(quick)return;openPalette(event.clientX,event.clientY);}} onConnectEnd={(event,state)=>{const over=hoveredRef.current;clearConnection();if(state.isValid)return;if(state.toNode||over){const id=state.toNode?.id||over;setConnectionFeedback({message:id.startsWith('group:')?chapterModels.get(id.slice(6))?.entry?'请拖到章节顶部的入口圆点':chapterModels.get(id.slice(6))?.entryReason||'请先设置章节入口':sourceFlow.authoring?.targets.find(t=>t.id===id)?.reason||'此处无法连接'});return;}if(state.fromHandle?.type!=='source'||!state.fromHandle.id)return;const point=sourcePoint(state.fromNode?.id||null,state.fromHandle.id);if(!point||!point.actions.includes('connect'))return;const cursor='changedTouches' in event?event.changedTouches[0]:event;if(cursor)openPalette(cursor.clientX,cursor.clientY,point,canvas.current?.screenToFlowPosition({x:cursor.clientX,y:cursor.clientY}));}} onEdgesChange={changes=>setSelectedEdges(current=>{const next=new Set(current);for(const change of changes)if(change.type==='select'){if(change.selected)next.add(change.id);else next.delete(change.id);}return [...next];})} onEdgesDelete={deleted=>disconnect(deleted.flatMap(e=>typeof e.data?.point==='string'?[e.data.point]:[]))} onNodeDoubleClick={(_,n)=>{if(n.id.startsWith('group:'))void toggle(n.id.slice(6)).catch(e=>setError(e.message));else{const original=flow.nodes.find(x=>x.id===n.id);if(original)openContent(original);}}} onNodeDragStart={()=>{lastDragCheck.current=0;}} onNodeDrag={(_,n)=>previewInsertion(n)} onNodeDragStop={(_,n,moved)=>void stopNodeDrag(n,moved)} onMoveEnd={(event,nextViewport)=>{if(event)void onLayout(detailed?{detailFlowViewport:nextViewport,detailFlowLayoutVersion:5}:{storyFlowViewport:nextViewport,storyFlowLayoutVersion:5}).catch(e=>setError(e.message));}}><Background color="#263f43"/><Controls/><MiniMap/></ReactFlow>
  </section><DockPanel id="flow-inspector" title="节点信息" initialSize={300} minSize={240} initialCollapsed storageVersion={2}>
   <aside className="inspector flow-inspector">{node?<div className="inspector-body" key={node.id}>
    <header className="flow-inspector-identity"><Workflow size={22}/><h2>{displayTitle(node)}</h2></header>
    <div className="flow-primary-actions"><button onClick={()=>openContent(node)}>编辑内容</button><button onClick={()=>onPreview(project.nativeRenpy?.labels.find(l=>l.id===node.label)?.name||node.title)}><Play size={14}/>测试</button></div>
    {node.type==='scene'&&!node.blockKind&&<label>名称<input maxLength={120} defaultValue={sceneTitle(project,node.label)} onBlur={event=>{const title=event.target.value.trim();if(title&&title!==sceneTitle(project,node.label))void onLayout({sceneTitles:{...((project.ide as {sceneTitles?:Record<string,string>})?.sceneTitles||{}),[node.label]:title}}).catch(e=>setError(e.message));}}/></label>}
    <label>章节<input defaultValue={node.group} onBlur={event=>{const group=event.target.value.trim();if(group&&group!==node.group)void onLayout({flowGroups:{...((project.ide as {flowGroups?:Record<string,string>})?.flowGroups||{}),[node.label]:group}}).catch(e=>setError(e.message));}}/></label>
    <details className="flow-inspector-advanced"><summary><Code2 size={14}/><span>高级与源码</span><ChevronDown size={14}/></summary><div className="flow-source-details">
     <label>标签<code>{project.nativeRenpy?.labels.find(l=>l.id===node.label)?.name||node.title}</code></label>
     <label>位置<code>{node.source.path}:{node.source.line}</code></label>
     {node.conditionExpression&&<label>条件表达式<code>{node.conditionExpression}</code></label>}
     {node.blockedReason&&<p>{node.blockedReason}</p>}
     {node.reachability==='unknown'&&<p>包含无法静态确定的入口或跳转，主线连接状态待确认。</p>}
     <button onClick={()=>onSource(node.source)}>编辑源码</button>
     {!!node.calls?.length&&<div><strong>子剧情</strong>{node.calls.map(call=><button key={call.id} onClick={()=>{const target=sourceFlow.nodes.find(n=>n.id===call.target);if(target)onScene(target.label,{callerLabel:node.title,source:call.source});else onSource(call.source);}}>{call.target?sceneTitle(project,call.target):'自定义调用'}</button>)}</div>}
    </div></details>
   </div>:selectedGroup?<div className="inspector-body"><h2>{selectedGroup.title}</h2><button onClick={()=>void toggle(selectedGroup.id)}>{collapsed.includes(selectedGroup.id)?'展开章节':'折叠章节'}</button></div>:<div className="flow-inspector-empty"><Workflow size={28}/><strong>选择剧情块查看信息</strong></div>}</aside>
  </DockPanel></div>
  {copiesOpen&&<Modal title="剧本副本" onClose={()=>setCopiesOpen(false)}><div className="modal-body"><p>默认使用编号版</p>{sourceFlow.sourceCopies?.map(copy=><div className="flow-copy-row" key={copy.path}><button onClick={()=>{setCopiesOpen(false);onSource({path:copy.original,line:1});}}>原版 · {copy.original}</button><button onClick={()=>{setCopiesOpen(false);onSource({path:copy.path,line:1});}}>编号版 · {copy.path}</button></div>)}</div></Modal>}
  {intent&&<FlowAuthoringDialog mode="connect" point={intent.point} initialTarget={intent.target} flow={sourceFlow} project={project} onOperation={onOperation} onClose={()=>setIntent(null)} onComplete={result=>{setUnlinkedOnly(false);setNotice(result.message+' · 未保存');}}/>}
  {menu&&<div className="flow-create-menu" role="menu" aria-label="新建剧情节点" style={{left:menu.x,top:menu.y}} onKeyDown={event=>{if(event.key==='Escape')setMenu(null);}}>
   <strong>{menu.point?'添加后续':'新建'}</strong>
   <button autoFocus role="menuitem" onClick={()=>newBlock('scene',menu)}>剧情块</button>
   <button role="menuitem" onClick={()=>newBlock('choice',menu)}>选项分支</button>
   <button role="menuitem" onClick={()=>newBlock('condition',menu)}>条件判断</button>
   {menu.point&&<><hr/><button role="menuitem" onClick={()=>{showIntent('connect',menu.point!);setMenu(null);}}>连接已有剧情</button><button role="menuitem" onClick={()=>void endOutlet(menu.point!).catch(e=>setError(e.message))}>结束此段</button></>}
   <button role="menuitem" onClick={()=>setMenu(null)}>取消</button>
  </div>}
 </div>;
}
