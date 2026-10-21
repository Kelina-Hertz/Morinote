// Smoke test only our newly extracted package in an isolated profile/project.
// Remote debugging is opt-in for this test process and binds to loopback.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const creator=path.resolve(__dirname,'..'),output=path.join(creator,'.checks','packaged-smoke'),profile=path.join(output,'profile-'+crypto.randomUUID());
const executable=process.env.CREATOR_TEST_EXE,project=process.env.CREATOR_TEST_PROJECT;
if(!executable||!project)throw new Error('Set CREATOR_TEST_EXE and CREATOR_TEST_PROJECT (disposable game).');
fs.mkdirSync(profile,{recursive:true});fs.writeFileSync(path.join(profile,'workspace.json'),JSON.stringify({lastProject:project}));
const child=spawn(executable,['--user-data-dir='+profile,'--remote-debugging-address=127.0.0.1','--remote-debugging-port=0'],{windowsHide:true,stdio:'ignore'});
let socket,timer,serial=0;const pending=new Map(),report={checks:[],executable,profile};
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const value=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(value.exceptionDetails)throw new Error(value.exceptionDetails.text);return value.result.value;}
async function wait(condition,message,timeout=35000){const end=Date.now()+timeout;while(Date.now()<end){if(child.exitCode!==null)throw new Error('Packaged IDE exited unexpectedly: '+child.exitCode);if(await condition())return;await pause(150);}throw new Error(message);}
(async()=>{
 try{
  const portFile=path.join(profile,'DevToolsActivePort');
  await wait(()=>fs.existsSync(portFile),'Packaged browser did not start');
  const port=Number(fs.readFileSync(portFile,'utf8').split('\n')[0]);if(!Number.isInteger(port)||port<1||port>65535)throw new Error('Invalid local debugging port');
  let page;await wait(async()=>{const targets=await (await fetch('http://127.0.0.1:'+port+'/json/list')).json();page=targets.find(t=>t.type==='page'&&t.url.startsWith('file:'));return !!page;},'Packaged renderer not found');
  socket=new WebSocket(page.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  socket.onmessage=event=>{const response=JSON.parse(String(event.data)),request=pending.get(response.id);if(request){pending.delete(response.id);if(response.error)request.reject(new Error(response.error.message));else request.resolve(response.result);}};
  await wait(()=>evaluate(`!!document.querySelector('.native-ide:not([inert]) .react-flow__node')`),'Packaged native workspace did not load');
  await wait(()=>evaluate(`document.body.innerText.includes('百团巡游 · 寻找动漫社')`),'Packaged scene title preset did not load');
  const context=await evaluate(`window.creator.request('/api/project')`);
  if(path.resolve(context.root)!==path.resolve(project))throw new Error('Packaged IDE selected the wrong project');
  report.checks.push('actual packaged executable starts with isolated profile and intended project');
  report.checks.push('bundled preload, Python service and native story flow load correctly');
  const result=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,'packaged-flow.png'),Buffer.from(result.data,'base64'));
  await send('Runtime.evaluate',{expression:`[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='项目素材库').click()`});
  await wait(()=>evaluate(`!!document.querySelector('.virtual-library')`),'Packaged asset library did not load');
  report.checks.push('packaged virtual asset library opens');
  report.ok=true;
 }catch(error){report.ok=false;report.error=String(error.stack||error);process.exitCode=1;}
 finally{
  fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
  if(socket?.readyState===WebSocket.OPEN){void send('Browser.close').catch(()=>{});await pause(3500);socket.close();}
  if(child.exitCode===null){const killer=spawn('taskkill.exe',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});await new Promise(r=>killer.on('close',r));}
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
