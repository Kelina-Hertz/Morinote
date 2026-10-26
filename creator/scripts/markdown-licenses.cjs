'use strict';
// Keep notices for code bundled by Vite even if npm's dependency collector
// omits transitive modules from app.asar (junction-based local development).
const fs=require('node:fs'),path=require('node:path');
function notices(root){const lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json'),'utf8'));const visited=new Set(),sections=[];
 function visit(name){if(visited.has(name)||name.startsWith('@types/'))return;visited.add(name);const info=lock.packages['node_modules/'+name];if(!info)throw new Error('Missing Markdown dependency lock: '+name);const folder=path.join(root,'node_modules',name),license=fs.readdirSync(folder).filter(n=>/^(?:licen[sc]e|copying|notice)(?:\.|$)/i.test(n));if(!license.length)throw new Error('Missing bundled dependency license: '+name);sections.push('## '+name+' '+info.version+'\n\n'+license.map(file=>fs.readFileSync(path.join(folder,file),'utf8')).join('\n\n'));for(const child of Object.keys(info.dependencies||{}))visit(child);}
 visit('react-markdown');visit('remark-gfm');fs.mkdirSync(path.join(root,'docs'),{recursive:true});fs.writeFileSync(path.join(root,'docs/MARKDOWN-LICENSES.md'),'# Markdown dependency notices\n\n'+sections.join('\n\n'),{encoding:'utf8'});return sections.length;
}
module.exports={notices};
if(require.main===module)console.log('Collected Markdown dependency notices: '+notices(path.resolve(__dirname,'..')));
