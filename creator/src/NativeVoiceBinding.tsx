import {useEffect,useRef,useState} from 'react';
import {Mic,Play,Square,X,Code2} from 'lucide-react';
import {api,useMediaRevision} from './api';
import type {Asset,VoiceBinding} from './types';
import type {SourceLocation} from './native-types';

let activePreview:HTMLAudioElement|null=null;

export default function NativeVoiceBinding({voice,asset,ordinal,prefill,onChoose,onRemove,onSource}:{voice?:VoiceBinding|null;asset?:Asset;ordinal:number;prefill:boolean;onChoose:()=>void;onRemove:()=>void;onSource:(source:SourceLocation)=>void}){
 const revision=useMediaRevision(),player=useRef<HTMLAudioElement|null>(null),request=useRef(0);
 const [playing,setPlaying]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState('');
 useEffect(()=>{setPlaying(false);setLoading(false);setError('');return()=>{
  request.current++;const audio=player.current;if(!audio)return;
  audio.onended=null;audio.onpause=null;audio.onerror=null;audio.pause();
  if(activePreview===audio)activePreview=null;player.current=null;
 };},[asset?.id,asset?.mediaAssetId,revision]);
 const editable=!prefill&&voice?.editable!==false;
 const media=asset?.mediaAssetId||(!asset?.virtual&&asset?.status==='ready'?asset.id:'');
 async function audition(){
  if(playing||loading){request.current++;player.current?.pause();setPlaying(false);setLoading(false);return;}
  if(!media)return;
  const serial=++request.current;setLoading(true);setError('');
  try{
   const url=await api.mediaUrl?.(media);if(serial!==request.current)return;
   if(!url)throw new Error('无法读取这条语音。');
   activePreview?.pause();const audio=new Audio(url);player.current=audio;activePreview=audio;
   audio.onended=audio.onpause=()=>{if(serial===request.current)setPlaying(false);};
   audio.onerror=()=>{if(serial===request.current){setPlaying(false);setError('语音无法播放，请检查素材。');}};
   await audio.play();if(serial===request.current)setPlaying(true);else audio.pause();
  }catch(e){if(serial===request.current)setError(e instanceof Error?e.message:String(e));}
  finally{if(serial===request.current)setLoading(false);}
 }
 const title=asset?.name||(voice?.command==='stop'?'本句静音':voice?.command==='sustain'?'延续上一句语音':voice?.filename||voice?.expression||'添加语音');
 const missing=!!voice&&voice.command!=='stop'&&voice.command!=='sustain'&&(!asset||asset.virtualStatus==='unbound'||asset.virtualStatus==='broken'||asset.status==='missing');
 return <div className="native-line-voice" aria-label={'第 '+ordinal+' 句语音'} onClick={e=>e.stopPropagation()}>
  <Mic size={13}/><span className="native-line-voice-label">Voice</span>
  <button className="native-line-voice-file" title={voice?.reason||title} disabled={!editable} onClick={onChoose}>{title}</button>
  {!!voice&&<><button aria-label={'试听第 '+ordinal+' 句语音'} title="试听语音" disabled={!media} onClick={()=>void audition()}>{playing||loading?<Square size={12}/>:<Play size={12}/>}</button><button aria-label={'移除第 '+ordinal+' 句语音'} title="移除语音" disabled={!editable} onClick={onRemove}><X size={12}/></button></>}
  {voice?.nativeSource&&<button aria-label={'打开第 '+ordinal+' 句语音源码'} title="语音源码" onClick={()=>onSource(voice.nativeSource!)}><Code2 size={12}/></button>}
  {missing&&<small>语音缺失</small>}{asset?.virtualStatus==='temporary'&&<small>缺失 · 暂用替代</small>}
  {prefill&&<small>预填消息</small>}{error&&<small role="alert">{error}</small>}
 </div>;
}
