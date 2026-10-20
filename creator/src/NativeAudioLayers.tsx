import {useState,useEffect} from 'react';
import {Music2,Plus} from 'lucide-react';
import type {Project} from './types';
import type {SourceLocation} from './native-types';
import AssetUsage from './AssetUsage';
import {AudioPlayer} from './Assets';
import {Modal} from './ui';
import {defaultChannels,cueAt,nextBgm,visibleChannels,type AudioChannel,type AudioSource,type NativeAudioState} from './native-audio';

function Parameter({label,title,value,max,onChange,disabled=false}:{label:string;title?:string;value:number;max:number;onChange:(value:number)=>void;disabled?:boolean}) {
 const [draft,setDraft]=useState(String(value));useEffect(()=>setDraft(String(value)),[value]);
 return <label>{title||label}<input aria-label={label} type="number" min={0} max={max} step={label.includes('音量')?1:.1} disabled={disabled} value={draft} onChange={e=>setDraft(e.target.value)} onBlur={()=>{const n=Number(draft);if(draft.trim()&&Number.isFinite(n)&&n>=0&&n<=max&&n!==value)onChange(n);else setDraft(String(value));}}/></label>;
}

export default function NativeAudioLayers({project,audio,extra,onAdd,onPick,onEdit,onStop,onSplit,onSource,onAsset}:{onSource?:(s:SourceLocation)=>void;onAsset?:(id:string)=>void;project:Project;audio:NativeAudioState|null;extra:AudioChannel[];onAdd:(channel:AudioChannel)=>void;onPick:(channel:string,source?:AudioSource)=>void;onEdit:(channel:string,source:AudioSource|undefined,property:string,value:number)=>void;onStop:(channel:string,source?:AudioSource)=>void;onSplit:(channel:string,volume:number)=>void}) {
 const channels=project.nativeRenpy?.audioChannels||defaultChannels;
 const layers=visibleChannels(channels,audio,extra);
 const [settings,setSettings]=useState<string|null>(null);
 const selected=layers.find(c=>c.id===settings),selectedCue=settings?cueAt(audio,settings):undefined,selectedAsset=project.assets.find(a=>a.id===selectedCue?.asset);
 return <div className="native-audio-layers">
  {audio?.nativeUnknown?.length&&<div className="web-unresolved">随路线变化</div>}
  {layers.map(channel=>{const cue=cueAt(audio,channel.id),asset=project.assets.find(a=>a.id===cue?.asset);return <section className="native-audio-layer" key={channel.id} aria-label={channel.name+' 音频层'}>
   <header><strong title={channel.id}>{channel.name}</strong><div><button aria-label={'设置 '+channel.name} onClick={()=>setSettings(channel.id)}>设置</button><button aria-label={'停止 '+channel.name} disabled={!asset} onClick={()=>onStop(channel.id,cue?.nativeUnknown?undefined:cue?.nativeSource)}>停止</button></div></header>
   <button className="web-music-name" aria-label={'选择 '+channel.name} onClick={()=>onPick(channel.id,cue?.nativeUnknown?undefined:cue?.nativeSource)}><Music2 size={16}/>{cue?.nativeUnknown?'随路线变化／选择音频':asset?.name||'静音／选择音频'}</button>
   <AssetUsage project={project} id={asset?.id} source={cue?.nativeSource} onSource={onSource} onAsset={onAsset}/><Parameter title="音量 (%)" label={channel.name+' 音量 (%)'} value={Math.round((cue?.volume??1)*100)} max={1000} disabled={!asset||!!cue?.nativeUnknown} onChange={n=>onEdit(channel.id,cue?.nativeSource,'volume',n/100)}/>
  </section>;})}
  <div className="native-audio-add"><button onClick={()=>onAdd(nextBgm([...channels,...extra]))}><Plus size={13}/>BGM 层</button>{defaultChannels.filter(c=>c.id!=='music'&&!layers.some(l=>l.id===c.id)).map(c=><button key={c.id} onClick={()=>onAdd(c)}>＋{c.name}</button>)}</div>
  {selected&&<Modal title={selected.name+' 设置'} onClose={()=>setSettings(null)}><div className="modal-body native-audio-settings"><small>{selected.id}</small><div className="web-fade-fields">{(['fadeout','fadein'] as const).map(p=><Parameter key={p} title={p==='fadeout'?'淡出 (秒)':'淡入 (秒)'} label={selected.name+(p==='fadeout'?' 淡出 (秒)':' 淡入 (秒)')} value={selectedCue?.[p]??(p==='fadeout'?.5:.8)} max={60} disabled={!selectedAsset||!!selectedCue?.nativeUnknown||selectedCue?.nativeSource?.statement?.trim().startsWith('$ renpy.music.set_volume')} onChange={n=>onEdit(selected.id,selectedCue?.nativeSource,p,n)}/>)}</div>{selectedAsset&&(!selectedAsset.virtual||selectedAsset.mediaAssetId)&&<AudioPlayer id={selectedAsset.mediaAssetId||selectedAsset.id}/>}<button disabled={!selectedAsset||!!selectedCue?.nativeUnknown} onClick={()=>{onSplit(selected.id,selectedCue?.volume??1);setSettings(null);}}>从所选句独立</button></div></Modal>}
 </div>;
}
