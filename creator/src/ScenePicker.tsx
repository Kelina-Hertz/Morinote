import {useId,useState} from 'react';
import type {Project} from './types';
import {sceneChoices} from './creation-model';

export default function ScenePicker({project,value,onChange,label='目标场景',error,disabled=false,allowedIds}:{project:Project;value:string;onChange:(value:string)=>void;label?:string;error?:string;disabled?:boolean;allowedIds?:string[]}){
 const [search,setSearch]=useState(''),id=useId();
 const choices=sceneChoices(project),query=search.trim().toLocaleLowerCase();
 const filtered=choices.filter(c=>(!allowedIds||allowedIds.includes(c.label.id)||c.label.name===value)&&(c.label.name===value||`${c.caption} ${c.label.name} ${c.label.file}`.toLocaleLowerCase().includes(query)));
 return <div className="scene-picker"><label>{label}<input aria-label={'搜索'+label} type="search" value={search} disabled={disabled} placeholder="搜索场景名称…" onChange={e=>setSearch(e.target.value)}/><select aria-label={label} aria-invalid={!!error} aria-describedby={error?id:undefined} value={value} disabled={disabled} onChange={e=>onChange(e.target.value)}><option value="">请选择场景</option>{value&&!choices.some(c=>c.label.name===value)&&<option value={value} disabled>原场景已不存在 · {value}</option>}{filtered.map(c=><option key={c.label.id} value={c.label.name} disabled={c.ambiguous||!!allowedIds&&!allowedIds.includes(c.label.id)}>{c.caption}{c.ambiguous?'（标签重复，请先处理）':''}</option>)}</select></label>{!filtered.length&&<small>没有匹配的场景，试试其他名称。</small>}{error&&<small className="creation-error" id={id}>{error}</small>}</div>;
}
