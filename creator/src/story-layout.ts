import type {NativeFlow} from './native-types';

/** Directed ranks; DFS back edges remain visible but do not inflate ranks. */
export function storyLayout(flow:NativeFlow,group:string){
 const nodes=flow.nodes.filter(n=>n.group===group).sort((a,b)=>a.source.path.localeCompare(b.source.path)||a.source.line-b.source.line),ids=new Set(nodes.map(n=>n.id));
 const links=flow.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)&&!['return','continuation','call'].includes(e.kind));
 const state=new Map<string,number>(),backs=new Set<string>();
 function visit(id:string){state.set(id,1);for(const e of links.filter(e=>e.source===id)){if(state.get(e.target)===1)backs.add(e.id);else if(!state.has(e.target))visit(e.target);}state.set(id,2);}
 nodes.forEach(n=>{if(!state.has(n.id))visit(n.id);});
 const forward=links.filter(e=>!backs.has(e.id)),indegree=new Map(nodes.map(n=>[n.id,forward.filter(e=>e.target===n.id).length])),rank=new Map(nodes.map(n=>[n.id,0]));
 const queue=nodes.filter(n=>indegree.get(n.id)===0).map(n=>n.id);
 for(let i=0;i<queue.length;i++){const id=queue[i];for(const e of forward.filter(e=>e.source===id)){rank.set(e.target,Math.max(rank.get(e.target)!,rank.get(id)!+1));indegree.set(e.target,indegree.get(e.target)!-1);if(indegree.get(e.target)===0)queue.push(e.target);}}
 const rows=new Map<number,string[]>();for(const n of nodes){const r=rank.get(n.id)!;rows.set(r,[...(rows.get(r)||[]),n.id]);}
 const width=Math.max(1,...[...rows.values()].map(r=>r.length))*330+48;
 const positions:Record<string,{x:number;y:number}>={};
 for(const [r,row] of rows)row.forEach((id,i)=>{positions[id]={x:24+(width-48-row.length*330)/2+i*330,y:66+r*170};});
 return {positions,width,height:Math.max(230,(Math.max(0,...rows.keys())+1)*170+80),backs};
}
