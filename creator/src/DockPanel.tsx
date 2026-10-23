import {createContext,useContext,useEffect,useRef,useState,type ReactNode,type PointerEvent as ReactPointerEvent} from 'react';
import './dock-panel.css';

const DockContext=createContext('default');
export function useDockScope(){return useContext(DockContext);}
export function DockScope({scope,children}:{scope:string;children:ReactNode}){
 return <DockContext.Provider value={scope}>{children}</DockContext.Provider>;
}
type Layout={size:number;collapsed:boolean};
type Props={id:string;title:string;side?:'left'|'right'|'bottom';initialSize?:number;initialCollapsed?:boolean;storageVersion?:number;minSize?:number;children:ReactNode};

/** Editor-only layout, scoped to a project; no source or preview changes. */
export default function DockPanel(props:Props){
 const scope=useDockScope(),key='creator:dock:v'+(props.storageVersion??1)+':'+scope+':'+props.id;
 return <Panel key={key} storageKey={key} {...props}/>;
}
function Panel({storageKey:key,title,side='right',initialSize=260,initialCollapsed=false,minSize=160,children}:Props&{storageKey:string}){
 const read=():Layout=>{try{const v=JSON.parse(localStorage.getItem(key)||'null');if(v&&Number.isFinite(v.size))return {size:Math.max(minSize,Math.min(1200,v.size)),collapsed:!!v.collapsed};}catch{}return {size:initialSize,collapsed:initialCollapsed};};
 const [layout,setLayout]=useState<Layout>(read),[dragging,setDragging]=useState(false);
 const panel=useRef<HTMLDivElement>(null),drag=useRef<{start:number;size:number;max:number}|null>(null);
 useEffect(()=>{if(!dragging)try{localStorage.setItem(key,JSON.stringify(layout));}catch{}},[key,layout,dragging]);
 const vertical=side==='bottom',closeArrow=vertical?'▾':side==='left'?'◂':'▸',openArrow=vertical?'▴':side==='left'?'▸':'◂';
 function maximum(){
  const parent=panel.current?.parentElement;if(!parent)return 1200;
  const rect=parent.getBoundingClientRect();let occupied=0;
  for(const sibling of Array.from(parent.children)){
   if(sibling===panel.current)continue;
   const css=getComputedStyle(sibling),box=sibling.getBoundingClientRect();
   if(css.display==='none')continue;
   occupied+=sibling.classList.contains('dock-panel')?(vertical?box.height:box.width):(parseFloat(vertical?css.minHeight:css.minWidth)||0);
  }
  return Math.max(minSize,(vertical?rect.height:rect.width)-occupied-8);
 }
 function begin(e:ReactPointerEvent<HTMLDivElement>){
  if(e.button!==0)return;e.preventDefault();
  const rect=panel.current?.getBoundingClientRect();
  drag.current={start:vertical?e.clientY:e.clientX,size:layout.collapsed?0:(vertical?rect?.height:rect?.width)||layout.size,max:maximum()};
  e.currentTarget.setPointerCapture(e.pointerId);setDragging(true);
 }
 function move(e:ReactPointerEvent<HTMLDivElement>){
  const d=drag.current;if(!d)return;
  const delta=((vertical?e.clientY:e.clientX)-d.start)*(side==='left'?1:-1);
  if(Math.abs(delta)<4)return;
  const size=d.size+delta;
  setLayout(v=>({size:size<minSize/2?v.size:Math.max(minSize,Math.min(d.max,size)),collapsed:size<minSize/2}));
 }
 function finish(){drag.current=null;setDragging(false);}
 function toggle(){setLayout(v=>({...v,size:v.collapsed?Math.min(v.size,maximum()):v.size,collapsed:!v.collapsed}));}
 const size=layout.collapsed?18:layout.size;
 return <div ref={panel} className={'dock-panel dock-'+side+(layout.collapsed?' dock-collapsed':'')+(dragging?' dock-dragging':'')} style={{flexBasis:size,...(vertical?{height:size}:{width:size})}}>
  <div className="dock-content" hidden={layout.collapsed}>{children}</div>
  <div className="dock-divider" role="separator" aria-label={'调整'+title+(vertical?'高度':'宽度')} aria-orientation={vertical?'horizontal':'vertical'} aria-valuemin={0} aria-valuemax={1200} aria-valuenow={layout.collapsed?0:Math.round(layout.size)} tabIndex={0} title={'拖动调整'+title+'；双击收起或恢复'} onPointerDown={begin} onPointerMove={move} onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={finish} onDoubleClick={toggle} onKeyDown={e=>{
   if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}
   else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){
    e.preventDefault();const increase=vertical?e.key==='ArrowUp':side==='left'?e.key==='ArrowRight':e.key==='ArrowLeft';
    setLayout(v=>({collapsed:false,size:Math.max(minSize,Math.min(maximum(),v.size+(increase?20:-20)))}));
   }
  }}/>
  <button type="button" className="dock-toggle" title={(layout.collapsed?'拉出':'收起')+title} aria-label={(layout.collapsed?'拉出':'收起')+title} aria-expanded={!layout.collapsed} onClick={toggle}>{layout.collapsed?openArrow:closeArrow}</button>
 </div>;
}
