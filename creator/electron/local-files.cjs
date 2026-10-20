'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function atomicWrite(file,data){fs.mkdirSync(path.dirname(file),{recursive:true});const temp=file+'.'+crypto.randomUUID()+'.tmp';try{const fd=fs.openSync(temp,'w');try{fs.writeFileSync(fd,data);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(temp,file);}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}}
module.exports={atomicWrite};
