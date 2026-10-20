import {useEffect,useRef,useState,type CSSProperties,type PointerEvent as ReactPointerEvent} from 'react';
import {Image,Music2} from 'lucide-react';
import {useDockScope} from './DockPanel';

const defaults=[36,39,25];
export function useTrackColumns(){
 const key='creator:track-columns:v1:'+useDockScope();
 const [sizes,setSizes]=useState<number[]>(()=>{try{const v=JSON.parse(localStorage.getItem(key)||'null');if(Array.isArray(v)&&v.length===3&&v.every(x=>Number.isFinite(x)&&x>=10)&&Math.abs(v.reduce((a,b)=>a+b,0)-100)<.1)return v;}catch{}return [...defaults];});
 const [dragging,setDragging]=useState(false),head=useRef<HTMLDivElement>(null),drag=useRef<{index:number;x:number;width:number;sizes:number[]}|null>(null);
 useEffect(()=>{if(!dragging)try{localStorage.setItem(key,JSON.stringify(sizes));}catch{}},[key,sizes,dragging]);
 function adjust(index:number,delta:number,base=sizes){
  const next=[...base],value=Math.max(10,Math.min(base[index]+base[index+1]-10,base[index]+delta));
  next[index]=value;next[index+1]=base[index]+base[index+1]-value;setSizes(next);
 }
 function begin(e:ReactPointerEvent<HTMLDivElement>,index:number){if(e.button!==0)return;e.preventDefault();drag.current={index,x:e.clientX,width:head.current?.getBoundingClientRect().width||920,sizes:[...sizes]};e.currentTarget.setPointerCapture(e.pointerId);setDragging(true);}
 function move(e:ReactPointerEvent<HTMLDivElement>){const d=drag.current;if(d)adjust(d.index,(e.clientX-d.x)/d.width*100,d.sizes);}
 function finish(){drag.current=null;setDragging(false);}
 const style={'--web-cols':sizes.map(v=>`minmax(180px,${v}fr)`).join(' ')} as CSSProperties;
 const headings=<div className={'web-track-headings'+(dragging?' track-resizing':'')} ref={head}>{['文字轨','画面轨','音乐轨'].map((title,index)=><span key={title}>{index===1?<Image size={14}/>:index===2?<Music2 size={14}/>:null}{title}{index<2&&<div className="track-column-divider" role="separator" aria-label={'调整'+title+'宽度'} aria-orientation="vertical" aria-valuemin={10} aria-valuemax={90} aria-valuenow={Math.round(sizes[index])} tabIndex={0} title="拖动调整轨道宽度；双击恢复默认" onPointerDown={e=>begin(e,index)} onPointerMove={move} onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={finish} onDoubleClick={()=>setSizes([...defaults])} onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();adjust(index,e.key==='ArrowLeft'?-2:2);}}}/>}</span>)}</div>;
 return {style,headings};
}
