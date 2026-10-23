import type {Project} from './types';

export function canonicalFile(file:string){return file.replaceAll('\\','/').replace(/ \(\d+\)(\.rpy)$/i,'$1');}

export function preferredLabels(project:Project){
 const labels=project.nativeRenpy?.labels||[],ids=project.nativeRenpy?.preferredLabelIds;
 if(!ids)return labels;
 const selected=new Set(ids);return labels.filter(label=>selected.has(label.id));
}

export function sourceLabel(project:Project,idOrName:string){
 const labels=project.nativeRenpy?.labels||[];
 return labels.find(label=>label.id===idOrName)||preferredLabels(project).find(label=>label.name===idOrName)||labels.find(label=>label.name===idOrName);
}
