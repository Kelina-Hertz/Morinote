'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn, execFile } = require('node:child_process');
const { promisify } = require('node:util');
const execute = promisify(execFile);

class RenpyLauncher {
  constructor(sdk) { this.sdk = sdk; this.child = null; this.project = null; this.opening = false; }

  async open(root, assertCurrent) {
    if (this.opening) throw new Error('Ren’Py 启动器正在打开，请稍候。');
    assertCurrent();
    if (this.child && this.child.exitCode === null && this.child.signalCode === null) {
      return { status: 'already-open', projectPath: root, selectedProject: this.project };
    }
    this.opening = true;
    try {
      if (!fs.statSync(path.join(root, 'game'), { throwIfNoEntry: false })?.isDirectory()) throw new Error('当前目录不是可直接运行的 Ren’Py 原工程，请直接打开包含 game 的原工程目录。');
      const python = path.join(this.sdk, 'lib', 'py3-windows-x86_64', 'python.exe');
      const script = path.join(this.sdk, 'renpy.py'), launcher = path.join(this.sdk, 'launcher');
      if (!fs.existsSync(python) || !fs.existsSync(script) || !fs.existsSync(path.join(launcher, 'game'))) throw new Error('捆绑的 Ren’Py 启动器不完整，请重新安装制作器。');
      const env = { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1' };
      for (const name of Object.keys(env)) if (name.startsWith('CREATOR_') || name.startsWith('SW_PREVIEW_') || ['RENPY_PATH_TO_SAVES', 'RENPY_SKIP_MAIN_MENU', 'RENPY_SKIP_SPLASHSCREEN', 'RENPY_SEARCHPATH'].includes(name)) delete env[name];
      // Use the SDK's own command; no generated game or IDE export pipeline.
      await execute(python, [script, launcher, 'set_project', root], { cwd: this.sdk, env, windowsHide: true, timeout: 30000, maxBuffer: 128 * 1024 }).catch(error => {
        throw new Error('无法在 Ren’Py 启动器中选择项目：' + String(error.stderr || error.message).slice(-2000));
      });
      assertCurrent();
      const child = spawn(python, [script, launcher], { cwd: this.sdk, env, windowsHide: true, detached: true, stdio: 'ignore' });
      await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
      this.child = child; this.project = root;
      child.once('exit', () => { if (this.child === child) { this.child = null; this.project = null; } });
      child.unref();
      return { status: 'opened', projectPath: root, selectedProject: root };
    } finally { this.opening = false; }
  }
}

module.exports = { RenpyLauncher };
