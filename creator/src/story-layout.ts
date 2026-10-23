import type {NativeFlow} from './native-types';

/** Directed ranks; DFS back edges remain visible but do not inflate ranks. */
export type LayoutDirection='vertical'|'horizontal';
export function storyLayout(flow:NativeFlow,group:string,options:{direction?:LayoutDirection;sizes?:Record<string,{width:number;height:number}>}={}){
 const nodes=flow.nodes.filter(n=>n.group===group).sort((a,b)=>a.source.path.localeCompare(b.source.path)||a.source.line-b.source.line),ids=new Set(nodes.map(n=>n.id));
 const links=flow.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)&&!['return','continuation','call'].includes(e.kind));
 const state=new Map<string,number>(),backs=new Set<string>();
 function visit(id:string){state.set(id,1);for(const e of links.filter(e=>e.source===id)){if(state.get(e.target)===1)backs.add(e.id);else if(!state.has(e.target))visit(e.target);}state.set(id,2);}
 nodes.forEach(n=>{if(!state.has(n.id))visit(n.id);});
 const forward=links.filter(e=>!backs.has(e.id)),indegree=new Map(nodes.map(n=>[n.id,forward.filter(e=>e.target===n.id).length])),rank=new Map(nodes.map(n=>[n.id,0]));
 const queue=nodes.filter(n=>indegree.get(n.id)===0).map(n=>n.id);
 for(let i=0;i<queue.length;i++){const id=queue[i];for(const e of forward.filter(e=>e.source===id)){rank.set(e.target,Math.max(rank.get(e.target)!,rank.get(id)!+1));indegree.set(e.target,indegree.get(e.target)!-1);if(indegree.get(e.target)===0)queue.push(e.target);}}
 const rows=new Map<number,string[]>();for(const n of nodes){const r=rank.get(n.id)!;rows.set(r,[...(rows.get(r)||[]),n.id]);}
 const size=(id:string)=>options.sizes?.[id]||{width:282,height:nodes.find(n=>n.id===id)?.optionPoints?.length?180+nodes.find(n=>n.id===id)!.optionPoints!.length*42:180};
 const ordered=[...rows].sort(([a],[b])=>a-b);
 const positions:Record<string,{x:number;y:number}>={};
 if(options.direction==='horizontal'){
  const height=Math.max(230,...ordered.map(([,row])=>row.reduce((sum,id)=>sum+size(id).height+55,0)+100));
  let x=24;
  for(const [,row] of ordered){
   let y=66;
   for(const id of row){positions[id]={x,y};y+=size(id).height+55;}
   x+=Math.max(282,...row.map(id=>size(id).width))+80;
  }
  return {positions,width:Math.max(378,x+24),height,backs};
 }
 const width=Math.max(330,...ordered.map(([,row])=>row.reduce((sum,id)=>sum+size(id).width+48,0)))+48;
 let y=66;
 for(const [,row] of ordered){
  const rowWidth=row.reduce((sum,id)=>sum+size(id).width+48,0);
  let x=24+(width-48-rowWidth)/2;
  for(const id of row){positions[id]={x,y};x+=size(id).width+48;}
  y+=Math.max(180,...row.map(id=>size(id).height))+65;
 }
 return {positions,width,height:Math.max(230,y+50),backs};
}
