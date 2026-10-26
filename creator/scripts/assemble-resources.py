"""Sequential package assembly; retries Windows scanner locks, never runs a game."""
from pathlib import Path
import hashlib
import shutil
import sys
import time

root=Path(sys.argv[1]).resolve();sdk=Path(sys.argv[2]).resolve();target=Path(sys.argv[3]).resolve()
if not target.is_relative_to(root) or target.name!='resources':raise ValueError('Invalid package destination.')
def digest(file):
    value=hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.digest()
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.is_file() and source.stat().st_size==destination.stat().st_size and digest(source)==digest(destination):return
    for attempt in range(20):
        try:shutil.copy2(source,destination);return
        except OSError:
            if attempt==19:raise
            time.sleep(.25)
for source,name in [(root/'backend','backend'),(root/'ai-runtime','ai-runtime'),(sdk,'renpy-sdk')]:
    if not source.is_dir():raise ValueError('Missing runtime: '+str(source))
    for file in source.rglob('*'):
        if not file.is_file():continue
        rel=file.relative_to(source);parts=rel.parts
        if {'__pycache__','saves','screenshots','cache'}&set(parts) or file.name in {'log.txt','traceback.txt','errors.txt'}:continue
        if name=='backend' and ('tests' in parts or file.suffix=='.pyc'):continue
        if name=='renpy-sdk' and parts[0]=='tmp':continue
        if name=='ai-runtime' and len(parts)>3 and parts[:2]==('node_modules','@deepseek-ai') and ('src' in parts[3:] or 'client' in parts[3:] and 'types' in parts[3:]):continue
        copy(file,target/name/rel)
    print('Assembled '+name,flush=True)
# Keep trusted Morinote instructions in sync without recompiling the pinned SDK.
for folder in ['plugin','skills']:
    source=root/'ai'/folder
    for file in source.rglob('*'):
        if file.is_file():copy(file,target/'ai-runtime'/folder/file.relative_to(source))
copy(root/'electron/dsh-worker.mjs',target/'dsh-worker.mjs')
copy(root/'docs/MARKDOWN-LICENSES.md',target/'licenses/MARKDOWN-LICENSES.md')
for relative in ['dsh-worker.mjs','ai-runtime/plugin/ide-filesystem.mjs','ai-runtime/node_modules/@deepseek-ai/dsh-fs-observation-policy/lib/index.js','backend/server.py','ai-runtime/manifest.json','ai-runtime/plugin/knowledge.mjs','ai-runtime/skills/morinote-ide/SKILL.md','ai-runtime/node/node.exe','ai-runtime/pwsh/pwsh.exe','ai-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js','ai-runtime/node_modules/@deepseek-ai/dsh-sdk-client/lib/index.js','ai-runtime/node_modules/@deepseek-ai/dsh-sandbox-windows-acl/lib/runner.js','ai-runtime/node_modules/@deepseek-ai/dsh-skill/lib/index.js','ai-runtime/node_modules/@deepseek-ai/dsh-skill-filesystem/lib/index.js','ai-runtime/node_modules/@deepseek-ai/dsh-tool-skill/lib/index.js','renpy-sdk/renpy.py']:
    if not (target/relative).is_file():raise ValueError('Incomplete package: '+relative)
