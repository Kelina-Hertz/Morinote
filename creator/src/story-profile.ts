import {sourceLabel} from './source-labels';
import type {Project} from './types';
import profile from '../backend/morinote_story.json';

type Entry={file:string;title:string;group?:string;role:string;summary?:string};
export function sceneInfo(project:Project,idOrName:string):Entry|undefined{
 const labels=project.nativeRenpy?.labels||[],names=new Set(labels.map(l=>l.name));
 if(!profile.signature.every(name=>names.has(name)))return;
 const label=sourceLabel(project,idOrName);if(!label)return;
 const entry=(profile.scenes as Record<string,Entry>)[label.name];
 return entry&&label.file.replaceAll('\\','/').split('/').at(-1)?.replace(/ \(\d+\)(\.rpy)$/i,'$1')===entry.file?entry:undefined;
}
