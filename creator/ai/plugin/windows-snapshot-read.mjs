// Fixed SDK capability, fixed private snapshot: no grants on the authored tree.
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

export function readGrantArguments(confined,root){
 const argv=confined.argv||[],w=argv.indexOf('--workspace'),s=argv.indexOf('--write-sid');
 if(confined.enforcement!=='partial'||w<0||s<0||path.resolve(argv[w+1])!==path.resolve(root)||!/^S-1-4-\d+-\d+$/.test(argv[s+1]||''))throw new Error('受限副本的读取能力无法验证，未启动执行。');
 return {root:path.resolve(root),sid:argv[s+1]};
}
export async function ensureSnapshotRead(confined,root,env,signal){
 if(process.platform!=='win32')return;
 const policy=readGrantArguments(confined,root);
 // A freshly created private Windows directory can inherit only OWNER RIGHTS.
 // LUA tokens then lose read access although the SDK granted write access.
 // Add RX to the SAME workspace capability SID, within the SAME snapshot.
 // The SDK owns that SID's lifetime and revokes it when the session ends.
 const pwsh=process.env.MORINOTE_PWSH;if(!pwsh)throw new Error('缺少随附 PowerShell，未启动受限执行。');
 const script=fileURLToPath(new URL('./windows-snapshot-read.ps1',import.meta.url));
 await new Promise((resolve,reject)=>{let output='';const child=spawn(pwsh,['-NoProfile','-NonInteractive','-File',script,'-Root',policy.root,'-WriteSid',policy.sid],{windowsHide:true,stdio:['ignore','pipe','pipe'],env,signal});const collect=chunk=>{output=(output+chunk.toString()).slice(-1500);};child.stdout.on('data',collect);child.stderr.on('data',collect);child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(new Error('受限副本无法取得读取能力，未启动执行（'+code+'）：'+output)));});
}
