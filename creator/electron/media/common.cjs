'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {atomicWrite}=require('../ai-storage.cjs');
class MediaError extends Error{constructor(code,message){super(message);this.code=code;}}
const fail=(code,message)=>{throw new MediaError(code,message);};
function canonical(value){if(Array.isArray(value))return value.map(canonical);if(value&&typeof value==='object'&&!Buffer.isBuffer(value))return Object.fromEntries(Object.keys(value).sort().filter(k=>value[k]!==undefined).map(k=>[k,canonical(value[k])]));return value;}
const digest=value=>crypto.createHash('sha256').update(Buffer.isBuffer(value)?value:JSON.stringify(canonical(value))).digest('hex');
const textHash=value=>digest(String(value).replace(/\r\n?/g,'\n'));
const id=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(value);
function sanitize(error,secrets=[]){let message=String(error?.message||error||'操作失败');for(const secret of secrets.filter(Boolean))message=message.split(secret).join('[已隐藏]');return message.replace(/Bearer\s+\S+/gi,'Bearer [已隐藏]').replace(/\b(?:sk-|sk_)[A-Za-z0-9_-]{8,}/g,'[已隐藏]').slice(0,1200);}
function readJSON(file,fallback){if(!fs.existsSync(file))return structuredClone(fallback);try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch{fail('LEDGER_CORRUPT','媒体记录无法读取，已停止新的收费提交。请保留记录并恢复备份。');}}
function saveJSON(file,value){atomicWrite(file,JSON.stringify(value,null,2));}
function checkAbort(signal){if(signal?.aborted)fail('CANCELLED','已取消；已提交的远端请求仍可能计费。');}
function inside(root,target){const relative=path.relative(path.resolve(root),path.resolve(target));return relative!==''&&!relative.startsWith('..'+path.sep)&&relative!=='..'&&!path.isAbsolute(relative);}
function regular(root,target){if(!inside(root,target))fail('INVALID_PATH','资源必须位于当前工程内。');let current=path.resolve(root);for(const part of path.relative(current,path.resolve(target)).split(path.sep)){current=path.join(current,part);if(fs.existsSync(current)&&fs.lstatSync(current).isSymbolicLink())fail('INVALID_PATH','生成资源路径不能包含链接。');}if(!fs.statSync(target).isFile())fail('INVALID_PATH','资源不是普通文件。');}
async function limitedBody(response,limit=32*1024*1024){if(Number(response.headers?.get('content-length')||0)>limit)fail('OUTPUT_TOO_LARGE','服务返回的内容超过限制。');const parts=[];let size=0;for await(const chunk of response.body||[]){size+=chunk.length;if(size>limit)fail('OUTPUT_TOO_LARGE','服务返回的内容超过限制。');parts.push(Buffer.from(chunk));}return Buffer.concat(parts);}
function imageInfo(data){let width,height,extension,mime;
 if(data.length>=24&&data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))){width=data.readUInt32BE(16);height=data.readUInt32BE(20);extension='png';mime='image/png';}
 else if(data.length>=12&&data[0]===255&&data[1]===216){let p=2;while(p+8<data.length){if(data[p++]!==255)continue;const marker=data[p++];if(marker===217||marker===218)break;if(marker===216||marker===1||marker>=208&&marker<=215)continue;const length=data.readUInt16BE(p);if(length<2||p+length>data.length)break;if([192,193,194].includes(marker)){height=data.readUInt16BE(p+3);width=data.readUInt16BE(p+5);break;}p+=length;}extension='jpg';mime='image/jpeg';}
 else fail('INVALID_MEDIA','图片必须是可解码的 PNG 或 JPEG。');
 if(!width||!height||width*height>16777216||width>8192||height>8192)fail('INVALID_MEDIA','图片尺寸无效或超过 1600 万像素。');return {width,height,extension,mime};
}
function audioInfo(data){if(data.length<32)fail('INVALID_MEDIA','音频为空或文件头无效。');if(data.subarray(0,4).toString()==='RIFF'&&data.subarray(8,12).toString()==='WAVE')return {extension:'wav',mime:'audio/wav'};if(data.subarray(0,3).toString()==='ID3'||data[0]===255&&(data[1]&224)===224)return {extension:'mp3',mime:'audio/mpeg'};fail('INVALID_MEDIA','音频不是 MP3 或 WAV，拒绝将响应文本保存为音频。');}
async function validateMedia(data,kind,decode){if(!Buffer.isBuffer(data)||!data.length||data.length>(kind==='image'?20:10)*1024*1024)fail('INVALID_MEDIA','产物为空或超过文件大小限制。');const info=kind==='image'?imageInfo(data):audioInfo(data);if(decode){const decoded=await decode(data,kind,info);if(kind==='voice'){if(!decoded?.duration||decoded.duration>120)fail('INVALID_MEDIA','配音无法解码或超过单句 120 秒限制。');info.duration=decoded.duration;}}return {...info,sha256:digest(data),bytes:data.length};}
module.exports={MediaError,fail,canonical,digest,textHash,id,sanitize,readJSON,saveJSON,checkAbort,inside,regular,limitedBody,imageInfo,audioInfo,validateMedia};
