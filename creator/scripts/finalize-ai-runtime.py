"""Assemble Windows binaries with standard-library copies, without launching them."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

plan=json.loads(Path(sys.argv[1]).read_text('utf-8'))
root=Path(plan['root']).resolve();stage=Path(plan['staging']).resolve();output=Path(plan['output']).resolve()
if not stage.is_relative_to(root/'.cache') or output!=root/'ai-runtime':raise ValueError('Invalid runtime assembly paths.')
source=Path(plan['source']).resolve()
(stage/'node').mkdir(exist_ok=True)
shutil.copy2(plan['node'],stage/'node/node.exe');shutil.copy2(plan['nodeLicense'],stage/'node/LICENSE')
shutil.copytree(plan['pwsh'],stage/'pwsh',dirs_exist_ok=True)
shutil.copytree(root/'ai/plugin',stage/'plugin',dirs_exist_ok=True)
shutil.copytree(root/'ai/skills',stage/'skills',dirs_exist_ok=True)
licenses=stage/'licenses';licenses.mkdir(exist_ok=True)
for name in ['LICENSE','THIRD_PARTY_NOTICES.md']:shutil.copy2(source/name,licenses/('DSH-'+name))
(licenses/'dependency-inventory.json').write_text(json.dumps(plan['inventory'],ensure_ascii=False,indent=2),encoding='utf-8')
def sha(file):
    digest=hashlib.sha256()
    with Path(file).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
manifest={'version':plan['version'],'commit':plan['pin'],'node':'25.8.2','powershell':'7.6.5','platform':'win32-x64',
    'lockfileSha256':sha(source/'pnpm-lock.yaml'),'nodeSha256':sha(stage/'node/node.exe'),'pwshSha256':sha(stage/'pwsh/pwsh.exe'),'packages':len(plan['inventory'])}
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
if output.exists():os.replace(output,root/'.cache'/('previous-ai-runtime-'+uuid.uuid4().hex))
os.replace(stage,output)
print('Assembled AI runtime with Windows binaries and licenses.',flush=True)
