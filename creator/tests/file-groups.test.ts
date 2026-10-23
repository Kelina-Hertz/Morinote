import test from 'node:test';
import assert from 'node:assert/strict';
import {groupedFiles} from '../src/file-groups';
import type {Project} from '../src/types';
import type {WorkspaceIndex} from '../src/native-types';

test('file classification preserves explicit overrides, story and configuration priorities',()=>{
 const project={scenes:[{lines:[{source:{file:'story.rpy'}},{source:{file:'shared.rpy'}},{}]}],ide:{fileGroups:{'game/story.rpy':'其他文件'}}} as unknown as Project;
 const index={config:{groups:[{sources:['game/shared.rpy','game/config.rpy']}]}} as unknown as WorkspaceIndex;
 const paths=['story.rpy','shared.rpy','config.rpy','picture.png','screens.rpy'];
 const tree=paths.map(name=>({name,path:'game/'+name}));
 const groups=groupedFiles([{name:'game',path:'game',children:tree}],project,index);
 const purpose=(name:string)=>groups.find(group=>group.children?.some(file=>file.name===name))?.name;
 assert.equal(purpose('story.rpy'),'其他文件');assert.equal(purpose('shared.rpy'),'剧情脚本');
 assert.equal(purpose('config.rpy'),'游戏配置');assert.equal(purpose('picture.png'),'其他文件');assert.equal(purpose('screens.rpy'),'界面与主题');
});
