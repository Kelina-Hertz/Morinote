import type { Audio, FlowNode, Graph, Kind, Line, Project, Scene, Visual } from './types';
export const uid=(prefix='id')=>`${prefix}_${crypto.randomUUID().replaceAll('-','').slice(0,12)}`;
export const copy=<T,>(value:T):T=>structuredClone(value);
export const silent=():Audio=>({music:{asset:'',volume:1,fadeout:.5,fadein:.8}});
export const emptyVisual=():Visual=>({background:'',sprites:[],transition:'none'});
export function effective<T extends 'visual'|'audio'>(lines:Line[],index:number,track:T):Line[T]{for(let i=index;i>=0;i--)if(lines[i][track]!==null)return lines[i][track];return null;}
export function segments(lines:Line[],track:'visual'|'audio'){const starts=lines.map((l,i)=>i===0||l[track]!==null?i:-1).filter(i=>i>=0);return starts.map((start,i)=>({start,end:starts[i+1]??lines.length,value:effective(lines,start,track)}));}
export function splitTrack(scene:Scene,index:number,track:'visual'|'audio'):Scene{const next=copy(scene);if(next.lines[index][track]===null){const value=effective(scene.lines,index,track);if(track==='visual')next.lines[index].visual=copy(value as Visual|null)||emptyVisual();else next.lines[index].audio=copy(value as Audio|null)||silent();}return next;}
export function insertLine(scene:Scene,index:number,kind:Kind):Scene{const next=copy(scene);next.lines.splice(index+1,0,{id:uid('line'),kind,speaker:'',text:'',autoWait:null,visual:null,audio:null,...(kind==='chat'?{phone:{title:'手机聊天'}}:{}),...(kind==='stage'?{duration:1}:{})});return next;}
export function removeLine(scene:Scene,index:number):Scene{const next=copy(scene);const removed=next.lines[index];if(next.lines[index+1]){if(next.lines[index+1].visual===null)next.lines[index+1].visual=copy(removed.visual);if(next.lines[index+1].audio===null)next.lines[index+1].audio=copy(removed.audio);}next.lines.splice(index,1);return next;}
export function textConnected(lines:Line[],index:number){if(index===0)return false;const a=lines[index-1],b=lines[index];if(b.kind==='chat'&&a.kind==='chat')return !b.phone?.title||!a.phone?.title||a.phone.title===b.phone.title;if(b.visual!==null||b.audio!==null)return false;return a.kind===b.kind&&(b.kind==='narration'||b.kind==='dialogue'&&a.speaker===b.speaker);}
export function defaultWait(text:string,speed=15){return Math.round(((15+text.length)/250*speed)*10)/10;}
export function nodeEdges(node:FlowNode):{target:string;label:string;handle:string}[]{if(node.type==='choice')return(node.options||[]).map(o=>({target:o.target,label:o.text,handle:o.id}));if(node.type==='condition')return[{target:node.yes||'',label:'满足',handle:'yes'},{target:node.no||'',label:'不满足',handle:'no'}];if(node.type==='component'&&node.resultRoutes)return Object.entries(node.resultRoutes).map(([label,target])=>({target,label,handle:label}));return node.next?[{target:node.next,label:node.type==='call'?'返回后':'',handle:'next'}]:[];}
export function ancestors(graphs:Graph[],graph:Graph):Graph[]{const result:Graph[]=[];let parent=graph.parent;const seen=new Set([graph.id]);while(parent){if(seen.has(parent))break;seen.add(parent);const g=graphs.find(x=>x.id===parent);if(!g)break;result.unshift(g);parent=g.parent;}return result;}
export function isDirty(project:Project|null,saved:Project|null){if(!project||!saved)return false;return JSON.stringify(project)!==JSON.stringify(saved);}
export function removeNode(graph:Graph,id:string):Graph{const next=copy(graph);next.nodes=next.nodes.filter(n=>n.id!==id).map(n=>({...n,next:n.next===id?undefined:n.next,yes:n.yes===id?'':n.yes,no:n.no===id?'':n.no,options:n.options?.filter(o=>o.target!==id),resultRoutes:n.resultRoutes?Object.fromEntries(Object.entries(n.resultRoutes).filter(([,target])=>target!==id)):undefined}));if(next.entry===id)next.entry=next.nodes[0]?.id||'';return next;}
export function sceneEntryState(project:Project,sceneId:string,track:'visual'|'audio'):{kind:'empty'|'known'|'varying';value:Visual|Audio|null}{
 const unknown='@runtime',states=new Map<string,Set<string>>(),queue:{graph:Graph;node:FlowNode;state:string}[]=[],entries=new Set<string>();
 function enqueue(graph:Graph|undefined,nodeId:string|undefined,state:string){if(!graph||!nodeId)return;const node=graph.nodes.find(n=>n.id===nodeId);if(!node)return;const key=`${graph.id}/${nodeId}`,seen=states.get(key)||new Set<string>();if(seen.has(state)||seen.has(unknown)&&seen.size>=12)return;if(seen.size>=12)state=unknown;seen.add(state);states.set(key,seen);queue.push({graph,node,state});}
 for(const graph of project.graphs.filter(g=>!g.parent))enqueue(graph,graph.entry,'null');
 const callers=project.graphs.flatMap(graph=>graph.nodes.filter(n=>n.type==='call').map(node=>({graph,node})));
 for(let count=0;queue.length&&count<10000;count++){
  const {graph,node,state}=queue.shift()!;let next=state;
  if(node.type==='scene'){
   if(node.scene===sceneId)entries.add(state);
   const scene=project.scenes.find(s=>s.id===node.scene);
   if(scene){for(const line of scene.lines)if(line[track]!==null)next=JSON.stringify(line[track]);}
  }
  if(node.type==='call'){const child=project.graphs.find(g=>g.id===node.target);enqueue(child,child?.entry,next);continue;}
  if(node.type==='return'){for(const caller of callers.filter(c=>c.node.target===graph.id))enqueue(caller.graph,caller.node.next,next);continue;}
  if(node.type==='component')next=unknown;
  for(const edge of nodeEdges(node))enqueue(graph,edge.target,next);
 }
 if(entries.size>1||entries.has(unknown))return{kind:'varying',value:null};
 const encoded=entries.values().next().value;if(!encoded||encoded==='null')return{kind:'empty',value:null};
 return{kind:'known',value:JSON.parse(encoded)};
}
