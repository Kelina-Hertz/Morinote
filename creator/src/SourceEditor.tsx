import {useEffect,useRef} from 'react';
import type {editor as MonacoEditor} from 'monaco-editor';
import type {SourceDocument,SourceLocation} from './native-types';
import {currentProjectSession} from './api';
const models=new Map<string,MonacoEditor.ITextModel>();

let runtime:Promise<typeof import('monaco-editor/esm/vs/editor/editor.api.js')>|undefined;
async function loadEditor(){
 if(!runtime)runtime=(async()=>{
  const [{default:Worker},monaco]=await Promise.all([import('monaco-editor/esm/vs/editor/editor.worker.js?worker'),import('monaco-editor/esm/vs/editor/editor.api.js')]);
  (self as unknown as {MonacoEnvironment:unknown}).MonacoEnvironment={getWorker:()=>new Worker()};
  await import('monaco-editor/esm/vs/basic-languages/python/python.contribution.js');
  monaco.languages.register({id:'json'});
  monaco.languages.setMonarchTokensProvider('json',{tokenizer:{root:[[/"(?:\\.|[^"\\])*"(?=\s*:)/,'string.key'],[/"(?:\\.|[^"\\])*"/,'string'],[/\b(?:true|false|null)\b/,'keyword'],[/-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/,'number']]}});
  monaco.languages.register({id:'renpy'});
  monaco.languages.setMonarchTokensProvider('renpy',{tokenizer:{root:[[/#.*/,'comment'],[/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/,'string'],[/\b(label|define|default|init|python|screen|transform|image|scene|show|hide|with|at|as|play|stop|queue|voice|menu|if|elif|else|while|jump|call|return|pause|parallel|linear|ease|True|False|None)\b/,'keyword'],[/\b\d+(?:\.\d+)?\b/,'number']]}});
  monaco.languages.setLanguageConfiguration('renpy',{comments:{lineComment:'#'},brackets:[['(',')'],['[',']'],['{','}']],autoClosingPairs:[{open:'(',close:')'},{open:'[',close:']'},{open:'{',close:'}'}]});
  return monaco;
 })();
 return runtime;
}

export default function SourceEditor({document,onChange,onSave,onLocation,location}:{document:SourceDocument;onChange:(value:string)=>void;onSave:()=>void;onLocation?:(line:number,column:number)=>void;location?:SourceLocation|null}){
 const host=useRef<HTMLDivElement>(null),instance=useRef<MonacoEditor.IStandaloneCodeEditor|null>(null),change=useRef(onChange),save=useRef(onSave),locate=useRef(onLocation);
 change.current=onChange;save.current=onSave;locate.current=onLocation;
 const current=useRef(document);current.current=document;
 useEffect(()=>{let cancelled=false;let model:MonacoEditor.ITextModel|undefined;const cleanup:{dispose:()=>void}[]=[];
  void loadEditor().then(monaco=>{if(cancelled||!host.current)return;
   const language=document.path.endsWith('.rpy')?'renpy':document.path.endsWith('.py')?'python':document.path.endsWith('.json')?'json':'plaintext';
   const key=currentProjectSession()+':'+document.path;
   for(const [other,old] of models)if(!other.startsWith(currentProjectSession()+':')){old.dispose();models.delete(other);}
   model=models.get(key)||monaco.editor.createModel(current.current.content,language);
   models.set(key,model);
   if(model.getValue()!==current.current.content)model.setValue(current.current.content);
   const ed=monaco.editor.create(host.current,{model,theme:'vs-dark',automaticLayout:true,fontSize:14,tabSize:4,insertSpaces:true,minimap:{enabled:false},scrollBeyondLastLine:false,wordWrap:'off',ariaLabel:'项目源码编辑器'});instance.current=ed;
   cleanup.push(ed.onDidChangeModelContent(()=>change.current(instance.current!.getValue())));
   cleanup.push(ed.onDidChangeCursorPosition(e=>locate.current?.(e.position.lineNumber,e.position.column)));
   ed.addCommand(monaco.KeyMod.CtrlCmd|monaco.KeyCode.KeyS,()=>save.current());
   if(location?.path===document.path){ed.setPosition({lineNumber:location.line,column:location.column||1});ed.revealLineInCenter(location.line);}
  });
  return()=>{cancelled=true;cleanup.forEach(x=>x.dispose());instance.current?.dispose();instance.current=null;};
 },[document.path]);
 useEffect(()=>{const ed=instance.current;if(ed&&ed.getValue()!==document.content){ed.executeEdits('visual-edit',[{range:ed.getModel()!.getFullModelRange(),text:document.content,forceMoveMarkers:true}]);ed.pushUndoStop();}},[document.content]);
 useEffect(()=>{const ed=instance.current;if(ed&&location?.path===document.path&&(ed.getPosition()?.lineNumber!==location.line||(location.column!==undefined&&ed.getPosition()?.column!==location.column))){ed.setPosition({lineNumber:location.line,column:location.column||1});ed.revealLineInCenter(location.line);}},[location?.path,location?.line,location?.column,document.path]);
 return <div className="source-editor" ref={host}/>;
}
