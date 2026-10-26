'use strict';
const fs=require('node:fs'),path=require('node:path'),root=path.resolve(__dirname,'..');
fs.writeFileSync(path.join(root,'dist/build-version.json'),JSON.stringify({version:require('../package.json').version}));
