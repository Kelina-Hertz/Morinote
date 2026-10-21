const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
function run(command,args){const result=spawnSync(command,args,{cwd:root,stdio:'inherit',windowsHide:true,env:{...process.env,PYTHONUTF8:'1'}});if(result.error)throw result.error;if(result.status!==0)throw new Error(command+' failed ('+result.status+')');}
try{
 run(process.execPath,[require.resolve('typescript/bin/tsc'),'--noEmit']);
 run(process.execPath,['--test','electron/tests/offline.test.cjs']);
 fs.mkdirSync(path.join(root,'.checks'),{recursive:true});
 require('esbuild').buildSync({entryPoints:[path.join(root,'tests/renderer.test.ts')],bundle:true,platform:'node',format:'cjs',outfile:path.join(root,'.checks/renderer.test.cjs')});
 run(process.execPath,['--test','.checks/renderer.test.cjs']);
 run(process.env.CREATOR_TEST_PYTHON||'python',['-B','-m','unittest','discover','-s','backend/tests','-v']);
}catch(error){console.error(error.message);process.exitCode=1;}
