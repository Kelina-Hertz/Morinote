import {useState} from 'react';
import type {Project} from './types';
import type {FlowEditPoint,NativeFlow,NativeOperation} from './native-types';
import {Modal} from './ui';
import {sceneTitle} from './scene-titles';
import {sceneFieldErrors} from './creation-model';
import {comparisonExpression,flowHashes,freshScene,globalStateChoices,visualCondition,type FlowBlockKind,type NewFlowScene} from './flow-authoring';
import './creation-dialogs.css';

type Props={kind:FlowBlockKind;group:string;point?:FlowEditPoint;edit?:FlowEditPoint;initialScene?:NewFlowScene;initialOptions?:string[];flow:NativeFlow;project:Project;onOperation:NativeOperation;onClose:()=>void;onCreated:(name:string)=>void};
export default function FlowBlockDialog({kind,group,point,edit,initialScene,initialOptions,flow,project,onOperation,onClose,onCreated}:Props){
 const [scene,setScene]=useState(()=>initialScene||({...freshScene(project,group),title:kind==='choice'?'剧情分支':kind==='condition'?'条件判断':''}));
 const [options,setOptions]=useState(()=>(initialOptions||['选项一','选项二']).map(text=>({id:crypto.randomUUID(),text})));
 const states=globalStateChoices(project),initial=edit?visualCondition(edit.title,states):null;
 const [variable,setVariable]=useState(initial?.variable||''),[operator,setOperator]=useState(initial?.operator||'truthy'),[value,setValue]=useState(initial?.value||'0'),[valueType,setValueType]=useState(initial?.valueType||'number');
 const [custom,setCustom]=useState(!!edit&&!initial),[expression,setExpression]=useState(edit?.title||'');
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const fields=sceneFieldErrors(scene.title,scene.name,scene.path,project.nativeRenpy?.labels||[]),selectedState=states.find(state=>state.name===variable);
 function chooseState(name:string){const state=states.find(state=>state.name===name);setVariable(name);setValueType(state?.type==='unknown'?'number':state?.type||'number');setOperator(state?.type==='boolean'||state?.type==='unknown'?'truthy':'==');setValue(state?.type==='boolean'?'true':state?.type==='string'?'':'0');}
 let condition='',conditionError='';
 if(kind==='condition'){try{if(!custom&&!selectedState)throw new Error('请选择已有的全局状态。');condition=custom?expression.trim():comparisonExpression(variable,operator,value,valueType);if(!condition)conditionError='请填写判断条件。';}catch(e){conditionError=(e as Error).message;}}
 const valid=!!flow.authoring&&!busy&&(edit||!Object.values(fields).some(Boolean))&&(kind!=='condition'||!conditionError)&&(kind!=='choice'||options.length>0&&options.every(o=>o.text.trim()));
 function move(index:number,offset:number){setOptions(current=>{const next=[...current];[next[index],next[index+offset]]=[next[index+offset],next[index]];return next;});}
 async function submit(){
  if(!valid)return;setBusy(true);setError('');
  try{
   const hashes=flowHashes(flow.authoring!.documents,edit?[]:[scene]);
   if(edit)await onOperation('flow',{operation:'update_condition',point:edit.id,hashes,condition});
   else await onOperation('flow',{operation:'create_block',kind,point:point?.id,scene:{...scene,title:scene.title.trim()},hashes,options:options.map(o=>o.text),condition});
   onCreated(edit?'':scene.name);onClose();
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <Modal title={edit?'修改判断条件':{scene:'新建剧情块',choice:'新建选项分支',condition:'新建条件判断'}[kind]} onClose={()=>{if(!busy)onClose();}}><form className="modal-body creation-form" onSubmit={e=>{e.preventDefault();void submit();}}>
  {!edit&&<label>名称<input autoFocus aria-label="剧情块名称" maxLength={120} value={scene.title} disabled={busy} onChange={e=>setScene(s=>({...s,title:e.target.value}))}/></label>}
  {point&&<p className="creation-note">接在“{sceneTitle(project,point.owner)}{point.title?' · '+point.title:''}”之后。{point.target?kind==='scene'?'新剧情块保留原后续。':kind==='choice'?'第一项保留原后续，其余出口可稍后拖线。':'“是”出口保留原后续，“否”出口可稍后拖线。':'出口可以稍后拖线连接。'}</p>}
  {kind==='choice'&&<><p className="creation-note">先填写选项文字，创建后从每个选项出口拖线。未连接的选项会结束／返回。</p>{options.map((option,index)=><div className="flow-option-editor" key={option.id}><label>选项 {index+1}<input aria-label={`选项 ${index+1} 文字`} value={option.text} disabled={busy} onChange={e=>setOptions(rows=>rows.map(row=>row.id===option.id?{...row,text:e.target.value}:row))}/></label><div className="choice-row-actions"><button type="button" aria-label={`上移选项 ${index+1}`} disabled={busy||index===0} onClick={()=>move(index,-1)}>↑</button><button type="button" aria-label={`下移选项 ${index+1}`} disabled={busy||index===options.length-1} onClick={()=>move(index,1)}>↓</button><button type="button" disabled={busy||options.length===1} onClick={()=>setOptions(rows=>rows.filter(row=>row.id!==option.id))}>删除</button></div></div>)}<button type="button" disabled={busy} onClick={()=>setOptions(rows=>[...rows,{id:crypto.randomUUID(),text:`选项${rows.length+1}`}])}>＋ 添加选项</button></>}
  {kind==='condition'&&<>{!custom&&<>
   <label>全局状态<select aria-label="判断变量" value={variable} disabled={busy} onChange={e=>chooseState(e.target.value)}><option value="">选择已有全局状态</option>{states.map(state=><option key={state.name} value={state.name}>{state.name}{state.name.startsWith('persistent.')?' · 跨存档':''} · {({boolean:'是／否',number:'数字',string:'文字',unknown:'其他状态'} as const)[state.type]}</option>)}</select></label>
   {!states.length&&<p className="creation-note">工程中还没有可选的全局状态。已有的源码条件仍可在高级设置中填写。</p>}
   {selectedState&&<><label>比较方式<select aria-label="比较方式" value={operator} disabled={busy} onChange={e=>setOperator(e.target.value)}><option value="truthy">为真／已满足</option><option value="falsy">为假／未满足</option>{selectedState.type!=='unknown'&&<><option value="==">等于</option><option value="!=">不等于</option>{selectedState.type==='number'&&<><option value=">">大于</option><option value=">=">大于等于</option><option value="<">小于</option><option value="<=">小于等于</option></>}</>}</select></label>
   {!['truthy','falsy'].includes(operator)&&<label>比较值{valueType==='boolean'?<select aria-label="比较值" value={value} disabled={busy} onChange={e=>setValue(e.target.value)}><option value="true">是</option><option value="false">否</option></select>:<input aria-label="比较值" type={valueType==='number'?'number':'text'} step={valueType==='number'?'any':undefined} value={value} disabled={busy} onChange={e=>setValue(e.target.value)}/>}</label>}</>}
  </>}{conditionError&&<small className="creation-error">{conditionError}</small>}<p className="creation-note">创建后分别连接“是”和“否”出口；未连接的出口会结束／返回。</p></>}
  <details className="creation-advanced" open={custom||undefined}><summary>高级设置</summary>{kind==='condition'&&<><label className="flow-checkbox"><input type="checkbox" checked={custom} disabled={busy} onChange={e=>{setCustom(e.target.checked);if(e.target.checked)setExpression(condition||expression);}}/>直接填写条件表达式</label>{custom&&<label>条件表达式<textarea aria-label="判断表达式" rows={3} value={expression} disabled={busy} onChange={e=>setExpression(e.target.value)}/></label>}</>}{!edit&&<><label>标签名称<input value={scene.name} disabled={busy} onChange={e=>setScene(s=>({...s,name:e.target.value}))}/></label>{fields.name&&<small className="creation-error">{fields.name}</small>}<label>源码文件<input value={scene.path} disabled={busy} onChange={e=>setScene(s=>({...s,path:e.target.value}))}/></label>{fields.path&&<small className="creation-error">{fields.path}</small>}</>}</details>
  {error&&<p className="creation-error" role="alert">{error}</p>}<div className="creation-actions"><button type="button" disabled={busy} onClick={onClose}>取消</button><button className="primary" type="submit" disabled={!valid}>{busy?'正在更新…':edit?'应用判断条件':'创建到画布'}</button></div>
 </form></Modal>;
}
