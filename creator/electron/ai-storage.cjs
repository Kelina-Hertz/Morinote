'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { providerURL } = require('./security.cjs');

const DEFAULTS = {
  openai: { model: 'gpt-5.4', baseUrl: 'https://api.openai.com/v1' },
  anthropic: { model: 'claude-sonnet-4-6', baseUrl: 'https://api.anthropic.com/v1' },
  deepseek: { model: 'deepseek-flash', baseUrl: 'https://api.deepseek.com' },
};
const PROVIDER_NAMES={deepseek:'DeepSeek',openai:'OpenAI',anthropic:'Anthropic'};

function atomicWrite(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.${crypto.randomUUID()}.tmp`;
  try { const descriptor=fs.openSync(temp,'wx',0o600);try{fs.writeFileSync(descriptor,data);fs.fsyncSync(descriptor);}finally{fs.closeSync(descriptor);}fs.renameSync(temp, file); }
  finally { if (fs.existsSync(temp)) fs.unlinkSync(temp); }
}

class SecureStore {
  constructor(directory, safeStorage) {
    this.directory = directory;
    this.safeStorage = safeStorage;
    this.keyStates = new Map();
    this.file = path.join(directory, 'ai-settings.json');
    this.data = { autoSave:false,approvalMode:'ask',provider: 'deepseek', providers: structuredClone(DEFAULTS) };
    if (fs.existsSync(this.file)) {try {
      const previous = JSON.parse(fs.readFileSync(this.file, 'utf8'));
      this.data.autoSave=previous.autoSave===true;
      this.data.approvalMode=previous.approvalMode==='reviewer'?'reviewer':'ask';
      if (Object.hasOwn(DEFAULTS, previous.provider)) this.data.provider = previous.provider;
      for (const provider of Object.keys(DEFAULTS)) Object.assign(this.data.providers[provider], previous.providers?.[provider]);
    }catch {this.warning='模型设置无法读取，请重新配置；原文件仍然保留。';}
    }
  }
  preferences(values){if('autoSave' in values){if(typeof values.autoSave!=='boolean')throw new Error('设置需为开关');this.data.autoSave=values.autoSave;}if('approvalMode' in values){if(!['ask','reviewer'].includes(values.approvalMode))throw new Error('无效审批方式');this.data.approvalMode=values.approvalMode;}atomicWrite(this.file,JSON.stringify(this.data,null,2));return this.settings();}
  available() {
    return this.safeStorage.isEncryptionAvailable() &&
      (process.platform !== 'linux' || this.safeStorage.getSelectedStorageBackend?.() !== 'basic_text');
  }
  settings() {
    return { storageWarning:this.warning,autoSave:this.data.autoSave,approvalMode:this.data.approvalMode,provider: this.data.provider, secureStorage: this.available(), providers: Object.fromEntries(Object.entries(this.data.providers)
      .map(([id, value]) => {const state=this.keyState(id,value);return [id,{model:value.model,baseUrl:value.baseUrl,hasKey:state.status==='ready',credentialStatus:state.status,...(state.error?{keyError:state.error}:{})}];})) };
  }
  keyError(provider){return `${PROVIDER_NAMES[provider]||provider} 已保存的 API Key 无法在当前本机配置中解密，请在“模型设置”中重新填写并保存。原有密文和对话记录已保留。`;}
  keyState(provider,value=this.data.providers[provider]){
    if(!value?.encryptedKey)return {status:'missing'};
    if(!this.available())return {status:'unavailable',error:'系统安全存储暂不可用，无法读取已保存的 API Key。'};
    const cached=this.keyStates.get(provider);if(cached?.cipher===value.encryptedKey)return cached;
    let state;
    try{const key=this.safeStorage.decryptString(Buffer.from(value.encryptedKey,'base64'));if(!key.trim())throw new Error('Empty key');state={status:'ready'};}
    catch{state={status:'unreadable',error:this.keyError(provider)};}
    this.keyStates.set(provider,{cipher:value.encryptedKey,...state});return state;
  }
  configure({ provider, model, baseUrl, key }) {
    if (!Object.hasOwn(DEFAULTS, provider)) throw new Error('不支持的服务商');
    const next = { ...this.data.providers[provider] };
    if (model !== undefined) {
      if (typeof model !== 'string' || !model.trim() || model.length > 200) throw new Error('请填写模型名称');
      next.model = model.trim();
    }
    if (baseUrl !== undefined) next.baseUrl = providerURL(baseUrl || DEFAULTS[provider].baseUrl);
    if (key !== undefined) {
      if (typeof key !== 'string' || key.length > 8192) throw new Error('API Key 格式不正确');
      if (key.trim()) {
        if (!this.available()) throw new Error('系统安全存储不可用，不能保存 API Key');
        next.encryptedKey = this.safeStorage.encryptString(key.trim()).toString('base64');
        if(this.safeStorage.decryptString(Buffer.from(next.encryptedKey,'base64'))!==key.trim())throw new Error('本机安全存储保存校验失败，原 Key 未被替换。');
      } else delete next.encryptedKey;
    }
    const saved={...this.data,provider,providers:{...this.data.providers,[provider]:next}};
    atomicWrite(this.file, JSON.stringify(saved, null, 2));
    this.data=saved;this.keyStates.delete(provider);this.warning=undefined;
    return this.settings();
  }
  config(provider = this.data.provider) {
    const value = this.data.providers[provider];
    if (!value || !value.encryptedKey) throw new Error('请先为所选服务商填写 API Key');
    if (!this.available()) throw new Error('系统安全存储不可用');
    let key;
    try{key=this.safeStorage.decryptString(Buffer.from(value.encryptedKey,'base64'));if(!key.trim())throw new Error('Empty key');}
    catch{this.keyStates.set(provider,{cipher:value.encryptedKey,status:'unreadable',error:this.keyError(provider)});throw new Error(this.keyError(provider));}
    return { provider, model: value.model, baseUrl: providerURL(value.baseUrl), key };
  }
  saveSession(session) {
    if (!this.available()) throw new Error('系统安全存储不可用，无法保存 AI 恢复记录');
    const name = this.sessionName(session.taskId);
    atomicWrite(name, this.safeStorage.encryptString(JSON.stringify(session)));
  }
  sessionName(taskId) {
    if (typeof taskId !== 'string' || !/^[a-zA-Z0-9_-]{1,120}$/.test(taskId)) throw new Error('任务 ID 无效');
    return path.join(this.directory, 'ai-sessions', `${taskId}.bin`);
  }
  loadSession(taskId) {
    const file = this.sessionName(taskId);
    if (!fs.existsSync(file)) return null;
    if (!this.available()) throw new Error('系统安全存储不可用');
    return JSON.parse(this.safeStorage.decryptString(fs.readFileSync(file)));
  }
}

module.exports = { SecureStore, DEFAULTS, atomicWrite };
