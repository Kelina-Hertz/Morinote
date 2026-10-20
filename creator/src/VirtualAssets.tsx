import DockPanel from './DockPanel';
import {useEffect,useMemo,useState} from 'react';
import {Plus,RefreshCw,Search,Music2,Link2,Code2} from 'lucide-react';
import type {Asset,Project} from './types';
import type {NativeOperation,SourceLocation} from './native-types';
import {api} from './api';
import {Media,AudioPlayer} from './Assets';
import {Modal} from './ui';
import {assetTabs,defaultAssetTab,type AssetType} from './asset-types';
import {virtualStatus,type Binding,type VirtualEntry} from './virtual-assets';
import './virtual-assets.css';

interface Props {
 project:Project;onOperation?:NativeOperation;onRefresh:()=>Promise<void>;onSource:(source:SourceLocation)=>void;
 onPick?:(asset:Asset)=>void;pickKind?:string;initialType?:AssetType;initialMissingOnly?:boolean;initialSelectedId?:string;runtimeMode?:'file'|'image';
}
const audioTypes=new Set(['bgm','ambience','sound','voice']);
function Preview({asset}:{asset?:Asset}){if(asset?.virtual&&asset.virtualStatus==='bound'&&!asset.path)return <div className="media-placeholder"><Code2 size={22}/><small>原生显示对象</small><small>{asset.name}</small></div>;return asset?.kind==='audio'?<div className="audio-cover"><Music2/></div>:<Media asset={asset}/>;}

export default function VirtualAssets({project,onOperation,onRefresh,onSource,onPick,pickKind,initialType,initialMissingOnly=false,initialSelectedId,runtimeMode}:Props){
 const library=project.nativeAssetLibrary;
 const [tab,setTab]=useState<AssetType>(initialType||defaultAssetTab(pickKind)),[mode,setMode]=useState<'virtual'|'physical'>('virtual');
 const [search,setSearch]=useState(''),[role,setRole]=useState(''),[costume,setCostume]=useState(''),[expression,setExpression]=useState(''),[category,setCategory]=useState(''),[missing,setMissing]=useState(initialMissingOnly);
 const [selected,setSelected]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[creating,setCreating]=useState(false),[name,setName]=useState(''),[newType,setNewType]=useState<AssetType>(tab);
 const [bindingEntry,setBindingEntry]=useState<string|null>(null),[targetMode,setTargetMode]=useState<'label'|'file'>('label'),[targetSearch,setTargetSearch]=useState(''),[target,setTarget]=useState<Binding|null>(null),[temporary,setTemporary]=useState(false);
 const entries=library?.entries||[],resources=library?.resources||[];
 const assets=useMemo(()=>new Map(project.assets.map(a=>[a.id,a])),[project.assets]);
 const resourceMap=useMemo(()=>new Map(resources.map(a=>[a.id,a])),[resources]);
 useEffect(()=>{if(!initialSelectedId)return;const e=project.nativeAssetLibrary?.entries.find(v=>v.id===initialSelectedId);if(e){setSelected(e.id);setTab(e.type);setMode('virtual');setMissing(false);setSearch('');setRole('');setCostume('');setExpression('');setCategory('');}},[initialSelectedId,project.id]);
 const entry=entries.find(e=>e.id===selected),binding=entries.find(e=>e.id===bindingEntry);
 const categories=useMemo(()=>[...new Set(entries.flatMap(e=>{const parts=(e.category||'').split('/').filter(Boolean);return parts.map((_,i)=>parts.slice(0,i+1).join('/'));}))].sort((a,b)=>a.localeCompare(b)),[entries]);
 const typeAllowed=(type:AssetType)=>!pickKind||pickKind==='audio'?(!pickKind||audioTypes.has(type)):pickKind==='sprite'?type==='sprite':pickKind==='background'?['background','cg'].includes(type):!audioTypes.has(type);
 const filtered=entries.filter(e=>typeAllowed(e.type)&&(!runtimeMode||e.runtime.kind===(runtimeMode==='image'?'image':'file'))&&(missing?e.status!=='bound':e.type===tab)&&(!role||(e.character||'未分类')===role)&&(!costume||e.costume===costume)&&(!expression||e.expression===expression)&&(!category||e.category===category||e.category?.startsWith(category+'/'))&&`${e.name} ${e.runtime.key} ${e.character||''} ${e.requirement||''}`.toLowerCase().includes(search.toLowerCase()));
 const typed=entries.filter(e=>e.type===tab);
 async function operate(operation:Record<string,unknown>){
  if(!onOperation)throw new Error('请在项目素材库中更换素材。');
  if(library?.error){setMessage('请先在源码中修复素材表，当前保留上次可用索引。');throw new Error(library.error);}
  setBusy(true);setMessage('');
  try{await onOperation('assets',operation);}catch(error){setMessage(error instanceof Error?error.message:String(error));throw error;}finally{setBusy(false);}
 }
 const update=(e:VirtualEntry,field:string,value:string)=>{if(String(e[field as keyof VirtualEntry]||'')===value)return;void operate({operation:'update',id:e.id,values:{[field]:value}}).catch(()=>{});};
 async function scan(){setBusy(true);setMessage('');try{await api.request('/api/assets/scan',{});await onRefresh();}catch(error){setMessage(String((error as Error).message));}finally{setBusy(false);}}
 function bind(e:VirtualEntry){setBindingEntry(e.id);setTarget(null);setTargetSearch('');setTemporary(e.temporary);setTargetMode(e.runtime.kind==='image'?'label':'file');}
 function switchTab(type:AssetType){setTab(type);setMissing(false);setRole('');setCostume('');setExpression('');setCategory('');setSelected('');}
 const targetOptions=targetMode==='label'?(library?.labels||[]).filter(l=>`${l.key} ${resourceMap.get(l.asset||'')?.name||''}`.toLowerCase().includes(targetSearch.toLowerCase())):resources.filter(a=>(audioTypes.has(binding?.type||'')?(a.kind==='audio'):(a.kind!=='audio'))&&`${a.name} ${a.nativeGamePath}`.toLowerCase().includes(targetSearch.toLowerCase()));
 if(!library)return <div className="empty"><h3>建立虚拟素材索引</h3><button disabled={busy} onClick={()=>void scan()}>重新扫描工程</button>{message&&<p role="alert">{message}</p>}</div>;
 return <div className="native-library virtual-library" aria-busy={busy}>
  <DockPanel id="asset-filters" title="素材筛选" side="left" initialSize={180} minSize={140}><aside className="category-panel asset-type-panel"><strong>{project.title} · 素材</strong>
   <button className={missing?'active':''} onClick={()=>{setMissing(v=>!v);setMode('virtual');setRole('');setCostume('');setExpression('');setCategory('');}}>缺失 ({entries.filter(e=>e.status!=='bound').length})</button>
   {tab==='sprite'&&<div className="asset-role-tabs"><strong>角色</strong><button className={!role?'active':''} onClick={()=>{setRole('');setCostume('');setExpression('');}}>全部角色</button>{[...new Set(typed.map(e=>e.character||'未分类'))].map(r=><button className={role===r?'active':''} key={r} onClick={()=>{setRole(r);setCostume('');setExpression('');}}>{r}</button>)}</div>}
   <details open><summary>分类</summary><button className={!category?'active':''} onClick={()=>setCategory('')}>全部分类</button>{categories.map(path=><button key={path} className={category===path?'active':''} style={{paddingLeft:12+path.split('/').length*8}} title={path} onClick={()=>setCategory(path)}>{path.split('/').at(-1)}</button>)}</details>
  </aside></DockPanel>
  <section className="native-library-main">
   <nav className="asset-type-tabs" aria-label="素材类型">{assetTabs.filter(([id])=>typeAllowed(id)).map(([id,title])=><button key={id} className={tab===id?'active':''} onClick={()=>switchTab(id)}>{title}<small>{entries.filter(e=>e.type===id).length}</small></button>)}</nav>
   <div className="virtual-view-switch"><button className={mode==='virtual'?'active':''} onClick={()=>setMode('virtual')}>虚拟素材</button><button className={mode==='physical'?'active':''} onClick={()=>setMode('physical')}>实际资源 · 只读</button></div>
   <div className="library-toolbar"><label className="search"><Search size={14}/><input aria-label="搜索素材" placeholder={mode==='virtual'?'搜索名称、角色、标签或需求':'搜索实际文件路径'} value={search} onChange={e=>setSearch(e.target.value)}/></label>
    <button disabled={busy||!onOperation} onClick={()=>{setName('');setNewType(tab);setCreating(true);}}><Plus size={13}/>新建虚拟素材</button><button disabled={busy} onClick={()=>void scan()}><RefreshCw size={13}/>重新扫描</button>
   </div>
   {message&&<p className="virtual-error" role="alert">{message}</p>}
   {library.error&&<div className="virtual-error" role="alert">{library.error}<button onClick={()=>onSource({path:library.path,line:1})}>修复映射源码</button></div>}
   {mode==='virtual'&&<>
    {tab==='sprite'&&<div className="portrait-filters"><label>服饰<select value={costume} onChange={e=>setCostume(e.target.value)}><option value="">全部服饰</option>{[...new Set(typed.filter(e=>!role||e.character===role).map(e=>e.costume).filter(Boolean))].map(c=><option key={c}>{c}</option>)}</select></label><label>表情／差分<select value={expression} onChange={e=>setExpression(e.target.value)}><option value="">全部差分</option>{[...new Set(typed.filter(e=>(!role||(e.character||'未分类')===role)&&(!costume||e.costume===costume)).map(e=>e.expression).filter(Boolean))].map(x=><option key={x}>{x}</option>)}</select></label></div>}
    <div className={'asset-grid asset-grid-'+tab}>{filtered.map(e=><div className={'asset-card virtual-card '+(selected===e.id?'selected':'')} key={e.id}><button className="asset-preview" onClick={()=>{const asset=assets.get(e.id);if(onPick&&asset)onPick(asset);else setSelected(e.id);}}><Preview asset={assets.get(e.id)}/><b>{e.name}</b><small>{[e.character,e.costume,e.expression].filter(Boolean).join(' · ')||e.runtime.key}</small>{e.status!=='bound'&&<span className={'virtual-state '+e.status}>{virtualStatus[e.status]}</span>}{e.status!=='bound'&&<small>{e.requirement||e.name}</small>}</button>{audioTypes.has(e.type)&&e.mediaAssetId&&<AudioPlayer id={e.mediaAssetId}/>}<button className="virtual-bind-button" disabled={busy||!onOperation} onClick={()=>bind(e)}><Link2 size={12}/>{e.binding?'更换':'选择素材'}</button></div>)}</div>
    {!filtered.length&&<p className="empty-detail">暂无素材</p>}
   </>}
   {mode==='physical'&&<div className="asset-grid physical-resource-grid">{resources.filter(a=>(audioTypes.has(tab)?a.kind==='audio':a.kind!=='audio')&&`${a.name} ${a.nativeGamePath}`.toLowerCase().includes(search.toLowerCase())).map(a=><div className="asset-card" key={a.id}><div className="asset-preview"><Preview asset={a}/><b>{a.name}</b><code>{a.nativeGamePath}</code></div>{a.kind==='audio'&&<AudioPlayer id={a.id}/>}<small>{a.nativeAliases?.join(' / ')||'未声明图片标签'}</small></div>)}</div>}
  </section>
  {entry&&!onPick&&mode==='virtual'&&<DockPanel id="asset-inspector" title="素材详情" initialSize={280}><aside className="inspector virtual-inspector"><div className="panel-heading">虚拟素材</div><div className="inspector-body"><Preview asset={assets.get(entry.id)}/>{entry.status!=='bound'&&<strong className={'virtual-state '+entry.status}>{virtualStatus[entry.status]}</strong>}
   <label>名称<input key={entry.id+'name'+entry.name} defaultValue={entry.name} disabled={busy} onBlur={e=>update(entry,'name',e.target.value)}/></label>
   <label>类型<select disabled={busy} value={entry.type} onChange={e=>update(entry,'type',e.target.value)}>{assetTabs.filter(([id])=>audioTypes.has(id)===audioTypes.has(entry.type)).map(([id,title])=><option key={id} value={id}>{title}</option>)}</select></label>
   {(['character','costume','expression','category','requirement'] as const).map((field,i)=><label key={field}>{['角色','服饰','表情／差分','分类路径','具体需求'][i]}<input key={entry.id+field+entry[field]} defaultValue={entry[field]||''} disabled={busy} placeholder={field==='category'?'立绘/汐泉/日常服':undefined} onBlur={e=>update(entry,field,e.target.value)}/></label>)}
   <strong>运行标识</strong><code>{entry.runtime.key}</code><strong>当前素材</strong><code>{entry.binding?.key||'缺失 · 使用占位'}</code>{entry.status==='broken'&&<small>原素材不存在，使用占位。</small>}{entry.opaque&&<small>复杂定义 · 原引擎执行</small>}
   <button disabled={busy} onClick={()=>bind(entry)}>更换</button>
   {entry.fallbackAlias&&<button disabled={busy} onClick={()=>void operate({operation:'bind',id:entry.id,binding:{kind:'label',key:entry.fallbackAlias},temporary:true}).catch(()=>{})}>暂用 {entry.fallbackAlias}</button>}
   <button disabled={busy||!entry.binding} onClick={()=>void operate({operation:'unbind',id:entry.id}).catch(()=>{})}>移除素材，使用占位</button>
   {entry.source&&<><button disabled={busy} onClick={()=>void operate({operation:'original',id:entry.id}).catch(()=>{})}>恢复原定义</button><button onClick={()=>onSource(entry.source!)}><Code2 size={12}/>原声明源码</button></>}
   <button disabled={busy||entry.references.length>0} title={entry.references.length?'请先处理剧情和系统引用':undefined} onClick={()=>void operate({operation:'delete',id:entry.id}).then(()=>setSelected('')).catch(()=>{})}>删除虚拟条目</button>
   <strong>引用 ({entry.references.length})</strong>{entry.references.slice(0,100).map(ref=><button className="virtual-reference" key={ref.path+':'+ref.line} onClick={()=>onSource(ref)}><code>{ref.path}:{ref.line}</code><small>{ref.text}</small></button>)}
  </div></aside></DockPanel>}
  {creating&&<Modal title="新建虚拟素材" onClose={()=>{if(!busy)setCreating(false);}}><div className="modal-body"><label>名称<input autoFocus value={name} onChange={e=>setName(e.target.value)} placeholder="例如：汐泉／女仆装／害羞"/></label><label>类型<select value={newType} onChange={e=>setNewType(e.target.value as AssetType)}>{assetTabs.map(([id,title])=><option key={id} value={id}>{title}</option>)}</select></label>{message&&<p role="alert">{message}</p>}<button className="primary" disabled={busy||!name.trim()} onClick={()=>void operate({operation:'create',name,type:newType}).then(()=>{setCreating(false);switchTab(newType);}).catch(()=>{})}>创建</button></div></Modal>}
  {binding&&<Modal title={'更换 · '+binding.name} wide onClose={()=>{if(!busy)setBindingEntry(null);}}><div className="modal-body virtual-target-picker"><div className="virtual-view-switch">{binding.runtime.kind==='image'&&<button className={targetMode==='label'?'active':''} onClick={()=>{setTargetMode('label');setTarget(null);}}>已有图片标签</button>}<button className={targetMode==='file'?'active':''} onClick={()=>{setTargetMode('file');setTarget(null);}}>实际文件</button></div><input aria-label="搜索素材" placeholder="搜索标签或文件路径" value={targetSearch} onChange={e=>setTargetSearch(e.target.value)}/><div className="virtual-target-grid">{targetOptions.map(option=>{const isLabel='key' in option,key=isLabel?option.key:option.nativeGamePath,asset=isLabel?resourceMap.get(option.asset||''):option,selected=target?.kind===targetMode&&target.key===key;return <button className={'virtual-target '+(selected?'selected':'')} key={key} onClick={()=>setTarget({kind:targetMode,key})}><Preview asset={asset}/><b>{isLabel?option.key:option.name}</b><code>{isLabel?asset?.nativeGamePath||'原生显示对象':option.nativeGamePath}</code>{isLabel&&<small>{option.opaque?'复杂定义':Object.entries(option.props||{}).map(([k,v])=>k+' '+v).join(' · ')}</small>}</button>;})}</div><label className="virtual-temporary"><input type="checkbox" checked={temporary} onChange={e=>setTemporary(e.target.checked)}/>临时替代，保留原需求待补</label>{message&&<p role="alert">{message}</p>}<div className="modal-actions"><code>{target?.key||'请选择素材'}</code><button disabled={busy||!target} className="primary" onClick={()=>void operate({operation:'bind',id:binding.id,binding:target,temporary}).then(()=>setBindingEntry(null)).catch(()=>{})}>确定</button></div></div></Modal>}
 </div>;
}
