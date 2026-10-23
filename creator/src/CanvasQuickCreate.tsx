import {useState} from 'react';
import type {Node,NodeProps} from '@xyflow/react';
import type {Project} from './types';
import type {NewFlowScene} from './flow-authoring';
import {globalStateChoices,visualCondition} from './flow-authoring';
import {sceneFieldErrors} from './creation-model';
import {preferredLabels} from './source-labels';
import {conditionResult,initialCondition,type FlowConditionDraft} from './flow-condition';
import './canvas-quick.css';

export type QuickCreateData={kind:'scene'|'choice'|'condition';project:Project;scene:NewFlowScene;options:string[];optionTargets?:(string|null)[];onOptionTargets?:(targets:(string|null)[])=>void;busy:boolean;error:string;attached:boolean;editing?:boolean;condition?:FlowConditionDraft;onCondition?:(condition:FlowConditionDraft)=>void;onScene:(scene:NewFlowScene)=>void;onOptions:(options:string[])=>void;onSubmit:()=>void;onCancel:()=>void;onAdvanced?:()=>void};

export default function CanvasQuickCreate({data}:NodeProps<Node<QuickCreateData,'quickCreate'>>){
 const [switchError,setSwitchError]=useState('');
 const [jsonOpen,setJsonOpen]=useState(false),[json,setJson]=useState<string|null>(null),[jsonError,setJsonError]=useState('');
 const targets=data.options.map((_,index)=>data.optionTargets?.[index]||null);
 const labels=preferredLabels(data.project);
 const targetErrors=data.kind==='choice'?targets.map((target,index)=>target&&labels.filter(label=>label.name===target).length!==1?`选项 ${index+1}：目标场景“${target}”不存在或有歧义。`:'').filter(Boolean):[];
 const jsonValue=json??JSON.stringify(data.options.map((text,index)=>({text,...(targets[index]?{target:targets[index]}:{})})),null,2);
 const condition=data.condition||initialCondition(data.project),result=conditionResult(data.project,condition);
 const states=globalStateChoices(data.project),selectedState=states.find(state=>state.name===condition.variable);
 const isCondition=data.kind==='condition',title=isCondition?result.title:data.scene.title;
 const fields=sceneFieldErrors(title,data.scene.name,data.scene.path,data.project.nativeRenpy?.labels||[]);
 const invalid=(!data.editing&&Object.values(fields).some(Boolean))||(isCondition?!!result.error:!title.trim())||(data.kind==='choice'&&(!data.options.length||data.options.some(text=>!text.trim())||!!jsonError||targetErrors.length>0));
 function updateCondition(patch:Partial<FlowConditionDraft>){setSwitchError('');data.onCondition?.({...condition,...patch});}
 function chooseState(name:string){
  const state=states.find(item=>item.name===name);
  updateCondition({variable:name,valueType:state?.type==='unknown'?'number':state?.type||'number',operator:state?.type==='boolean'||state?.type==='unknown'?'truthy':'==',value:state?.type==='boolean'?'true':state?.type==='string'?'':'0'});
 }
 function useVisualCondition(){
  const parsed=visualCondition(condition.expression,states);
  if(!parsed){setSwitchError('此表达式无法转换，请修正，或放弃表达式后重新选择。');return;}
  updateCondition({...parsed,custom:false});
 }
 function updateOptions(options:string[],nextTargets=targets){setJson(null);data.onOptions(options);data.onOptionTargets?.(options.map((_,index)=>nextTargets[index]||null));}
 function moveOption(index:number,offset:number){const next=[...data.options],nextTargets=[...targets];[next[index],next[index+offset]]=[next[index+offset],next[index]];[nextTargets[index],nextTargets[index+offset]]=[nextTargets[index+offset],nextTargets[index]];updateOptions(next,nextTargets);}
 function editJson(value:string){
  setJson(value);
  try{
   const parsed:unknown=JSON.parse(value);
   if(!Array.isArray(parsed)||!parsed.length)throw new Error('选项 JSON 需为至少包含一项的数组。');
   const rows=parsed.map((item:unknown)=>{
    if(!item||typeof item!=='object')throw new Error('每项需填写 text 文字，可选填 target 标签名。');
    const row=item as {text?:unknown;target?:unknown};
    if(typeof row.text!=='string'||row.target!=null&&typeof row.target!=='string')throw new Error('每项需填写 text 文字，可选填 target 标签名。');
    return {text:row.text,target:typeof row.target==='string'&&row.target.trim()?row.target.trim():null};
   });
   setJsonError('');data.onOptions(rows.map(row=>row.text));data.onOptionTargets?.(rows.map(row=>row.target));
  }catch(error){setJsonError(error instanceof SyntaxError?'选项 JSON 格式不正确，请修正或放弃修改。':error instanceof Error?error.message:String(error));}
 }
 return <form className="flow-quick-create nodrag nopan nowheel" aria-label={data.editing?'画布内编辑节点':'画布内新建节点'} onSubmit={event=>{event.preventDefault();if(!invalid&&!data.busy)data.onSubmit();}} onKeyDown={event=>{event.stopPropagation();if(event.key==='Escape'&&!data.busy){event.preventDefault();data.onCancel();}}}>
  <small>{isCondition?(data.editing?'修改条件':'条件判断'):data.kind==='choice'?'选项分支':'剧情块'}{!data.editing&&` · ${data.attached?'创建后自动连接':'独立创建'}`}</small>
  {isCondition?<div className="flow-quick-condition">
   <strong className="flow-quick-condition-title">{result.title}</strong>
   {!condition.custom&&<>
    <label>全局状态<select autoFocus aria-label="判断变量" value={condition.variable} disabled={data.busy} onChange={event=>chooseState(event.target.value)}><option value="">选择已有全局状态</option>{states.map(state=><option key={state.name} value={state.name}>{state.name}{state.type==='unknown'?' · 其他状态':''}</option>)}</select></label>
    {!states.length&&<small>没有可选状态，可在高级设置中填写条件。</small>}
    {selectedState&&<>
     <label>比较方式<select aria-label="比较方式" value={condition.operator} disabled={data.busy} onChange={event=>updateCondition({operator:event.target.value})}><option value="truthy">为真／已满足</option><option value="falsy">为假／未满足</option>{selectedState.type!=='unknown'&&<><option value="==">等于</option><option value="!=">不等于</option>{selectedState.type==='number'&&<><option value=">">大于</option><option value=">=">大于等于</option><option value="<">小于</option><option value="<=">小于等于</option></>}</>}</select></label>
     {!['truthy','falsy'].includes(condition.operator)&&<label>比较值{condition.valueType==='boolean'?<select aria-label="比较值" value={condition.value} disabled={data.busy} onChange={event=>updateCondition({value:event.target.value})}><option value="true">是</option><option value="false">否</option></select>:<input aria-label="比较值" type={condition.valueType==='number'?'number':'text'} step={condition.valueType==='number'?'any':undefined} value={condition.value} disabled={data.busy} onChange={event=>updateCondition({value:event.target.value})}/>}</label>}
    </>}
   </>}
   {condition.custom&&<small>已使用自定义条件</small>}
  </div>:<input autoFocus aria-label="剧情块名称" maxLength={120} value={data.scene.title} disabled={data.busy} onFocus={event=>event.currentTarget.select()} onChange={event=>data.onScene({...data.scene,title:event.target.value})}/>}
  {data.kind==='choice'&&<div className="flow-quick-options">{data.options.map((text,index)=><div className="flow-quick-option" key={index}><label>选项 {index+1}<input aria-label={`选项 ${index+1} 文字`} value={text} disabled={data.busy||!!jsonError} onChange={event=>updateOptions(data.options.map((value,i)=>i===index?event.target.value:value))}/></label><div className="flow-quick-row-actions"><button type="button" aria-label={`上移选项 ${index+1}`} disabled={data.busy||!!jsonError||index===0} onClick={()=>moveOption(index,-1)}>↑</button><button type="button" aria-label={`下移选项 ${index+1}`} disabled={data.busy||!!jsonError||index===data.options.length-1} onClick={()=>moveOption(index,1)}>↓</button><button type="button" aria-label={`删除选项 ${index+1}`} disabled={data.busy||!!jsonError||data.options.length===1} onClick={()=>updateOptions(data.options.filter((_,i)=>i!==index),targets.filter((_,i)=>i!==index))}>删除</button></div></div>)}<button type="button" disabled={data.busy||!!jsonError} onClick={()=>updateOptions([...data.options,`选项${data.options.length+1}`],[...targets,null])}>＋ 选项</button></div>}
  <details className="flow-quick-advanced"><summary>高级设置{(!data.editing&&(fields.name||fields.path))||jsonError||targetErrors.length?' · 需修正':''}</summary>
   {data.kind==='choice'&&(jsonOpen?<label>选项列表（JSON）<textarea aria-label="选项列表 JSON" rows={6} disabled={data.busy} aria-invalid={!!jsonError||targetErrors.length>0} value={jsonValue} onChange={event=>editJson(event.target.value)}/></label>:<button type="button" disabled={data.busy} onClick={()=>setJsonOpen(true)}>编辑选项 JSON</button>)}
   {isCondition&&<>
    {condition.custom?<><label>条件表达式<textarea aria-label="判断表达式" rows={3} value={condition.expression} disabled={data.busy} onChange={event=>updateCondition({expression:event.target.value})}/></label><button type="button" disabled={data.busy} onClick={useVisualCondition}>转为可视条件</button>{switchError&&<div className="creation-error" role="alert">{switchError}<button type="button" disabled={data.busy} onClick={()=>{setSwitchError('');data.onCondition?.(initialCondition(data.project));}}>放弃表达式，重新选择</button></div>}</>:<button type="button" disabled={data.busy} onClick={()=>updateCondition({custom:true,expression:result.expression||condition.expression})}>使用条件表达式</button>}
   </>}
   {!data.editing&&<><label>标签名称<input aria-label="标签名称" aria-invalid={!!fields.name} value={data.scene.name} disabled={data.busy} onChange={event=>data.onScene({...data.scene,name:event.target.value})}/></label>{fields.name&&<small className="creation-error">{fields.name}</small>}<label>源码文件<input aria-label="源码文件" aria-invalid={!!fields.path} value={data.scene.path} disabled={data.busy} onChange={event=>data.onScene({...data.scene,path:event.target.value})}/></label>{fields.path&&<small className="creation-error">{fields.path}</small>}</>}
  </details>
  {!data.editing&&(fields.name||fields.path)&&<p className="creation-error" role="alert">{fields.name||fields.path} 请在高级设置中修正。</p>}
  {jsonError&&<div className="creation-error" role="alert">{jsonError}<button type="button" disabled={data.busy} onClick={()=>{setJson(null);setJsonError('');}}>放弃 JSON 修改</button></div>}
  {targetErrors.map(message=><p className="creation-error" role="alert" key={message}>{message}</p>)}
  {isCondition&&result.error&&<p className="creation-error" role="status">{result.error}</p>}
  {data.error&&<p className="creation-error" role="alert">{data.error}</p>}
  <div className="flow-quick-actions"><button type="button" disabled={data.busy} onClick={data.onCancel}>取消</button><button className="primary" disabled={data.busy||invalid} type="submit">{data.busy?'正在更新…':data.editing?'应用':'创建'}</button></div>
 </form>;
}
