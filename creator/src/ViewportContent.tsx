import {useEffect,useLayoutEffect,useRef,useState,type ReactNode} from 'react';

/** Retain measured height and focused editors when taking distant controls out. */
export default function ViewportContent({children,estimate=170,keep=false,className=''}:{children:ReactNode;estimate?:number;keep?:boolean;className?:string}){
 const node=useRef<HTMLDivElement>(null),height=useRef(estimate),near=useRef(false),[visible,setVisible]=useState(false),[focused,setFocused]=useState(false);
 const mounted=visible||keep||focused;
 useEffect(()=>{
  const element=node.current!,root=element.closest('.web-timeline-scroll');
  const observer=new IntersectionObserver(entries=>{near.current=entries[0].isIntersecting;setVisible(near.current);},{root,rootMargin:'500px 0px'});
  // A sticky stage can sit outside its own segment's visible portion. Observe
  // the segment so its preview is ready anywhere along the shared track.
  observer.observe(element.classList.contains('web-segment-inner')?element.parentElement!:element);return()=>observer.disconnect();
 },[]);
 useLayoutEffect(()=>{
  if(!mounted)return;
  const element=node.current!,observer=new ResizeObserver(()=>{height.current=element.getBoundingClientRect().height;});
  height.current=element.getBoundingClientRect().height;observer.observe(element);return()=>observer.disconnect();
 },[mounted]);
 return <div ref={node} className={className} data-deferred={mounted?undefined:'true'} style={mounted?undefined:{height:height.current}} onFocusCapture={()=>setFocused(true)} onBlurCapture={e=>{if(!e.currentTarget.contains(e.relatedTarget))setFocused(false);}}>{mounted?children:null}</div>;
}
