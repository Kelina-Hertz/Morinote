export interface SourceDocument {path:string;content:string;hash:string;exists?:boolean;bom?:boolean;newline?:string}
export interface SourceLocation {path:string;line:number;column?:number;start?:number;end?:number;hash?:string}
export interface ConfigField extends SourceLocation {id:string;label:string;name:string;value:unknown;editable:boolean;expression:string;tuple?:boolean;assetKind?:string;references?:string[]}
export interface ConfigEntry extends ConfigField {key:string;fields:ConfigField[];rowStart?:number}
export interface ConfigTable extends ConfigField {entries:ConfigEntry[];container:string}
export interface ConfigGroup {id:string;title:string;fields:ConfigField[];tables:ConfigTable[];sources:string[];actions?:{id:string;title:string;path:string;line:number;fields:ConfigField[];label?:string}[]}
export interface NativeFlowNode {id:string;type:string;title:string;group:string;label:string;source:SourceLocation;role?:'story'|'conversation'|'system'|'test';terminal?:boolean;optionTitles?:string[];unresolved?:boolean;calls?:(NativeFlowNode&{target?:string})[]}
export interface NativeFlow {nodes:NativeFlowNode[];edges:{id:string;source:string;target:string;kind:string;title:string;callSite?:string}[];groups:{id:string;title:string}[];story?:NativeFlow;storyDetail?:NativeFlow;sourceCopies?:{path:string;original:string}[]}
export interface TreeNode {name:string;path:string;children?:TreeNode[];text?:boolean}
export interface WorkspaceIndex {tree:TreeNode[];config:{groups:ConfigGroup[];bindings:Record<string,ConfigField>};flow:NativeFlow}
export interface Category {id:string;name:string;parent:string|null}
export type NativeOperation=(adapter:'config'|'flow'|'stage'|'assets',operation:Record<string,unknown>)=>Promise<void>;
