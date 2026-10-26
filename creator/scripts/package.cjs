'use strict';
const fs=require('node:fs'),path=require('node:path');
const {build,Platform,Arch}=require('electron-builder');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),pkg=require('../package.json');
require('./markdown-licenses.cjs').notices(root);
const sdk=path.resolve(process.env.CREATOR_RENPY_SDK||path.join(root,'..','renpy-8.5.3-sdk'));
if(!fs.existsSync(path.join(root,'ai-runtime','manifest.json')))throw new Error('Build the pinned AI runtime first; see docs/AI-DSH.md.');
if(!fs.existsSync(path.join(sdk,'renpy.py'))||!fs.existsSync(path.join(sdk,'lib','py3-windows-x86_64','python.exe'))){
 throw new Error('RenPy 8.5.3 SDK not found. Set CREATOR_RENPY_SDK to its directory.');
}
build({projectDir:root,targets:Platform.WINDOWS.createTarget('dir',Arch.x64),config:{extraResources:[]}}).then(()=>{
 const release=pkg.build.directories.output;
 const assembled=spawnSync(path.join(sdk,'lib/py3-windows-x86_64/python.exe'),['-B',path.join(root,'scripts/assemble-resources.py'),root,sdk,path.join(root,release,'win-unpacked/resources')],{stdio:'inherit',windowsHide:true});
 if(assembled.error)throw assembled.error;if(assembled.status!==0)throw new Error('Runtime assembly failed.');
 const launcher='@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\start-portable.ps1"\r\nif errorlevel 1 (\r\n pause\r\n exit /b 1\r\n)\r\n';
 fs.writeFileSync(path.join(root,'启动IDE.cmd'),launcher);
 const archive=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',path.join(root,'scripts','package-portable.ps1')],{cwd:root,stdio:'inherit',windowsHide:true});
 if(archive.error)throw archive.error;
 if(archive.status!==0)throw new Error('Portable archive creation failed.');
 console.log('Portable IDE and launcher ready: '+release);
}).catch(error=>{console.error(error);process.exit(1);});
