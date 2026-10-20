'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('creator', Object.freeze({
  request: (path, body) => ipcRenderer.invoke('creator:request', path, body),
  pickFolder: () => ipcRenderer.invoke('creator:pickFolder'),
  pickFiles: (kind) => ipcRenderer.invoke('creator:pickFiles', kind),
  mediaUrl: (id) => ipcRenderer.invoke('creator:mediaUrl', id),
  recovery: (method, payload) => ipcRenderer.invoke('creator:recovery', method, payload),
  openRenpy: (payload) => ipcRenderer.invoke('creator:openRenpy', payload),
  onPrepareClose: (callback) => {
    if (typeof callback !== 'function') throw new TypeError('callback required');
    const listener = async (_event, request) => {
      if (!request || typeof request.id !== 'string') return;
      try {
        await callback();
        ipcRenderer.send('creator:close-result', { id: request.id, ok: true });
      } catch (error) {
        ipcRenderer.send('creator:close-result', { id: request.id, ok: false, error: String(error?.message || error) });
      }
    };
    ipcRenderer.on('creator:prepare-close', listener);
    ipcRenderer.send('creator:recovery-ready', true);
    return () => {
      ipcRenderer.removeListener('creator:prepare-close', listener);
      ipcRenderer.send('creator:recovery-ready', false);
    };
  },
  onCloseCancelled: (callback) => {
    if (typeof callback !== 'function') throw new TypeError('callback required');
    const listener = () => callback();
    ipcRenderer.on('creator:close-cancelled', listener);
    return () => ipcRenderer.removeListener('creator:close-cancelled', listener);
  },

}));
