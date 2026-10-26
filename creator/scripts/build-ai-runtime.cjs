'use strict';
// Offline build from the verified pinned checkout after its frozen-lockfile install.
// No tests, model calls, plugin installation or agent runs are performed here.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ts=require('typescript'),esbuild=require('esbuild');
const [sourceArgument,nodeArgument,pwshArgument,nodeLicenseArgument]=process.argv.slice(2);
if(!sourceArgument||!nodeArgument||!pwshArgument||!nodeLicenseArgument)throw new Error('Usage: node scripts/build-ai-runtime.cjs PINNED_SOURCE NODE_EXE PWSH_DIRECTORY NODE_LICENSE');
const source=path.resolve(sourceArgument),root=path.resolve(__dirname,'..'),output=path.join(root,'ai-runtime');
const pin='22ddee3792402c3e70ec5f86a63c3e3e895a2f60',version='0.2.1-rc.3';
if(!path.basename(source).includes(pin))throw new Error('Expected the fixed official source archive directory.');
if(process.versions.node!=='25.8.2')throw new Error('Build with Node 25.8.2.');
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
for(const relative of ['apps/cli','packages/sdk/client'])if(read(path.join(source,relative,'package.json')).version!==version)throw new Error('Pinned SDK/runtime version mismatch.');
const staging=process.env.CREATOR_DSH_RESUME?path.resolve(process.env.CREATOR_DSH_RESUME):path.join(root,'.cache','ai-runtime-'+crypto.randomUUID());
if(!staging.startsWith(path.join(root,'.cache','ai-runtime-')))throw new Error('Invalid staging directory.');
fs.mkdirSync(path.join(staging,'node_modules'),{recursive:true});
const registry=new Map(),queue=[],built=[];
const workspaces=new Map();
for(const pattern of ['packages/*/*/package.json','vendor/*/package.json','apps/*/package.json','native/system/packages/*/package.json'])for(const file of fs.globSync(pattern,{cwd:source})){const directory=path.dirname(path.join(source,file)),manifest=read(path.join(directory,'package.json'));workspaces.set(manifest.name,directory);}
function within(parent,child){const rel=path.relative(parent,child);return !rel.startsWith('..')&&!path.isAbsolute(rel);}
function locate(name,from){
 let folder=from;while(true){const candidate=path.join(folder,'node_modules',name);if(fs.existsSync(path.join(candidate,'package.json')))return fs.realpathSync(candidate);const parent=path.dirname(folder);if(parent===folder)break;folder=parent;}
 return workspaces.get(name)||null;
}
function findRuntime(name,from){
 let folder=from;while(within(staging,folder)){const candidate=path.join(folder,'node_modules',name);if(registry.has(candidate))return candidate;const parent=path.dirname(folder);if(parent===folder)break;folder=parent;}return null;
}
function copyPackage(real,dest){
 fs.mkdirSync(path.dirname(dest),{recursive:true});
 if(!fs.existsSync(path.join(dest,'package.json')))fs.cpSync(real,dest,{recursive:true,dereference:false,filter:file=>{const relative=path.relative(real,file),parts=relative.split(path.sep);return !parts.some(p=>['node_modules','.git','tests','test','__snapshots__','.cache'].includes(p))&&!/\.tsbuildinfo$/.test(file);}});
 registry.set(dest,real);queue.push({real,dest});return dest;
}
function add(name,from,destination=staging){
 const real=locate(name,from);if(!real)return null;
 const hit=findRuntime(name,destination);if(hit&&registry.get(hit)===real)return hit;
 const preferred=path.join(staging,'node_modules',name);
 const dest=!registry.has(preferred)?preferred:path.join(destination,'node_modules',name);
 if(registry.has(dest)){if(registry.get(dest)!==real)throw new Error('Unresolved package version collision: '+name);return dest;}
 return copyPackage(real,dest);
}
const seed=path.join(source,'packages/sdk/client');
for(const [name,relative] of [['@deepseek-ai/dsh-sdk-client','packages/sdk/client'],['@deepseek-ai/dsh-llm-pi-ai','packages/llm/llm-pi-ai'],['@deepseek-ai/dsh-tools','packages/core/tools'],['@deepseek-ai/dsh-skill','packages/skill/skill'],['@deepseek-ai/dsh-skill-filesystem','packages/skill/skill-filesystem'],['@deepseek-ai/dsh-tool-skill','packages/skill/tool-skill']])copyPackage(path.join(source,relative),path.join(staging,'node_modules',name));
for(let i=0;i<queue.length;i++){
 const {real,dest}=queue[i],manifest=read(path.join(real,'package.json'));
 for(const [name,spec] of Object.entries({...manifest.dependencies,...manifest.optionalDependencies,...manifest.peerDependencies})){
  const location=add(name,real,dest);
  if(!location&&!manifest.optionalDependencies?.[name]&&!manifest.peerDependenciesMeta?.[name]?.optional)throw new Error('Missing locked dependency '+name+' required by '+manifest.name+' '+spec);
 }
 if(within(source,real)&&!within(path.join(source,'node_modules'),real))built.push({real,dest,manifest});
}
function walk(directory){if(!fs.existsSync(directory))return [];return fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);}
async function compile({real,dest,manifest}){
 const input=path.join(real,'src'),emitted=path.join(dest,'lib','types');
 for(const file of walk(input)){
  const relative=path.relative(input,file),target=path.join(emitted,relative.replace(/\.(?:tsx?|mts|cts)$/,'.js'));fs.mkdirSync(path.dirname(target),{recursive:true});
  if(/\.d\.[cm]?ts$/.test(file))continue;
  if(/\.[cm]?tsx?$/.test(file)){
   const result=ts.transpileModule(fs.readFileSync(file,'utf8'),{fileName:file,compilerOptions:{target:ts.ScriptTarget.ES2024,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX,rewriteRelativeImportExtensions:true,esModuleInterop:true,useDefineForClassFields:true}});
   fs.writeFileSync(target,result.outputText);
  }else fs.copyFileSync(file,target);
 }
 const entries=new Set(),entrySources=new Map();
 const collect=value=>{if(typeof value==='string'){if(/^(?:\.\/)?lib\/(?!types\/).*\.[cm]?js$/.test(value)&&!value.includes('*'))entries.add(value);}else if(value&&typeof value==='object'){
  if(typeof value.types==='string'&&value.types.includes('/lib/types/'))for(const key of ['default','import','require'])if(typeof value[key]==='string')entrySources.set(value[key],path.join(dest,value.types.replace(/\.d\.ts$/,'.js')));
  for(const [key,v] of Object.entries(value))if(key!=='types')collect(v);
 }};
 collect(manifest.exports);collect(manifest.main);collect(manifest.bin);
 for(const entry of entries){
  const relative=entry.replace(/^\.\//,'').replace(/^lib\//,''),file=entrySources.get(entry)||path.join(emitted,relative.replace(/\.[cm]js$/,'.js'));
  if(relative.startsWith('client'))continue;
  if(!fs.existsSync(file)){if(relative.startsWith('client')||relative.startsWith('typert.'))continue;throw new Error('Missing runtime entry '+manifest.name+' '+entry);}
  await esbuild.build({entryPoints:[file],outfile:path.join(dest,entry),bundle:true,packages:'external',format:entry.endsWith('.cjs')?'cjs':'esm',platform:'node',target:'node25',logLevel:'warning',external:['*?raw','*.css','*.svg','*.webp','*.png','*.node'],legalComments:'linked'});
 }
 console.log('Built '+manifest.name+' '+manifest.version);
}
(async()=>{
 if(process.env.CREATOR_DSH_FINALIZE_ONLY!=='1')for(const item of built)await compile(item);
 const inventory=[...registry].map(([dest,real])=>{const m=read(path.join(dest,'package.json'));return {name:m.name,version:m.version,license:m.license||'See package notice',path:path.relative(staging,dest).replaceAll('\\','/'),source:within(source,real)&&!real.includes(path.sep+'node_modules'+path.sep)?pin:'pnpm-lock.yaml'};});
 const plan={root,staging,source,output,pin,version,node:path.resolve(nodeArgument),pwsh:path.resolve(pwshArgument),nodeLicense:path.resolve(nodeLicenseArgument),inventory};
 const planFile=path.join(root,'.cache','ai-runtime-plan.json');fs.writeFileSync(planFile,JSON.stringify(plan));
 const python=path.join(process.env.CREATOR_RENPY_SDK||path.resolve(root,'../renpy-8.5.3-sdk'),'lib/py3-windows-x86_64/python.exe');
 const result=require('node:child_process').spawnSync(python,['-B',path.join(__dirname,'finalize-ai-runtime.py'),planFile],{stdio:'inherit',windowsHide:true});
 if(result.error)throw result.error;if(result.status!==0)throw new Error('AI runtime finalization failed: '+result.status);
 console.log('Packaged pinned AI runtime: '+output);
})().catch(error=>{console.error(error);process.exitCode=1;});
