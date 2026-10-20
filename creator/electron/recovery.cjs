'use strict';

// Recovery is intentionally independent of the Python compilation queue. It
// stores editor buffers only and never writes a project source file.
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { TextDecoder } = require('node:util');

const MAX_TEXT = 4 * 1024 * 1024;
const MAX_STATE = 32 * 1024 * 1024;
const TEXT = new Set(['.rpy', '.py', '.json', '.md', '.txt', '.toml', '.yaml', '.yml', '.ini', '.cfg', '.csv', '.xml', '.html', '.css', '.js', '.ts', '.glsl', '.gitignore', '.gitattributes']);
const HIDDEN = new Set(['.git', '.creator', 'sources', 'cache', 'saves', '__pycache__']);
const REASONS = new Set(['auto', 'save', 'restore', 'close', 'discard']);
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const isObject = value => value && typeof value === 'object' && !Array.isArray(value);

function relativeSource(value) {
  if (typeof value !== 'string' || !value || value.length > 2000 || /[\\:\x00-\x1f]/.test(value) || path.isAbsolute(value)) throw new Error('无效的恢复文件路径');
  const parts = value.split('/');
  if (parts.some(part => !part || part === '.' || part === '..' || /[. ]$/.test(part) || HIDDEN.has(part.toLowerCase()) || /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part))) throw new Error('该路径不能用于源码恢复');
  if (!TEXT.has(path.extname(value).toLowerCase()) && !TEXT.has(path.basename(value).toLowerCase())) throw new Error('恢复仅支持文本源码');
  return value;
}

async function noLinks(root, relative) {
  let current = root;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    try { if ((await fs.lstat(current)).isSymbolicLink()) throw new Error('恢复路径不能经过符号链接或目录联接'); }
    catch (error) { if (error.code === 'ENOENT') break; throw error; }
  }
  return current;
}

async function atomic(file, data) {
  const temp = file + '.' + crypto.randomUUID() + '.tmp';
  let handle;
  try {
    handle = await fs.open(temp, 'wx');
    await handle.writeFile(data);
    await handle.sync();
    await handle.close(); handle = null;
    await fs.rename(temp, file);
  } finally {
    await handle?.close().catch(() => {});
    await fs.unlink(temp).catch(() => {});
  }
}

function packed(data) {
  return JSON.stringify({ checksum: hash(JSON.stringify(data)), data });
}

async function unpack(file, maximum = MAX_STATE) {
  const stat = await fs.stat(file);
  if (stat.size > maximum) throw new Error('恢复记录超过大小限制');
  const bytes = await fs.readFile(file);
  if (bytes.length > maximum) throw new Error('恢复记录超过大小限制');
  const wrapper = JSON.parse(bytes.toString('utf8'));
  if (!isObject(wrapper) || !isObject(wrapper.data) || wrapper.checksum !== hash(JSON.stringify(wrapper.data))) throw new Error('恢复记录校验失败');
  return wrapper.data;
}

function validateState(input) {
  const serialized = JSON.stringify(input);
  if (!serialized || Buffer.byteLength(serialized) > MAX_STATE) throw new Error('恢复草稿超过 32 MiB，请先保存部分文件');
  const state = JSON.parse(serialized);
  if (!isObject(state) || !Array.isArray(state.documents) || state.documents.length > 200 || !Array.isArray(state.tabs) || state.tabs.length > 300) throw new Error('无效的恢复草稿');
  const paths = new Set();
  for (const document of state.documents) {
    if (!isObject(document) || !isObject(document.base)) throw new Error('无效的恢复文档');
    const relative = relativeSource(document.base.path);
    if (paths.has(relative.toLowerCase())) throw new Error('恢复草稿包含重复路径');
    paths.add(relative.toLowerCase());
    for (const value of [document.base.content, document.value]) {
      if (typeof value !== 'string' || value.includes('\0') || Buffer.byteLength(value) > MAX_TEXT) throw new Error('恢复源码必须是小于 4 MiB 的文本');
    }
    if (typeof document.base.hash !== 'string' || !/^[a-f0-9]{64}$/.test(document.base.hash)) throw new Error('无效的基础源码摘要');
    if (document.base.bom !== undefined && typeof document.base.bom !== 'boolean') throw new Error('无效的 BOM 标记');
    if (document.base.exists !== undefined && typeof document.base.exists !== 'boolean') throw new Error('无效的源码存在标记');
    if (document.base.newline !== undefined && !['\n', '\r\n', '\r'].includes(document.base.newline)) throw new Error('无效的换行格式');
  }
  if (typeof state.active !== 'string' || state.active.length > 4000 || typeof state.lastCode !== 'string' || state.lastCode.length > 2000) throw new Error('无效的编辑器恢复位置');
  if (state.lastCode) relativeSource(state.lastCode);
  if (state.location != null) {
    relativeSource(state.location.path);
    if (!Number.isInteger(state.location.line) || state.location.line < 1 || state.location.line > 10000000) throw new Error('无效的恢复行号');
  }
  for (const tab of state.tabs) {
    if (!isObject(tab) || typeof tab.id !== 'string' || typeof tab.title !== 'string' || tab.id.length > 4000 || tab.title.length > 2000 || !['flow', 'code', 'scene', 'config', 'assets', 'media'].includes(tab.kind)) throw new Error('无效的编辑器恢复标签');
    if (tab.kind === 'code') relativeSource(tab.target);
  }
  return state;
}

class RecoveryStore {
  constructor() { this.context = null; }

  // Called with backend responses, never renderer supplied roots or IDs.
  async register(result) {
    if (!isObject(result) || !Object.hasOwn(result, 'session') || !Object.hasOwn(result, 'root') || !Object.hasOwn(result, 'project')) return;
    if (!result.project?.nativeRenpy || !result.root || !result.session) { this.context = null; return; }
    if (!/^[a-f0-9]{32}$/.test(result.session) || typeof result.project.id !== 'string') throw new Error('无效的项目恢复会话');
    if (this.context?.session === result.session) return;
    const root = await fs.realpath(result.root);
    this.context = { root, projectId: result.project.id, session: result.session, directory: path.join(root, '.creator', 'editor', 'recovery'), queue: Promise.resolve(), sequence: 0, loaded: false };
  }

  bound(payload) {
    const context = this.context;
    if (!context || payload?.projectSession !== context.session) throw new Error('项目已切换，拒绝旧项目恢复请求');
    return context;
  }

  async request(method, payload) {
    const context = this.bound(payload);
    const operation = context.queue.catch(() => {}).then(async () => {
      this.bound(payload);
      await noLinks(context.root, '.creator/editor/recovery');
      await noLinks(context.root, '.creator/editor/recovery/blobs');
      await noLinks(context.root, '.creator/editor/recovery/snapshots');
      if (method === 'readFiles') return this.readFiles(context, payload.paths);
      if (method === 'history') return { items: (await this.history(context)).map(item => ({ id: item.id, time: item.time, reason: item.reason, paths: item.paths })) };
      if (method === 'snapshot') {
        if (typeof payload.id !== 'string' || !/^[a-f0-9-]{36}$/.test(payload.id)) throw new Error('无效的历史快照');
        await noLinks(context.root, '.creator/editor/recovery/snapshots/' + payload.id + '.json');
        const manifest = await unpack(path.join(context.directory, 'snapshots', payload.id + '.json'));
        return { state: await this.expand(context, manifest), savedAt: manifest.time, sequence: manifest.sequence };
      }
      if (!context.loaded) await this.loadCurrent(context);
      if (method === 'current') return this.currentResult(context);
      if (method === 'write') return this.write(context, payload);
      if (method === 'discard') return this.discard(context, payload);
      throw new Error('不支持的恢复操作');
    });
    context.queue = operation;
    return operation;
  }

  currentResult(context) {
    return { state: context.currentState ?? null, savedAt: context.latest?.time, sequence: context.sequence, ...(context.warning ? { warning: context.warning } : {}) };
  }

  async loadCurrent(context) {
    let cleared = null;
    try {
      await noLinks(context.root, '.creator/editor/recovery/cleared.json');
      cleared = await unpack(path.join(context.directory, 'cleared.json'));
      if (!cleared.cleared) throw new Error('无效的放弃草稿记录');
      await this.expand(context, cleared);
    } catch (error) {
      if (error.code !== 'ENOENT') {
        context.warning = '放弃草稿记录损坏，请先在恢复历史中检查草稿';
        context.discardCorrupt = true;
      }
      cleared = null;
    }
    context.clearedAt = cleared?.time;
    const candidates = ['current.json', 'previous.json'];
    let hadFailure = false;
    for (const name of candidates) {
      try {
        await noLinks(context.root, '.creator/editor/recovery/' + name);
        const manifest = await unpack(path.join(context.directory, name));
        if (cleared && manifest.time <= cleared.time) { context.sequence = Math.max(context.sequence, cleared.sequence || 0); continue; }
        const state = await this.expand(context, manifest);
        context.latest = manifest; context.currentState = context.discardCorrupt ? null : state;
        context.sequence = Math.max(context.sequence, manifest.sequence);
        context.loaded = true;
        if (!context.discardCorrupt && (hadFailure || name !== 'current.json')) context.warning = '最近的恢复记录不完整，已回退到上一份完整草稿';
        return;
      } catch (error) { if (error.code !== 'ENOENT') hadFailure = true; }
    }
    if (hadFailure && !context.warning) context.warning = '恢复记录损坏，请查看恢复历史';
    if (!context.warning?.startsWith('放弃草稿记录损坏')) {
      const fallbacks = await this.history(context);
      if (isObject(cleared?.replacement)) fallbacks.push(cleared.replacement);
      fallbacks.sort((left, right) => String(right.time).localeCompare(String(left.time)));
      for (const entry of fallbacks) {
        if (cleared && entry.time <= cleared.time) continue;
        try {
          const state = await this.expand(context, entry);
          context.latest = entry; context.currentState = state; context.sequence = Math.max(context.sequence, entry.sequence);
          context.warning = '最近的恢复记录不完整，已回退到最近可用历史快照'; break;
        } catch { /* Another history record may still be intact. */ }
      }
    }
    context.sequence = Math.max(context.sequence, cleared?.sequence || 0);
    context.loaded = true;
  }

  async expand(context, manifest) {
    if (manifest.version !== 1 || manifest.projectId !== context.projectId || !Number.isSafeInteger(manifest.sequence) || manifest.sequence < 1 || typeof manifest.time !== 'string' || !Number.isFinite(Date.parse(manifest.time))) throw new Error('恢复清单与项目不匹配');
    if (manifest.cleared) return null;
    const state = JSON.parse(JSON.stringify(manifest.state));
    if (!isObject(state) || !Array.isArray(state.documents) || state.documents.length > 200) throw new Error('恢复清单格式不正确');
    let expandedSize = 0;
    const readBlob = async id => {
      if (typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id)) throw new Error('恢复文本引用无效');
      const file = path.join(context.directory, 'blobs', id + '.txt');
      await noLinks(context.root, '.creator/editor/recovery/blobs/' + id + '.txt');
      if ((await fs.stat(file)).size > MAX_TEXT) throw new Error('恢复文本过大');
      const bytes = await fs.readFile(file);
      expandedSize += bytes.length;
      if (bytes.length > MAX_TEXT || expandedSize > MAX_STATE) throw new Error('恢复草稿超过大小限制');
      if (hash(bytes) !== id) throw new Error('恢复文本校验失败');
      return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
    };
    for (const document of state.documents) {
      document.base.content = await readBlob(document.base.contentRef);
      document.value = await readBlob(document.valueRef);
      delete document.base.contentRef; delete document.valueRef;
    }
    return validateState(state);
  }

  async history(context) {
    const directory = path.join(context.directory, 'snapshots');
    const files = await fs.readdir(directory).catch(error => { if (error.code === 'ENOENT') return []; throw error; });
    const items = [];
    for (const name of files) {
      if (!/^[a-f0-9-]{36}\.json$/.test(name)) continue;
      try {
        await noLinks(context.root, '.creator/editor/recovery/snapshots/' + name);
        const item = await unpack(path.join(directory, name));
        if (item.version === 1 && item.projectId === context.projectId && item.id + '.json' === name && Array.isArray(item.paths) && typeof item.time === 'string') items.push(item);
      } catch { /* Keep damaged history on disk for manual recovery. */ }
    }
    return items.sort((left, right) => right.time.localeCompare(left.time));
  }

  async prepareDirectory(context) {
    await noLinks(context.root, '.creator/editor/recovery');
    await fs.mkdir(path.join(context.directory, 'blobs'), { recursive: true });
    await fs.mkdir(path.join(context.directory, 'snapshots'), { recursive: true });
    await noLinks(context.root, '.creator/editor/recovery/blobs');
    await noLinks(context.root, '.creator/editor/recovery/snapshots');
  }

  validateSequence(context, payload) {
    if (!Number.isSafeInteger(payload.sequence) || payload.sequence <= context.sequence) throw new Error('恢复请求已过期，请读取最新序号后重试');
  }

  async write(context, payload) {
    this.validateSequence(context, payload);
    if (!REASONS.has(payload.reason)) throw new Error('无效的草稿备份原因');
    const state = validateState(payload.state);
    await this.prepareDirectory(context);
    const encoded = await this.encodeState(context, state);
    const time = new Date(Math.max(Date.now(), (Date.parse(context.latest?.time || context.clearedAt || '') || 0) + 1)).toISOString();
    const fingerprint = hash(JSON.stringify(encoded.documents.map(document => [document.base.path, document.valueRef, document.base.exists !== false])));
    const manifest = { version: 1, projectId: context.projectId, sequence: payload.sequence, time, reason: payload.reason, fingerprint, paths: state.documents.filter(document => document.base.exists === false || document.value !== document.base.content).map(document => document.base.path), state: encoded };
    this.bound(payload);
    if (context.discardCorrupt) {
      // A fresh explicit editor backup supersedes a damaged discard marker;
      // old drafts remain accessible in history, never auto-restored.
      const marker = { version: 1, projectId: context.projectId, sequence: payload.sequence, time: new Date(Date.parse(time) - 1).toISOString(), reason: 'discard', cleared: true };
      await atomic(path.join(context.directory, 'cleared.json'), packed(marker));
      context.clearedAt = marker.time; context.discardCorrupt = false;
    }
    if (context.latest) await atomic(path.join(context.directory, 'previous.json'), packed(context.latest));
    await atomic(path.join(context.directory, 'current.json'), packed(manifest));
    context.latest = manifest; context.currentState = state; context.sequence = payload.sequence; context.warning = undefined;
    const history = await this.history(context);
    const newest = history[0];
    const sameContent = history.some(item => item.fingerprint === fingerprint);
    const due = !newest || Date.parse(time) - Date.parse(newest.time) >= 60000;
    if (!sameContent && (payload.reason !== 'auto' || due)) {
      const snapshot = { ...manifest, id: crypto.randomUUID() };
      await atomic(path.join(context.directory, 'snapshots', snapshot.id + '.json'), packed(snapshot));
    }
    // Cleanup cannot turn a durable successful backup into an apparent failure.
    await this.prune(context).catch(error => { context.warning = '草稿已备份，但历史清理失败：' + error.message; });
    return { savedAt: time, sequence: context.sequence, ...(!sameContent && payload.reason === 'auto' && !due ? { nextSnapshotAt: new Date(Date.parse(newest.time) + 60000).toISOString() } : {}), ...(context.warning ? { warning: context.warning } : {}) };
  }

  async encodeState(context, state) {
    const encoded = JSON.parse(JSON.stringify(state));
    const blobs = new Map();
    for (const document of encoded.documents) {
      for (const value of [document.base.content, document.value]) blobs.set(hash(value), value);
      document.base.contentRef = hash(document.base.content); delete document.base.content;
      document.valueRef = hash(document.value); delete document.value;
    }
    for (const [id, content] of blobs) {
      const file = path.join(context.directory, 'blobs', id + '.txt');
      await noLinks(context.root, '.creator/editor/recovery/blobs/' + id + '.txt');
      let valid = false;
      try { valid = (await fs.stat(file)).size <= MAX_TEXT && hash(await fs.readFile(file)) === id; } catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (!valid) await atomic(file, content);
    }
    return encoded;
  }

  async discard(context, payload) {
    this.validateSequence(context, payload);
    const state = Object.hasOwn(payload, 'state') ? validateState(payload.state) : null;
    await this.prepareDirectory(context);
    const time = new Date(Math.max(Date.now(), (Date.parse(context.latest?.time || context.clearedAt || '') || 0) + 1)).toISOString();
    const manifest = { version: 1, projectId: context.projectId, sequence: payload.sequence, time, reason: 'discard', cleared: true };
    if (state) {
      const encoded = await this.encodeState(context, state);
      const fingerprint = hash(JSON.stringify(encoded.documents.map(document => [document.base.path, document.valueRef, document.base.exists !== false])));
      manifest.replacement = { version: 1, projectId: context.projectId, sequence: payload.sequence, time: new Date(Date.parse(time) + 1).toISOString(), reason: 'discard', fingerprint, paths: state.documents.filter(document => document.base.exists === false || document.value !== document.base.content).map(document => document.base.path), state: encoded };
    }
    this.bound(payload);
    if (context.latest?.state && !(await this.history(context)).some(item => item.fingerprint === context.latest.fingerprint)) {
      const previous = { ...context.latest, id: crypto.randomUUID(), reason: 'discard' };
      await atomic(path.join(context.directory, 'snapshots', previous.id + '.json'), packed(previous));
    }
    // The watermark prevents a corrupt current record from resurrecting a
    // deliberately discarded draft through previous.json or history fallback.
    // For partial discard the watermark carries the complete remaining draft,
    // so an interruption between these atomic replacements is recoverable.
    await atomic(path.join(context.directory, 'cleared.json'), packed(manifest));
    const current = manifest.replacement || manifest;
    context.latest = current; context.currentState = state; context.sequence = payload.sequence; context.clearedAt = time; context.warning = undefined; context.discardCorrupt = false;
    await atomic(path.join(context.directory, 'current.json'), packed(current));
    await atomic(path.join(context.directory, 'previous.json'), packed(current));
    if (state && !(await this.history(context)).some(item => item.fingerprint === current.fingerprint)) {
      const snapshot = { ...current, id: crypto.randomUUID() };
      await atomic(path.join(context.directory, 'snapshots', snapshot.id + '.json'), packed(snapshot));
    }
    await this.prune(context).catch(error => { context.warning = '草稿已备份，但历史清理失败：' + error.message; });
    return { savedAt: current.time, sequence: context.sequence, ...(context.warning ? { warning: context.warning } : {}) };
  }

  async prune(context) {
    const history = await this.history(context);
    const cutoff = Date.now() - 30 * 86400000;
    const kept = [];
    for (const item of history) {
      if (kept.length < 100 && Date.parse(item.time) >= cutoff) kept.push(item);
      else await fs.unlink(path.join(context.directory, 'snapshots', item.id + '.json')).catch(error => { if (error.code !== 'ENOENT') throw error; });
    }
    const references = new Set();
    const retain = manifest => {
      for (const document of manifest?.state?.documents || []) {
        references.add(document.base.contentRef); references.add(document.valueRef);
      }
    };
    kept.forEach(retain); retain(context.latest);
    try {
      await noLinks(context.root, '.creator/editor/recovery/previous.json');
      retain(await unpack(path.join(context.directory, 'previous.json')));
    } catch { /* latest remains protected */ }
    try {
      await noLinks(context.root, '.creator/editor/recovery/cleared.json');
      retain((await unpack(path.join(context.directory, 'cleared.json'))).replacement);
    } catch { /* current and history remain protected */ }
    // Do not remove blobs from damaged snapshots: those files are intentionally
    // retained for manual salvage instead of making corruption destructive.
    const snapshotNames = await fs.readdir(path.join(context.directory, 'snapshots'));
    if (snapshotNames.filter(name => name.endsWith('.json')).length !== kept.length) return;
    for (const name of await fs.readdir(path.join(context.directory, 'blobs'))) {
      if (/^[a-f0-9]{64}\.txt$/.test(name) && !references.has(name.slice(0, -4))) await fs.unlink(path.join(context.directory, 'blobs', name));
    }
  }

  async readFiles(context, paths) {
    if (!Array.isArray(paths) || paths.length > 200) throw new Error('恢复读取文件数量无效');
    const documents = [], errors = [];
    let total = 0;
    for (const relative of [...new Set(paths)]) {
      try {
        relativeSource(relative);
        await noLinks(context.root, relative);
        const file = path.join(context.root, ...relative.split('/'));
        let bytes = Buffer.alloc(0), exists = false;
        try {
          const stat = await fs.stat(file);
          if (!stat.isFile() || stat.size > MAX_TEXT) throw new Error('文件过大或不是文本文件');
          bytes = await fs.readFile(file); exists = true;
        } catch (error) { if (error.code !== 'ENOENT') throw error; }
        total += bytes.length;
        if (bytes.length > MAX_TEXT || total > MAX_STATE || bytes.includes(0)) throw new Error('文件过大或不是文本文件');
        const bom = bytes.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]));
        const content = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bom ? bytes.subarray(3) : bytes);
        documents.push({ path: relative, content, hash: hash(bytes), exists, bom, newline: bytes.includes(Buffer.from('\r\n')) ? '\r\n' : '\n' });
      } catch (error) { errors.push({ path: typeof relative === 'string' ? relative : '', message: error.message }); }
    }
    return { documents, errors };
  }
}

module.exports = { RecoveryStore };
