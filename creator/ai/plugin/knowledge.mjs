// Bundled, read-only instructions. Never resolves a path supplied by the model.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const skillName='morinote-ide';
export const knowledgeVersion='2.1.0';
export const sections=Object.freeze(['architecture','tracks','systems','assets','verification']);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','skills',skillName);

export function readGuide(section){
 if(!sections.includes(section))throw new Error('未知 IDE 指南，请使用工具列出的 section。');
 const base=fs.realpathSync(root),file=fs.realpathSync(path.join(base,'references',section+'.md'));
 if(!file.startsWith(base+path.sep)||!fs.statSync(file).isFile()||fs.statSync(file).size>128*1024)throw new Error('IDE 指南资源位置或大小无效。');
 const content=fs.readFileSync(file,'utf8');
 return {skill:skillName,version:knowledgeVersion,section,resource:'references/'+section+'.md',hash:crypto.createHash('sha256').update(content).digest('hex'),content};
}
