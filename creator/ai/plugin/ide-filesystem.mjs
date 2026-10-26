// DSH filesystem contract, backed by the IDE's shared live-document broker.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {FileSystem,FsError} from '@deepseek-ai/dsh-fs';
export const name='morinote-filesystem';
const root=path.resolve(process.env.MORINOTE_WORKSPACE);
const knowledge=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../skills');
const inside=(base,file)=>file===base||file.startsWith(base+path.sep);
async function call(body,signal){const response=await fetch(process.env.MORINOTE_BRIDGE_URL+'/fs',{method:'POST',headers:{authorization:'Bearer '+process.env.MORINOTE_BRIDGE_TOKEN,'content-type':'application/json'},body:JSON.stringify(body),signal});const v=await response.json();if(!response.ok){const code=/FS_[A-Z_]+/.exec(v.error)?.[0]||'FS_IO_ERROR';throw new FsError(v.error,code);}return v;}
export default class IDEFileSystem extends FileSystem{
 constructor(ctx){super(ctx);}
 get sandboxMode(){return 'workspace-write';}
 async resolve(input,opts={}){opts.signal?.throwIfAborted();let absolute=path.resolve(opts.cwd||root,input),tail=[],probe=absolute;while(true){try{absolute=path.join(await fs.realpath(probe),...tail);break;}catch(error){if(error.code!=='ENOENT')throw new FsError(error.message,'FS_PERMISSION_DENIED');const parent=path.dirname(probe);if(parent===probe)throw new FsError('路径不存在','FS_NOT_FOUND');tail.unshift(path.basename(probe));probe=parent;}}
  if(!inside(root,absolute)&&!inside(knowledge,absolute))throw new FsError('不能访问工程之外的路径。','FS_SANDBOX_DENIED');if(inside(root,absolute)&&path.relative(root,absolute).split(path.sep).some(p=>['.git','.creator','cache','saves','__pycache__','node_modules'].includes(p.toLowerCase())))throw new FsError('不能访问编辑器内部目录。','FS_SANDBOX_DENIED');return {targetKey:absolute,displayPath:absolute};}
 processPath(t){return String(t.targetKey);}
 processPathFromHostPath(p){const resolved=path.resolve(p);return inside(root,resolved)||inside(knowledge,resolved)?resolved:undefined;}
 fileUrl(t){return pathToFileURL(this.processPath(t)).href;}
 contains(a,b){return inside(this.processPath(a),this.processPath(b));}
 relative(t){return path.relative(root,this.processPath(t)).split(path.sep).join('/');}
 async stat(t,signal){signal?.throwIfAborted();const p=this.processPath(t);let info;try{info=await fs.stat(p);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(info?.isDirectory())return {type:'directory',version:String(info.mtimeMs)};
  if(inside(knowledge,p))return info?{type:'file',size:info.size,version:String(info.mtimeMs)}:undefined;
  try{const d=await call({action:'read',path:this.relative(t)},signal);return d.exists?{type:'file',size:Buffer.byteLength(d.value),version:d.version}:undefined;}catch(error){if(info&&!/FS_STALE_VERSION/.test(error.message))return {type:'other',size:info.size,version:String(info.mtimeMs)};throw error;}}
 async lstat(p,opts={},signal){return this.stat(await this.resolve(p,{...opts,signal}),signal);}
 async readText(t,signal){if(inside(knowledge,this.processPath(t)))return fs.readFile(this.processPath(t),{encoding:'utf8',signal});const d=await call({action:'read',path:this.relative(t)},signal);if(!d.exists)throw new FsError('文件不存在','FS_NOT_FOUND');return d.value;}
 async streamText(t,signal){const content=await this.readText(t,signal);return (async function*(){yield content;})();}
 async readBytes(t,signal,maxBytes){const value=Buffer.from(await this.readText(t,signal));if(value.length>maxBytes)throw new FsError('文件过大','FS_TOO_LARGE');return value;}
 async readByteRange(t,range,signal){const value=Buffer.from(await this.readText(t,signal));return value.subarray(range.offset,range.offset+range.length);}
 async listDir(t,signal){const p=this.processPath(t);if(inside(knowledge,p)){const entries=await fs.readdir(p,{withFileTypes:true});return entries.map(e=>({name:e.name,type:e.isDirectory()?'directory':'file',target:{targetKey:path.join(p,e.name),displayPath:path.join(p,e.name)}}));}
  const state=await call({action:'tree'},signal),relative=this.relative(t);let items=state.tree;for(const part of relative?relative.split('/'):[]){items=items.find(n=>n.name===part)?.children||[];}const map=new Map(items.map(e=>[e.name,{name:e.name,type:e.children?'directory':e.text?'file':'other',target:{targetKey:path.join(p,e.name),displayPath:path.join(p,e.name)}}]));for(const d of state.documents){if(d.deleted)continue;const rel=path.relative(p,path.resolve(root,d.path));if(rel.startsWith('..')||path.isAbsolute(rel)||!rel)continue;const [name,...rest]=rel.split(path.sep);if(!map.has(name))map.set(name,{name,type:rest.length?'directory':'file',target:{targetKey:path.join(p,name),displayPath:path.join(p,name)}});}return [...map.values()].sort((a,b)=>a.name.localeCompare(b.name));}
 async writeText(t,content,expected,signal){if(inside(knowledge,this.processPath(t)))throw new FsError('随附指南只读','FS_SANDBOX_DENIED');return call({action:'write',path:this.relative(t),content,expected,callId:crypto.randomUUID()},signal);}
 async editText(t,edit,expected,signal){if(inside(knowledge,this.processPath(t)))throw new FsError('随附指南只读','FS_SANDBOX_DENIED');return call({action:'edit',path:this.relative(t),edit,expected,callId:crypto.randomUUID()},signal);}
}
