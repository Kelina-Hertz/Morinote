import type {Asset,Project} from './types';
export const assetTabs=[['sprite','立绘'],['background','背景'],['cg','CG'],['bgm','BGM'],['ambience','环境音'],['sound','音效'],['voice','语音'],['interface','界面'],['unknown','未分类']] as const;
export type AssetType=typeof assetTabs[number][0];
export function assetType(asset:Asset,project:Project):AssetType {
 const virtual=asset.virtualType;
 if(virtual&&assetTabs.some(([id])=>id===virtual))return virtual as AssetType;
 const explicit=(project.ide as {assetTypes?:Record<string,AssetType>})?.assetTypes?.[asset.id];
 if(explicit&&assetTabs.some(([id])=>id===explicit))return explicit;
 if(asset.kind==='sprite'||asset.kind==='background')return asset.kind;
 const path=asset.path.toLowerCase().replaceAll('\\','/');
 if(asset.kind==='audio') {
  if(/(?:^|\/)(?:bgm|music)(?:\/|[_ .-])/.test(path))return 'bgm';
  if(/(?:^|\/)(?:voice|cv)(?:\/|[_ .-])/.test(path))return 'voice';
  if(/(?:^|\/)(?:ambience|ambient)(?:\/|[_ .-])/.test(path))return 'ambience';
  if(/(?:^|\/)(?:se|sfx|sound)(?:\/|[_ .-])/.test(path))return 'sound';
 }
 if(asset.kind==='image'&&/(?:^|\/)(?:gui|ui)(?:\/)/.test(path))return 'interface';
 return 'unknown';
}
export function defaultAssetTab(kind?:string):AssetType {
 return kind==='audio'?'bgm':kind==='image'?'interface':assetTabs.some(([id])=>id===kind)?kind as AssetType:'sprite';
}
