import type {FlowEditPoint,NativeFlow} from './native-types';

export interface ChapterPort {
 point:FlowEditPoint;
 caption:string;
 ownerCaption:string;
 targetCaption?:string;
}
export interface ChapterEntry {sceneId:string;caption:string}
export interface ChapterPorts {ports:ChapterPort[];entry?:ChapterEntry;entryReason:string;entries:ChapterEntry[];exit?:ChapterPort;exitReason:string}

/** Project real source exits onto a container; never invent a chapter-level exit. */
export function chapterPorts(flow:NativeFlow,group:string,caption?:(sceneId:string)=>string,preferences:{entry?:string;exit?:string}={}):ChapterPorts {
 const allScenes=flow.nodes.filter(node=>node.type==='scene'&&node.group===group);
 const allowed=new Set(flow.authoring?.targets.filter(target=>!target.reason).map(target=>target.id));
 const scenes=allScenes.filter(scene=>allowed.has(scene.id)).sort((a,b)=>a.source.path.localeCompare(b.source.path,undefined,{numeric:true})||a.source.line-b.source.line);
 const owners=new Set(allScenes.map(node=>node.id));
 const members=new Set(flow.nodes.filter(node=>node.group===group).map(node=>node.id));
 const name=(id:string)=>caption?.(id)||flow.nodes.find(node=>node.id===id)?.title||'未命名场景';
 const points=Object.values(flow.authoring?.points||{}).filter(point=>owners.has(point.owner)&&point.actions.includes('connect')&&(!point.target||!owners.has(point.target)));
 const ports=points.map(point=>({point,ownerCaption:name(point.owner),caption:point.title?`${name(point.owner)} · ${point.title}`:`${name(point.owner)} · 后续`,targetCaption:point.target?name(point.target):undefined}));
 const titles=new Map<string,number>();
 for(const port of ports)titles.set(port.caption,(titles.get(port.caption)||0)+1);
 const occurrence=new Map<string,number>();
 for(const port of ports)if((titles.get(port.caption)||0)>1){const title=port.caption,index=(occurrence.get(title)||0)+1;occurrence.set(title,index);port.caption=`${title} ${index}`;}
 // Calls/returns describe a stack continuation, not a chapter's story entrance.
 const links=flow.edges.filter(edge=>!['call','return','continuation'].includes(edge.kind));
 const roots=scenes.filter(scene=>!links.some(edge=>edge.target===scene.id&&members.has(edge.source)));
 const external=scenes.filter(scene=>links.some(edge=>edge.target===scene.id&&!members.has(edge.source)));
 const chosen=preferences.entry?scenes.find(scene=>scene.id===preferences.entry||scene.title===preferences.entry):external.length===1?external[0]:scenes.find(scene=>scene.title==='start')||roots[0];
 const unavailable=allScenes.find(scene=>!allowed.has(scene.id)&&!links.some(edge=>edge.target===scene.id&&members.has(edge.source)));
 const exit=preferences.exit?ports.find(port=>port.point.id===preferences.exit):ports.length===1?ports[0]:undefined;
 return {ports,entries:scenes.map(scene=>({sceneId:scene.id,caption:name(scene.id)})),entry:chosen?{sceneId:chosen.id,caption:name(chosen.id)}:undefined,
  entryReason:chosen?'':preferences.entry?'章节入口已失效，请重新选择':unavailable?flow.authoring?.targets.find(target=>target.id===unavailable.id)?.reason||'请选择章节入口':allScenes.length?'请选择章节入口':'章节中还没有场景',
  exit,exitReason:exit?'':preferences.exit?'后续出口已变化，请重新选择':ports.length?'请在入口设置中选择后续出口':'本章没有可安全连接的出口'};
}

export function chapterCollapsedHeight(model:Pick<ChapterPorts,'ports'|'entry'>&Partial<Pick<ChapterPorts,'exit'>>){return 124+model.ports.filter(port=>port.point.id!==model.exit?.point.id).length*48+(model.entry?0:18);}
