'use strict';
const {Seedream}=require('./providers/seedream.cjs');
const {MiniMax}=require('./providers/minimax.cjs');
const {fail}=require('./common.cjs');
class ProviderRegistry{constructor(options={}){this.providers={seedream:new Seedream(options),minimax:new MiniMax(options)};}get(kind){if(['music','sfx','video'].includes(kind))fail('CAPABILITY_NOT_IMPLEMENTED','该生成能力待开发，可选择工程中已有素材。');const provider=kind==='image'?'seedream':kind==='voice'?'minimax':null;if(!provider)fail('CAPABILITY_NOT_IMPLEMENTED','不支持的媒体生成能力。');return {id:provider,provider:this.providers[provider]};}describe(settings){return [{id:'seedream',kinds:['image'],capabilities:['background','cg','image','reference-edit'],availability:settings.providers.seedream.hasKey?'ready':'unconfigured'},{id:'minimax',kinds:['voice'],capabilities:['tts','system-voice','emotion','pronunciation'],availability:settings.providers.minimax.hasKey?'ready':'unconfigured'},...['music','sfx','video'].map(kind=>({id:kind,kinds:[kind],capabilities:[],availability:'planned'}))];}}
module.exports={ProviderRegistry};
