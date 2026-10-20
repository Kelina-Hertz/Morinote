import type {Project} from './types';
import {sceneInfo} from './story-profile';

/** Display metadata only: execution and source lookup always use native labels. */
export function sceneTitle(project:Project,idOrName:string):string {
 const label=project.nativeRenpy?.labels.find(l=>l.id===idOrName||l.name===idOrName);
 if(!label)return idOrName;
 const titles=(project.ide as {sceneTitles?:Record<string,string>})?.sceneTitles;
 return titles?.[label.id]?.trim()||titles?.[label.name]?.trim()||sceneInfo(project,label.id)?.title||(label.name==='start'?'故事开场':label.name);
}
export function sceneOption(project:Project,idOrName:string):string {
 const label=project.nativeRenpy?.labels.find(l=>l.id===idOrName||l.name===idOrName),title=sceneTitle(project,idOrName);
 return label&&title!==label.name?`${title} · ${label.name}`:title;
}
