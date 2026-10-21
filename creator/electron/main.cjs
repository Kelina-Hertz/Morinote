'use strict';

const { app, BrowserWindow, ipcMain, dialog, session } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { routeMethod, trustedSender, redact } = require('./security.cjs');
const { startupProject, rememberProject } = require('./workspace-startup.cjs');
const { RecoveryStore } = require('./recovery.cjs');
const { RenpyLauncher } = require('./renpy-launcher.cjs');

let window, backend, serviceURL, loadedURL, renpyLauncher;
let exiting = false;
let startupWarning = '';
app.setName('Morinote IDE Offline');
const profileDirectory = app.commandLine.getSwitchValue('user-data-dir');
app.setPath('userData', profileDirectory ? path.resolve(profileDirectory) : path.join(app.getPath('appData'), 'Morinote-IDE-Offline'));
const token = crypto.randomBytes(32).toString('hex');
const recovery = new RecoveryStore();
const pendingSourceMutations = new Set();
const SOURCE_MUTATIONS = new Set(['/api/workspace/save', '/api/workspace/restore', '/api/workspace/rename', '/api/workspace/operation', '/api/project/source']);
let recoveryReady = false, closeAllowed = false, closePending = null;

async function backendRequest(route, body, options = {}) {
  const method = routeMethod(route, body);
  if (!serviceURL) throw new Error('本地制作服务尚未启动');
  let response, value;
  try {
    response = await fetch(`${serviceURL}${route}`, { method, headers: { Authorization: `Bearer ${token}`, 'content-type': 'application/json' },
      ...(method === 'POST' ? { body: JSON.stringify(body ?? {}) } : {}), signal: options.signal ?? AbortSignal.timeout(300000), redirect: 'error' });
    value = await response.json();
  } catch (cause) {
    const error = new Error(`本地服务连接中断，调用结果待确认：${cause.message}`);
    error.code = 'BACKEND_TRANSPORT'; throw error;
  }
  if (!response.ok) { const error = new Error(value.error ?? `本地服务错误：${response.status}`); error.code = 'BACKEND_TOOL'; error.status = response.status; throw error; }
  if (['/api/project', '/api/project/open', '/api/project/new', '/api/project/migrate'].includes(route.split('?')[0])) await recovery.register(value);
  return value;
}

async function startBackend() {
  const base = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
  const sdk = app.isPackaged ? path.join(base, 'renpy-sdk') : path.resolve(process.env.CREATOR_RENPY_SDK || path.join(base, '..', 'renpy-8.5.3-sdk'));
  renpyLauncher = new RenpyLauncher(sdk);
  const python = path.join(sdk, 'lib', 'py3-windows-x86_64', 'python.exe');
  const server = path.join(base, 'backend', 'server.py');
  if (!fs.existsSync(python) || !fs.existsSync(server)) throw new Error('缺少 Ren’Py 8.5.3 或制作服务文件，请重新安装制作器');
  const readyDir = path.join(app.getPath('userData'), 'runtime');
  fs.mkdirSync(readyDir, { recursive: true });
  const ready = path.join(readyDir, `ready-${crypto.randomUUID()}.json`);
  let processError = '', output = '';
  backend = spawn(python, ['-B', server, '--port', '0', '--token', token, '--sdk', sdk, '--ready-file', ready], {
    cwd: base, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1' },
  });
  backend.on('error', error => { processError = error.message; });
  const keepOutput = chunk => { output = (output + chunk.toString('utf8')).slice(-6000); };
  backend.stdout.on('data', keepOutput); backend.stderr.on('data', keepOutput);
  try {
    for (let attempt = 0; attempt < 300; attempt++) {
      if (fs.existsSync(ready)) {
        const readyData = JSON.parse(fs.readFileSync(ready, 'utf8'));
        if (!Number.isInteger(readyData.port) || readyData.port < 1 || readyData.port > 65535) throw new Error('制作服务端口无效');
        serviceURL = `http://127.0.0.1:${readyData.port}`;
        await backendRequest('/api/project');
        return;
      }
      if (processError || backend.exitCode !== null) throw new Error(processError || `制作服务已退出：${output}`);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error(`制作服务启动超时：${output}`);
  } finally { if (fs.existsSync(ready)) fs.unlinkSync(ready); }
}

function handle(channel, fn) {
  ipcMain.handle(channel, async (event, ...args) => {
    if (!trustedSender(event, window, loadedURL)) throw new Error('不允许的调用来源');
    try { return await fn(...args); }
    catch (error) { throw new Error(redact(error.message, [token])); }
  });
}

function registerIPC() {
  handle('creator:request', async (route, body) => {
    const routePath = typeof route === 'string' ? route.split('?')[0] : '';
    if (closePending && ['/api/project/open', '/api/project/new', '/api/project/migrate'].includes(routePath)) throw new Error('正在备份并关闭编辑器，请先取消关闭再切换项目');
    if (pendingSourceMutations.size && ['/api/project/open', '/api/project/new', '/api/project/migrate'].includes(routePath)) throw new Error('源码保存尚未结束，完成后才能切换项目');
    const mutation = SOURCE_MUTATIONS.has(routePath) && body !== undefined ? {} : null;
    if (mutation) pendingSourceMutations.add(mutation);
    let result;
    try { result = await backendRequest(route, body); }
    catch (error) {
      if (mutation && error.code === 'BACKEND_TRANSPORT') {
        mutation.uncertain = true;
        void waitForSourceCompletion(mutation, body?.projectSession);
      }
      throw error;
    } finally { if (mutation && !mutation.uncertain) pendingSourceMutations.delete(mutation); }
    if(['/api/project/open','/api/project/new','/api/project/migrate'].includes(route)) {
      rememberProject(app.getPath('userData'),result.root); startupWarning='';
    }
    if(route==='/api/project' && startupWarning) result.startupWarning=startupWarning;
    return result;
  });
  handle('creator:recovery', (method, payload) => recovery.request(method, payload));
  handle('creator:openRenpy', async payload => {
    if (closePending) throw new Error('正在关闭 IDE，请先取消关闭。');
    if (pendingSourceMutations.size) throw new Error('源码仍在保存，请等待完成后打开 Ren’Py 启动器。');
    const current = await backendRequest('/api/project');
    const assertCurrent = () => {
      if (!payload?.projectSession || current.session !== payload.projectSession || recovery.context?.session !== payload.projectSession) throw new Error('项目已切换，请重新打开 Ren’Py 启动器。');
      if (closePending) throw new Error('正在关闭 IDE，已取消打开启动器。');
    };
    assertCurrent();
    if (!current.project?.nativeRenpy || !current.root) throw new Error('请先打开 Ren’Py 原工程。');
    return renpyLauncher.open(current.root, assertCurrent);
  });
  ipcMain.on('creator:recovery-ready', (event, ready) => {
    if (trustedSender(event, window, loadedURL)) recoveryReady = ready === true;
  });
  ipcMain.on('creator:close-result', (event, result) => {
    if (!trustedSender(event, window, loadedURL) || !closePending || result?.id !== closePending.id) return;
    closePending.resolve(result.ok === true ? null : String(result.error || '草稿备份失败'));
  });
  handle('creator:pickFolder', async () => {
    const result = await dialog.showOpenDialog(window, { properties: ['openDirectory', 'createDirectory'], title: '选择项目文件夹' });
    return result.canceled ? null : result.filePaths[0];
  });
  handle('creator:pickFiles', async kind => {
    const filters = kind === 'audio' ? [{ name: '音乐与音效', extensions: ['ogg', 'mp3', 'wav', 'opus', 'flac'] }]
      : kind === 'json' ? [{ name: '旧工作台项目数据', extensions: ['json'] }]
      : kind === 'script' ? [{ name: '剧本和项目数据', extensions: ['docx', 'json', 'rpy'] }]
        : [{ name: '图片素材', extensions: ['png', 'jpg', 'jpeg', 'webp', 'avif', 'svg'] }];
    const result = await dialog.showOpenDialog(window, { properties: ['openFile', 'multiSelections'], filters });
    return result.canceled ? [] : result.filePaths;
  });
  handle('creator:mediaUrl', id => {
    if (typeof id !== 'string' || !id || id.length > 300) throw new Error('素材 ID 无效');
    return `${serviceURL}/api/media?id=${encodeURIComponent(id)}&token=${token}`;
  });

}

async function waitForSourceCompletion(mutation, projectSession) {
  // A transport timeout is not evidence that Python finished writing. The
  // read-only barrier takes the same service lock as source mutations.
  while (backend && backend.exitCode === null) {
    try {
      const result = await backendRequest('/api/workspace/barrier', { projectSession }, { signal: AbortSignal.timeout(15000) });
      if (result.idle === true) break;
    } catch (error) {
      // Keep an uncertain save pending until the barrier explicitly succeeds
      // or the service exits; a rejected request is not completion evidence.
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  pendingSourceMutations.delete(mutation);
}

function cancelClose() {
  if (closePending?.timer) clearTimeout(closePending.timer);
  closePending = null;
  if (window && !window.isDestroyed()) window.webContents.send('creator:close-cancelled');
}

async function prepareClose() {
  if (!window || window.isDestroyed() || closePending) return;
  const id = crypto.randomUUID();
  const failure = await new Promise(resolve => {
    const timer = setTimeout(() => resolve('等待草稿备份超时；现有备份仍然保留。'), 15000);
    closePending = { id, timer, resolve: result => { clearTimeout(timer); resolve(result); } };
    window.webContents.send('creator:prepare-close', { id });
  });
  if (!window || window.isDestroyed() || closePending?.id !== id) return;
  const saving = pendingSourceMutations.size > 0;
  if (!failure && !saving) {
    closePending = null; closeAllowed = true; window.close(); return;
  }
  const result = await dialog.showMessageBox(window, {
    type: 'warning', title: saving ? '正在保存源码' : '草稿备份尚未完成',
    message: saving ? '源码仍在保存，暂时不能关闭 IDE。' : '最近的修改尚未确认备份成功。',
    detail: saving ? '请等待保存完成后重试，或取消关闭继续编辑。现有恢复草稿保持不变。' : `${failure || '草稿尚未备份'}\n退出会放弃最后一次成功备份之后的修改；已有草稿和历史仍保留。`,
    buttons: saving ? ['重试', '取消关闭'] : ['重试', '取消关闭', '放弃未备份修改并退出'], defaultId: 0, cancelId: 1, noLink: true,
  });
  if (!window || window.isDestroyed() || closePending?.id !== id) return;
  if (result.response === 0) { clearTimeout(closePending.timer); closePending = null; void prepareClose(); }
  else if (result.response === 2 && !pendingSourceMutations.size) {
    clearTimeout(closePending.timer); closePending = null; closeAllowed = true; window.close();
  } else cancelClose();
}

function createWindow() {
  const dev = !app.isPackaged && process.env.CREATOR_DEV_URL;
  if (dev) {
    const url = new URL(dev);
    if (url.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(url.hostname) || url.username || url.password) throw new Error('开发界面只允许本机 HTTP 地址');
    loadedURL = url.href;
  } else loadedURL = pathToFileURL(path.resolve(__dirname, '..', 'dist', 'index.html')).href;
  // Vite's development React refresh preamble is inline. Packaged builds keep
  // the stricter policy and only load the compiled, local renderer scripts.
  const csp = `default-src 'self'; script-src 'self'${dev ? " 'unsafe-inline'" : ''}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: http://127.0.0.1:*; media-src 'self' blob: http://127.0.0.1:*; connect-src 'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*; worker-src 'self' blob:; object-src 'none'; frame-src 'none'; base-uri 'none'`;
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({ responseHeaders: { ...details.responseHeaders, 'Content-Security-Policy': [csp] } });
  });
  window = new BrowserWindow({ width: 1560, height: 980, minWidth: 1100, minHeight: 740, title: 'Morinote IDE', backgroundColor: '#10141b',
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true,
      webSecurity: true, allowRunningInsecureContent: false, spellcheck: false } });
  window.removeMenu();
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => { if (url !== loadedURL) event.preventDefault(); });
  window.webContents.on('will-attach-webview', event => event.preventDefault());
  window.on('close', event => {
    if (!closeAllowed && recoveryReady && recovery.context) {
      event.preventDefault(); void prepareClose();
    }
  });
  // A renderer beforeunload veto is silent in Electron unless the host
  // presents its own confirmation. Never tear down the service before it.
  window.webContents.on('will-prevent-unload', event => {
    if (closeAllowed) { event.preventDefault(); return; }
    const choice = dialog.showMessageBoxSync(window, {
      type: 'warning', title: '未保存的修改', message: '还有未保存的修改，要退出 IDE 吗？',
      detail: '选择继续编辑后，可按 Ctrl+S 保存。直接退出会放弃尚未保存的修改。',
      buttons: ['继续编辑', '放弃修改并退出'], defaultId: 0, cancelId: 0, noLink: true,
    });
    // In this event preventDefault means ignore the renderer's veto.
    if (choice === 1) event.preventDefault();
  });
  window.on('closed', () => { window = null; });
  window.loadURL(loadedURL).catch(error => dialog.showErrorBox('界面加载失败', error.message));
}

async function boot() {
  await startBackend();
  const initial=startupProject({userData:app.getPath('userData'),executable:app.getPath('exe'),sourceDirectory:__dirname});
  startupWarning=initial.error||'';
  if(initial.path) {
    try {const result=await backendRequest('/api/project/open',{path:initial.path});rememberProject(app.getPath('userData'),result.root);}
    catch(error) {startupWarning=`无法打开${initial.remembered?'上次':'默认'}项目，请重新定位：${initial.path}。${error.message}`;}
  }
  registerIPC(); createWindow();
  backend.on('exit', code => { if (!exiting && window) dialog.showErrorBox('本地服务已退出', `本地制作服务已退出（${code}），请重新启动 IDE。`); });
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus(); } });
  app.whenReady().then(boot).catch(error => { dialog.showErrorBox('制作器启动失败', redact(error.message, [token])); backend?.kill(); app.quit(); });
  app.on('window-all-closed', () => app.quit());
  // will-quit runs only after all windows accepted closing. Cancelling the
  // unsaved-work prompt must leave the backend available.
  app.on('will-quit', event => {
    if (exiting) return;
    event.preventDefault(); exiting = true;
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true; clearTimeout(deadline);
      backend?.kill(); app.exit(0);
    };
    // A hung local service must not leave the desktop process stuck exiting.
    const deadline = setTimeout(finish, 3500);
    const stop = serviceURL ? backendRequest('/api/preview/stop', {}, { signal: AbortSignal.timeout(2500) }).catch(() => {}) : Promise.resolve();
    stop.finally(finish);
  });
}
