export interface AudioChannel {id:string;name:string;kind:string}
export interface AudioSource {path:string;line:number;endLine?:number;statement?:string}
export interface NativeCue {asset:string;volume:number;fadein?:number;fadeout?:number;nativeSource?:AudioSource;nativeUnknown?:string[]}
export interface NativeAudioState {nativeUnknown?:string[];nativeBoundary?:boolean;[key:string]:NativeCue|string[]|boolean|undefined}
export const defaultChannels:AudioChannel[]=[{id:'music',name:'BGM 1',kind:'bgm'},{id:'ambience',name:'环境音',kind:'ambience'},{id:'sound',name:'音效',kind:'sound'},{id:'voice',name:'语音',kind:'voice'}];
export function cueAt(audio:NativeAudioState|null,channel:string):NativeCue|undefined {const cue=audio?.[channel];return cue&&typeof cue==='object'&&!Array.isArray(cue)?cue:undefined;}
export function nextBgm(channels:AudioChannel[]):AudioChannel {let n=2;const used=new Set(channels.map(c=>c.id));while(used.has('creator_bgm_'+n))n++;return {id:'creator_bgm_'+n,name:'BGM '+n,kind:'bgm'};}
export function visibleChannels(channels:AudioChannel[],audio:NativeAudioState|null,extra:AudioChannel[]) {return [...channels,...extra].filter((c,i,all)=>all.findIndex(x=>x.id===c.id)===i&&(c.kind==='bgm'||cueAt(audio,c.id)||extra.some(e=>e.id===c.id))).sort((a,b)=>Number(b.kind==='bgm')-Number(a.kind==='bgm'));}
export function audioVolumeChanges(before:NativeAudioState|null,after:NativeAudioState|null,channels:AudioChannel[]) {return channels.flatMap(({id})=>{const a=cueAt(before,id),b=cueAt(after,id);return a?.asset&&a.asset===b?.asset&&!a.nativeUnknown&&!b.nativeUnknown&&a.volume!==b.volume?[{operation:'volume',channel:id,value:b.volume,base:a.volume}]:[];});}
