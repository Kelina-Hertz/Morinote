import {sourceLabel,canonicalFile} from './source-labels';
import type {Project} from './types';
import {sceneInfo} from './story-profile';

/** Display metadata only: execution and source lookup always use native labels. */
export function sceneTitle(project:Project,idOrName:string):string {
 const label=sourceLabel(project,idOrName);
 if(!label)return idOrName;
 const titles=(project.ide as {sceneTitles?:Record<string,string>})?.sceneTitles;
 const prior=project.nativeRenpy?.labels.find(l=>l.name===label.name&&canonicalFile(l.file)===canonicalFile(label.file)&&titles?.[l.id]?.trim());
 return titles?.[label.id]?.trim()||titles?.[label.name]?.trim()||(prior?titles?.[prior.id]?.trim():undefined)||label.displayTitle||sceneInfo(project,label.id)?.title||(label.name==='start'?'故事开场':label.name);
}
export function sceneOption(project:Project,idOrName:string):string {
 const label=sourceLabel(project,idOrName),title=sceneTitle(project,idOrName);
 return label&&title!==label.name?`${title} · ${label.name}`:title;
}
