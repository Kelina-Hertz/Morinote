'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { atomicWrite } = require('./local-files.cjs');

function startupProject({userData,executable,sourceDirectory}) {
  const file=path.join(userData,'workspace.json');
  if(fs.existsSync(file)) {
    try {const saved=JSON.parse(fs.readFileSync(file,'utf8'));if(saved.lastProject)return {path:saved.lastProject,remembered:true};}
    catch {return {error:'上次的项目记录无法读取，请重新打开项目。'};}
  }
  // In a checkout creator/ sits beside game/. The portable build may be
  // several directories below it. Search ancestors only; never create a game.
  const starts=[path.resolve(sourceDirectory),path.dirname(executable)];
  const candidates=[];
  for(const start of starts){let dir=start;for(let depth=0;depth<7;depth++){candidates.push(dir);const parent=path.dirname(dir);if(parent===dir)break;dir=parent;}}
  return {path:candidates.find(p=>fs.existsSync(path.join(p,'game'))),remembered:false};
}
function rememberProject(userData,root){if(root)atomicWrite(path.join(userData,'workspace.json'),JSON.stringify({lastProject:root}));}
module.exports={startupProject,rememberProject};
