import type {Project} from './types';
import type {SourceLocation} from './native-types';
import {virtualStatus} from './virtual-assets';
import './source-merge.css';

export default function AssetUsage({project,id,source,onSource,onAsset}:{project:Project;id?:string;source?:SourceLocation;onSource?:(s:SourceLocation)=>void;onAsset?:(id:string)=>void}){
 const asset=project.assets.find(a=>a.id===id),entry=project.nativeAssetLibrary?.entries.find(a=>a.id===id);
 if(!asset)return null;
 return <span className="asset-usage-card"><span>{asset.name}</span>{entry&&entry.status!=='bound'&&<><b className="asset-missing">{virtualStatus[entry.status]}</b><small>{entry.requirement||asset.requirement||asset.name}</small></>}
  {entry?.binding&&<code>{entry.binding.key}</code>}
  {onAsset&&<button type="button" onClick={()=>onAsset(asset.id)}>素材详情</button>}
  {source&&onSource&&<button type="button" onClick={()=>onSource(source)}>使用处源码</button>}
  {entry?.source&&onSource&&<button type="button" onClick={()=>onSource(entry.source!)}>定义源码</button>}
 </span>;
}
