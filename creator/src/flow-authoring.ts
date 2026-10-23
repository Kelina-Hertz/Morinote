import type {NativeFlow,FlowEditPoint,FlowFingerprint} from './native-types';
import type {Project,GlobalState} from './types';
import {newSceneLabel} from './creation-model';

export interface NewFlowScene {title:string;name:string;path:string;group:string}
export type FlowIntent='connect'|'insert'|'branch';
export type FlowBlockKind='scene'|'choice'|'condition';
export interface BranchRow {id:string;text:string;kind:'existing'|'new'|'return';target:string;scene:NewFlowScene}
const emptyHash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
export function freshScene(project:Project,group:string):NewFlowScene{return {title:'',name:newSceneLabel(project.nativeRenpy?.labels||[]),path:'game/creator_scenes.rpy',group};}
export function flowHashes(documents:Record<string,FlowFingerprint>,scenes:NewFlowScene[]){
 const hashes={...documents};for(const scene of scenes)if(!hashes[scene.path])hashes[scene.path]={hash:emptyHash,contentHash:emptyHash};return hashes;
}
export function formsCycle(flow:NativeFlow,owner:string,target:string){
 const pending=[target],seen=new Set<string>();
 while(pending.length){const id=pending.pop()!;if(id===owner)return true;if(seen.has(id))continue;seen.add(id);for(const edge of flow.edges)if(edge.source===id&&edge.kind!=='return')pending.push(edge.target);}
 return false;
}
export function pointsForNode(flow:NativeFlow,nodeId:string):FlowEditPoint[]{
 const node=flow.nodes.find(n=>n.id===nodeId),points=flow.authoring?.points||{};
 if(!node||node.type==='return')return [];
 return [...new Set([node.editPoint,...(node.optionPoints||[])].filter((id):id is string=>!!id))].flatMap(id=>points[id]?.actions.includes('connect')?[points[id]]:[]);
}

export function chapterTargets(flow:NativeFlow,group:string){
 const allowed=new Set(flow.authoring?.targets.filter(t=>!t.reason).map(t=>t.id));
 return flow.nodes.filter(n=>n.type==='scene'&&n.group===group&&allowed.has(n.id));
}

export function chapterExits(flow:NativeFlow,group:string){
 const owners=new Set(flow.nodes.filter(n=>n.type==='scene'&&n.group===group).map(n=>n.id));
 return Object.values(flow.authoring?.points||{}).filter(p=>owners.has(p.owner)&&p.actions.includes('connect')&&(!p.target||!owners.has(p.target)));
}

export function chapterConnectionEndpoints(flow:NativeFlow,connection:{from:string;to:string;point?:FlowEditPoint;target?:string}){
 const exits=connection.point?[connection.point]:chapterExits(flow,connection.from);
 const targets=chapterTargets(flow,connection.to).filter(n=>!connection.target||n.id===connection.target);
 const internal=new Set(flow.nodes.filter(n=>n.group===connection.to).map(n=>n.id));
 const entries=targets.filter(n=>!flow.edges.some(e=>e.target===n.id&&internal.has(e.source)&&!['call','return','continuation'].includes(e.kind)));
 return {exits,targets,point:exits.length===1?exits[0]:undefined,target:targets.length===1?targets[0]:entries.length===1?entries[0]:undefined};
}

export function insertionProblem(flow:NativeFlow,project:Project,scene:string,point?:FlowEditPoint){
 const node=flow.nodes.find(n=>n.id===scene),exit=node?.editPoint?flow.authoring?.points[node.editPoint]:undefined;
 if(node?.type!=='scene'||!exit||!['jump','return','fallthrough'].includes(exit.kind))return '只能自动插入具有单一简单出口的剧情块。';
 const label=project.nativeRenpy?.labels.find(l=>l.id===scene);
 if(!label||label.name==='start'||!project.nativeRenpy?.labels.some(l=>l.name==='start')&&project.graphs.find(g=>g.id===project.entryGraph)?.entry===scene)return '游戏入口不能作为中间剧情块插入。';
 const reason=flow.authoring?.targets.find(t=>t.id===scene)?.reason;if(reason)return reason;
 if(flow.edges.some(e=>e.target===scene))return '这个剧情块已有入口连接，拖动只调整位置。';
 if(point){
  if(scene===point.owner||scene===point.target)return '不能插入连线的来源或原目标。';
  if(exit.target&&exit.target!==point.target)return '这个剧情块已有其他后续，请先断开再插入。';
  if(formsCycle(flow,point.owner,scene))return '插入会形成循环，请使用连接操作明确设置。';
 }
 return '';
}

export function comparisonExpression(variable:string,operator:string,value:string,valueType:string){
 if(!/^(?:persistent\.)?[A-Za-z_]\w*$/.test(variable.trim()))throw new Error('请选择或填写已定义的剧情变量。');
 const name=variable.trim();
 if(operator==='truthy')return name;
 if(operator==='falsy')return `not ${name}`;
 if(!['==','!=','>','>=','<','<='].includes(operator))throw new Error('请选择比较方式。');
 let literal='';
 if(valueType==='number'){
  if(!value.trim()||!Number.isFinite(Number(value)))throw new Error('比较值需填写有效数字。');
  literal=String(Number(value));
 }else if(valueType==='boolean')literal=value==='true'?'True':'False';
 else literal=JSON.stringify(value);
 return `${name} ${operator} ${literal}`;
}

export function globalStateChoices(project:Project):GlobalState[]{
 const states=project.nativeRenpy?.globalStates??project.variables.filter(v=>v.scope!=='component').map(v=>({name:v.scope==='persistent'?'persistent.'+v.name:v.name,type:['boolean','number','string'].includes(v.type)?v.type as GlobalState['type']:'unknown' as const}));
 return [...states].sort((a,b)=>a.name.localeCompare(b.name,'zh-CN'));
}

export function visualCondition(expression:string,states:GlobalState[]){
 const match=expression.trim().match(/^(not\s+)?((?:persistent\.)?[A-Za-z_]\w*)(?:\s*(==|!=|>=|<=|>|<)\s*(.+))?$/);
 if(!match||match[1]&&match[3])return null;
 const state=states.find(s=>s.name===match[2]);if(!state)return null;
 const operator=match[3]||(match[1]?'falsy':'truthy');
 if(!match[3])return {variable:state.name,operator,value:'0',valueType:state.type==='unknown'?'number':state.type};
 const raw=match[4];let value='',valueType='';
 if(raw==='True'||raw==='False'){value=raw==='True'?'true':'false';valueType='boolean';}
 else if(/^-?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(raw)){value=String(Number(raw));valueType='number';}
 else {try{const parsed=JSON.parse(raw);if(typeof parsed!=='string')return null;value=parsed;valueType='string';}catch{return null;}}
 if(valueType!==state.type||valueType!=='number'&&!['==','!='].includes(operator))return null;
 return {variable:state.name,operator,value,valueType};
}
