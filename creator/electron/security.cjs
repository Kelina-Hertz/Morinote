'use strict';

const { fileURLToPath } = require('node:url');
const path = require('node:path');

const ROUTES = new Map([
  ['/api/project', 'GET'], ['/api/project/new', 'POST'], ['/api/project/open', 'POST'],
  ['/api/project/save', 'POST'], ['/api/project/validate', 'POST'], ['/api/project/migrate', 'POST'],
  ['/api/project/inspect', 'POST'], ['/api/project/reindex', 'POST'],
  ['/api/assets/import', 'POST'], ['/api/preview/start', 'POST'], ['/api/preview/update', 'POST'],
  ['/api/preview/mode', 'POST'], ['/api/preview/stop', 'POST'], ['/api/preview/status', 'GET'],
  ['/api/build', 'POST'], ['/api/export', 'POST'],  
    
  
  ['/api/project/source', 'POST'], ['/api/project/confirm', 'POST'],
  ['/api/assets/scan', 'POST'], ['/api/preview/reload', 'POST'],
  ['/api/workspace', 'GET'], ['/api/workspace/save', 'POST'], ['/api/workspace/restore', 'POST'],
  ['/api/workspace/rename', 'POST'], ['/api/workspace/operation', 'POST'], ['/api/workspace/metadata', 'POST'],
  ['/api/preview/native', 'POST'],
  ['/api/workspace/analyze', 'POST'], ['/api/workspace/prepare', 'POST'],
  ['/api/workspace/barrier', 'POST'],
  ['/api/assets/need','POST'],
  ['/api/workspace/save-recovery','GET'], ['/api/workspace/save-recovery-ack','POST'],
  ['/api/workspace/merge','POST'], ['/api/workspace/motion-source','POST'],
  ['/api/preview/motion','POST'], ['/api/preview/screenshot','POST'],
]);

function routeMethod(route, body) {
  if (typeof route === 'string' && route.includes('?')) {
    const url = new URL(route, 'http://127.0.0.1');
    if (url.pathname === '/api/workspace/document') {
      const file=url.searchParams.get('path');
      if(body!==undefined || !file || file.includes('\\') || file.includes(':') || file.split('/').some(p=>!p||p==='.'||p==='..') || [...url.searchParams.keys()].some(k=>!['path','projectSession'].includes(k))) throw new Error('无效工程源码路径');
      return 'GET';
    }
    if(url.searchParams.has('projectSession')) {
      const scope=url.searchParams.get('projectSession');
      if(!/^[a-f0-9]{32}$/.test(scope)) throw new Error('无效项目会话');
      url.searchParams.delete('projectSession');
      const query=url.searchParams.toString();
      return routeMethod(url.pathname+(query?'?'+query:''),body);
    }
  }
  if (typeof route === 'string' && /^\/api\/preview\/status\?after=\d+$/.test(route)) {
    if (body !== undefined) throw new Error('读取接口不接受请求正文');
    return 'GET';
  }
  if (typeof route === 'string' && route.startsWith('/api/project/source?')) {
    const query = new URL(route, 'http://127.0.0.1').searchParams;
    const file = query.get('path');
    if (body !== undefined || [...query.keys()].length !== 1 || !file?.startsWith('extensions/') || file.includes('\\') || file.includes(':') || file.includes('\0') || file.split('/').some(p => !p || p === '.' || p === '..')) throw new Error('只允许读取扩展源文件');
    return 'GET';
  }
  if (typeof route !== 'string' || !ROUTES.has(route)) throw new Error('不允许的本地接口');
  const method = ROUTES.get(route);
  if (method === 'GET' && body !== undefined) throw new Error('读取接口不接受请求正文');
  if (body !== undefined && (!body || typeof body !== 'object' || Array.isArray(body))) throw new Error('请求正文必须为对象');
  if (JSON.stringify(body ?? {}).length > 32 * 1024 * 1024) throw new Error('请求过大');
  return method;
}

function trustedSender(event, window, loadedURL) {
  if (!window || window.isDestroyed() || event.sender !== window.webContents || event.senderFrame !== window.webContents.mainFrame) return false;
  try {
    const actual = new URL(event.senderFrame.url);
    const expected = new URL(loadedURL);
    if (actual.protocol !== expected.protocol) return false;
    if (actual.protocol === 'file:') return path.resolve(fileURLToPath(actual)) === path.resolve(fileURLToPath(expected));
    return actual.origin === expected.origin && actual.pathname === expected.pathname;
  } catch { return false; }
}

function redact(value, secrets = []) {
  const clean = (text) => {
    let result = text;
    for (const secret of secrets.filter(Boolean)) result = result.split(secret).join('[已隐藏]');
    return result.replace(/\b(?:sk-|sk_)[A-Za-z0-9_\-]{8,}/g, '[已隐藏]')
      .replace(/(Bearer\s+)[^\s"']+/gi, '$1[已隐藏]');
  };
  if (typeof value === 'string') return clean(value);
  if (Array.isArray(value)) return value.map(v => redact(v, secrets));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) =>
    [key,
      /^(?:api[-_]?key|authorization|secret|key)$/i.test(key) ? '[已隐藏]' : redact(item, secrets)]));
  return value;
}

module.exports = { ROUTES, routeMethod, trustedSender, redact };
