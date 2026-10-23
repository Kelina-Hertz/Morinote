import type {Project} from './types';
import type {TreeNode,WorkspaceIndex} from './native-types';
export const fileGroupNames=['剧情脚本','手机与通讯录','界面与主题','游戏配置','成就与番外','运行支持与测试','其他文件'];
export function groupedFiles(tree:TreeNode[],project:Project,index?:WorkspaceIndex|null):TreeNode[]{
 const overrides=(project.ide as {fileGroups?:Record<string,string>})?.fileGroups||{};
 const files:TreeNode[]=[];function walk(items:TreeNode[]){for(const item of items)if(item.children)walk(item.children);else files.push(item);}walk(tree);
 const groups=new Map(fileGroupNames.map(name=>[name,[] as TreeNode[]]));
 const storyFiles=new Set<string>(),configFiles=new Set(index?.config.groups.flatMap(group=>group.sources)||[]);
 for(const scene of project.scenes)for(const line of scene.lines)if(line.source?.file)storyFiles.add('game/'+line.source.file);
 const known:Record<string,string>={message:'手机与通讯录',message_system:'手机与通讯录',contact_system:'手机与通讯录',gui:'界面与主题',screens:'界面与主题','00_ui_sounds':'界面与主题',options:'游戏配置',settings:'游戏配置',achievements:'成就与番外',ova:'成就与番外',ova_script:'成就与番外',story_workflow_runtime:'运行支持与测试',_ui_qa:'运行支持与测试'};
 for(const file of files){const base=file.name.replace(/\.rpy$/,'');let group=overrides[file.path]||known[base];
  if(!group&&/^script_c\d/i.test(base))group='剧情脚本';
  if(!group&&storyFiles.has(file.path))group='剧情脚本';
  if(!group&&configFiles.has(file.path))group='游戏配置';
  if(!group||!groups.has(group))group='其他文件';groups.get(group)!.push(file);
 }
 return [...groups].filter(([,items])=>items.length).map(([name,children])=>({name,path:'purpose:'+name,children}));
}
