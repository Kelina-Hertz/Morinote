import type { CreatorAPI } from './types';
import {useSyncExternalStore} from 'react';
let tokenPromise:Promise<string>|null=null;
async function token(){
  if(!tokenPromise) tokenPromise=fetch('/api/bootstrap').then(async r=>{if(!r.ok)throw new Error('无法连接本地制作服务');return (await r.json()).token||'';}).catch(e=>{tokenPromise=null;throw e;});
  return tokenPromise;
}
const browser:CreatorAPI={
  async request<T>(path:string,body?:unknown):Promise<T>{const bearer=await token();const r=await fetch(path,{method:body===undefined?'GET':'POST',headers:{Authorization:`Bearer ${bearer}`,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw new Error(data.error||`请求失败 (${r.status})`);return data;},
  async pickFolder(){return window.prompt('项目文件夹的完整路径');},
  async pickFiles(){const value=window.prompt('本地文件的完整路径（多项使用换行分隔）');return value?.split('\n').map(x=>x.trim()).filter(Boolean)||[];},
  async mediaUrl(id){await token();return `/api/media?id=${encodeURIComponent(id)}`;}
};
const transport=window.creator||browser;
let projectSession='', revision=0;
const listeners=new Set<()=>void>();
export function useMediaRevision(){return useSyncExternalStore(callback=>{listeners.add(callback);return()=>listeners.delete(callback);},()=>projectSession+':'+revision);}
export function currentProjectSession(){return projectSession;}
export const api:CreatorAPI={...transport,
 async request<T>(path:string,body?:unknown):Promise<T>{
   const captured=projectSession;
   const route=body===undefined&&captured&&path!=='/api/project'?path+(path.includes('?')?'&':'?')+'projectSession='+captured:path;
   const payload=body===undefined?undefined:{...(body as object),...(captured?{projectSession:captured}:{})};
   const result=await transport.request<T>(route,payload);
   const value=result as unknown as {session?:string;project?:{revision:number}};
   if(captured!==projectSession)throw new Error('项目已切换，忽略旧项目响应。');
   const changed=!!value.session&&value.session!==projectSession;
   if(value.session)projectSession=value.session;
   if(value.project)revision=changed?value.project.revision:Math.max(revision,value.project.revision);
   if(value.session||value.project)listeners.forEach(fn=>fn());
   return result;
 },
 async mediaUrl(id:string){const base=await transport.mediaUrl!(id);return base+(base.includes('?')?'&':'?')+'projectSession='+projectSession+'&version='+revision;}
};
export const isDesktop=!!window.creator;
