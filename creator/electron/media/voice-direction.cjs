'use strict';
const {fail}=require('./common.cjs');
const EFFECTS=['laughs','chuckle','coughs','clear-throat','groans','breath','pant','inhale','exhale','gasps','sniffs','sighs','snorts','burps','lip-smacking','humming','hissing','emm','sneezes'];
const effect=new RegExp('\\(('+EFFECTS.join('|')+')\\)','g');
function spokenText(value){return value.replace(/<#(?:\d+(?:\.\d{1,2})?)#>/g,'').replace(effect,'').replace(/\s/g,'');}
function voiceRequest(displayText,voice={}){
 if(typeof displayText!=='string'||!displayText.trim())fail('INVALID_REQUEST','配音需要原台词。');
 const text=voice.text||displayText;
 if(typeof text!=='string'||spokenText(text)!==displayText.replace(/\s/g,''))fail('VOICE_TEXT_CHANGED','合成文字只能添加受支持的停顿、语气标记；读音请使用 pronunciation，导演说明不能进入朗读正文。');
 for(const match of text.matchAll(/<#([^<>]+)#>/g)){const seconds=Number(match[1]);if(!/^\d+(?:\.\d{1,2})?$/.test(match[1])||seconds<.01||seconds>99.99)fail('INVALID_REQUEST','停顿范围为 0.01–99.99 秒，最多两位小数。');}
 if(/^(?:\s*)<#|#>(?:\s*)$|#>\s*<#/.test(text))fail('INVALID_REQUEST','停顿必须位于台词之间，不能连续设置。');
 const request={text};for(const key of ['voiceId','speed','emotion','volume','pitch','pronunciation'])if(voice[key]!==undefined)request[key]=voice[key];
 return request;
}
function direction(voice={}){
 const director=voice.director??'';if(typeof director!=='string'||director.length>8000)fail('INVALID_REQUEST','导演说明应为 8000 字以内的文本。');
 const unexpressed=voice.unexpressed??[];if(!Array.isArray(unexpressed)||unexpressed.some(v=>typeof v!=='string'||v.length>1000))fail('INVALID_REQUEST','未落实的导演要求应为文本列表。');
 return {director,unexpressed};
}
module.exports={voiceRequest,direction,spokenText,EFFECTS};
