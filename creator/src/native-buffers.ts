import type {SourceDocument} from './native-types';
export type SourceBuffer={base:SourceDocument;value:string;origin?:'code'|'visual'};

// A save acknowledges its submitted value, never text typed while compilation ran.
export function reconcileSavedBuffers(current:Record<string,SourceBuffer>,documents:SourceDocument[],submitted:{path:string;content:string}[]){
 const next={...current};
 for(const document of documents){
  const latest=current[document.path],sent=submitted.find(d=>d.path===document.path);
  next[document.path]=latest&&sent&&latest.value!==sent.content?{...latest,base:document}:{base:document,value:document.content};
 }
 return next;
}
