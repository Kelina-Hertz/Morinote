import {useLayoutEffect,useRef,useState,type ReactNode} from 'react';
import './windowed-grid.css';

/** Fixed card slots keep scrolling stable while mounting only nearby rows. */
export default function WindowedGrid<T>({items,itemKey,render,className='',rowHeight=310,minWidth=155,resetKey=''}:{items:T[];itemKey:(item:T)=>string;render:(item:T)=>ReactNode;className?:string;rowHeight?:number;minWidth?:number;resetKey?:string}){
 const host=useRef<HTMLDivElement>(null);
 const [view,setView]=useState({width:0,height:600,top:0});
 const [focusedKey,setFocusedKey]=useState<string|null>(null);
 useLayoutEffect(()=>{
  const node=host.current!;
  const measure=()=>setView(v=>{const next={width:node.clientWidth,height:node.clientHeight,top:node.scrollTop};return v.width===next.width&&v.height===next.height&&v.top===next.top?v:next;});
  const observer=new ResizeObserver(measure);observer.observe(node);measure();
  node.addEventListener('scroll',measure,{passive:true});return()=>{observer.disconnect();node.removeEventListener('scroll',measure);};
 },[]);
 useLayoutEffect(()=>{host.current!.scrollTop=0;setView(v=>({...v,top:0}));},[resetKey]);
 const gap=12,columns=Math.max(1,Math.floor((view.width+gap)/(minWidth+gap))),pitch=rowHeight+gap;
 const rows=Math.ceil(items.length/columns),start=Math.max(0,Math.floor(view.top/pitch)-1),end=Math.min(rows,Math.ceil((view.top+view.height)/pitch)+1);
 const indices=Array.from({length:Math.max(0,end-start)*columns},(_,n)=>start*columns+n).filter(i=>i<items.length);
 const focused=focusedKey===null?-1:items.findIndex(item=>itemKey(item)===focusedKey);
 if(focused>=0&&!indices.includes(focused))indices.push(focused);
 return <div ref={host} className={'windowed-grid '+className} tabIndex={0} aria-label={`素材列表，共 ${items.length} 项`} onFocusCapture={e=>setFocusedKey((e.target as HTMLElement).closest<HTMLElement>('[data-windowed-key]')?.dataset.windowedKey??null)} onBlurCapture={e=>{if(!e.currentTarget.contains(e.relatedTarget))setFocusedKey(null);}}>
  <div className="windowed-grid-space" role="list" style={{height:Math.max(0,rows*pitch-gap)}}>
   {indices.sort((a,b)=>a-b).map(i=>{const item=items[i];return <div role="listitem" aria-posinset={i+1} aria-setsize={items.length} data-windowed-key={itemKey(item)} key={itemKey(item)} className="windowed-grid-item" style={{top:Math.floor(i/columns)*pitch,left:`calc(${i%columns} * (100% + ${gap}px) / ${columns})`,width:`calc((100% - ${(columns-1)*gap}px) / ${columns})`,height:rowHeight}}>{render(item)}</div>;})}
  </div>
 </div>;
}
