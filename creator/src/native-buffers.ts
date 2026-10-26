import type {SourceDocument} from './native-types';
export type SourceBuffer={base:SourceDocument;value:string;deleted?:boolean;origin?:'code'|'visual'};
export function bufferDirty(document:SourceBuffer){return document.deleted?document.base.exists:!document.base.exists||document.value!==document.base.content;}

// A save acknowledges its submitted value, never text typed while compilation ran.
export function reconcileSavedBuffers(current:Record<string,SourceBuffer>,documents:SourceDocument[],submitted:{path:string;content:string;delete?:boolean}[]){
 const next={...current};
 for(const document of documents){
  const latest=current[document.path],sent=submitted.find(d=>d.path===document.path);
  if(latest&&sent&&(latest.value!==sent.content||!!latest.deleted!==!!sent.delete))next[document.path]={...latest,base:document};
  else if(sent?.delete)delete next[document.path];
  else next[document.path]={base:document,value:document.content};
 }
 return next;
}
