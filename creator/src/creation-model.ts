import type {Project} from './types';
import {sceneTitle} from './scene-titles';
import {preferredLabels} from './source-labels';

export type SceneLabel=NonNullable<Project['nativeRenpy']>['labels'][number];
export interface ChoiceOption {text:string;target:string}
export interface PreviewFields {args:string;state:string;initialize:string}

export function sceneChoices(project:Project){
 const labels=preferredLabels(project);
 const titles=labels.map(label=>sceneTitle(project,label.id));
 const titleCounts=new Map<string,number>(),nameCounts=new Map<string,number>();
 labels.forEach((label,index)=>{titleCounts.set(titles[index],(titleCounts.get(titles[index])||0)+1);nameCounts.set(label.name,(nameCounts.get(label.name)||0)+1);});
 return labels.map((label,index)=>({label,title:titles[index],caption:titleCounts.get(titles[index])!>1?`${titles[index]} · ${label.file}`:titles[index],ambiguous:nameCounts.get(label.name)!>1}));
}

export function parseChoiceJson(text:string):ChoiceOption[]{
 let value:unknown;
 try{value=JSON.parse(text);}catch{throw new Error('选项 JSON 格式不正确，请修正或放弃 JSON 修改。');}
 if(!Array.isArray(value)||!value.length||value.some(o=>!o||typeof o!=='object'||typeof o.text!=='string'||typeof o.target!=='string'))throw new Error('选项 JSON 需为至少包含一项的数组，每项填写 text 和 target 字符串。');
 return value.map(o=>({text:o.text,target:o.target}));
}

export function choiceErrors(options:ChoiceOption[],labels:SceneLabel[]){
 return options.map(option=>({text:option.text.trim()?'':'请填写选项文字。',target:labels.filter(l=>l.name===option.target).length===1?'':'请选择存在且标签唯一的目标场景。'}));
}

export function sceneFieldErrors(title:string,name:string,path:string,labels:SceneLabel[]){
 return {title:title.trim().length>0&&title.trim().length<=120?'':'场景名称需为 1 至 120 个非空字符。',
  name:/^[A-Za-z_]\w*$/.test(name)&&!labels.some(l=>l.name===name)?'':'标签需以英文字母或下划线开头，且不能与已有标签重名。',
  path:path.startsWith('game/')&&path.endsWith('.rpy')&&!path.includes(':')&&!path.includes('\\')&&!path.split('/').some(p=>!p||p==='.'||p==='..'||['.git','.creator','sources','cache','saves','__pycache__'].includes(p.toLowerCase()))?'':'源码文件需位于 game/ 内，并以 .rpy 结尾，不能使用内部目录或上级路径。'};
}

export function newSceneLabel(labels:SceneLabel[]){
 let name='';
 do{name='scene_'+crypto.randomUUID().replaceAll('-','').slice(0,12);}while(labels.some(l=>l.name===name));
 return name;
}

export function parsePreviewFields(fields:PreviewFields){
 function read(text:string,fallback:string,label:string,array:boolean):unknown{
  let value:unknown;
  try{value=JSON.parse(text.trim()||fallback);}catch{throw new Error(`${label} JSON 格式不正确，请打开高级设置修正。`);}
  if(array?!Array.isArray(value):!value||typeof value!=='object'||Array.isArray(value))throw new Error(`${label}需为 JSON ${array?'数组':'对象'}，请打开高级设置修正。`);
  return value;
 }
 const args=read(fields.args,'[]','标签参数',true) as unknown[],state=read(fields.state,'{}','测试状态',false) as Record<string,unknown>,initialize=read(fields.initialize,'[]','前置调用',true) as unknown[];
 if(initialize.some(name=>typeof name!=='string'))throw new Error('前置调用需填写标签名称组成的 JSON 数组。');
 if(Object.keys(state).some(key=>!/^(?:persistent\.)?[A-Za-z_]\w*$/.test(key)||key.startsWith('_')))throw new Error('测试状态的变量名无效，请打开高级设置修正。');
 return {args,state,initialize:initialize as string[]};
}

export function hasPreviewSettings(fields:PreviewFields){
 try{const value=parsePreviewFields(fields);return !!(value.args.length||Object.keys(value.state).length||value.initialize.length);}catch{return true;}
}
