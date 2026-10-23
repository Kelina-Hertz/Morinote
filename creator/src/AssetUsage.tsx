import type {Project} from './types';
import type {SourceLocation} from './native-types';
import {virtualStatus} from './virtual-assets';
import './source-merge.css';
import {TechnicalDetails} from './ui';

export default function AssetUsage({project,id,source,onSource,onAsset}:{project:Project;id?:string;source?:SourceLocation;onSource?:(s:SourceLocation)=>void;onAsset?:(id:string)=>void}){
 const asset=project.assets.find(a=>a.id===id),entry=project.nativeAssetLibrary?.entries.find(a=>a.id===id);
 if(!asset)return null;
 return <span className="asset-usage-card"><span>{asset.name}</span>{entry&&entry.status!=='bound'&&<><b className="asset-missing">{virtualStatus[entry.status]}</b><small>{entry.requirement||asset.requirement||asset.name}</small></>}
  {onAsset&&<button type="button" onClick={()=>onAsset(asset.id)}>素材详情</button>}
  {(entry?.binding||source&&onSource||entry?.source&&onSource)&&<TechnicalDetails title="使用详情">{entry?.binding&&<code>{entry.binding.key}</code>}
  {source&&onSource&&<button type="button" onClick={()=>onSource(source)}>使用处源码</button>}
  {entry?.source&&onSource&&<button type="button" onClick={()=>onSource(entry.source!)}>定义源码</button>}
 </TechnicalDetails>}
 </span>;
}
