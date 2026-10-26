import type {SourceDocument,SourceLocation} from './native-types';
import type {SourceBuffer} from './native-buffers';
import type {Asset} from './types';

export interface RecoveryTab {
 id:string; title:string; kind:'flow'|'code'|'scene'|'config'|'assets'|'media'|'ai-diff'; target?:string; batchIds?:string[];
 callContext?:{callerLabel:string;source:SourceLocation};
}
export interface RecoveryMetadata {
 baseIde:Record<string,unknown>;
 ide:Record<string,unknown>;
 baseAssets?:Asset[];
 assets?:Asset[];
}
export interface RecoveryState {
 metadata?:RecoveryMetadata;
 documents:SourceBuffer[];
 tabs:RecoveryTab[];
 active:string;
 lastCode:string;
 location:SourceLocation|null;
}
export type RecoveryReason='auto'|'save'|'restore'|'close'|'discard';
export interface RecoveryResult {state:RecoveryState|null;savedAt?:string;sequence:number;warning?:string}
export interface RecoveryReceipt {savedAt:string;sequence:number;warning?:string;nextSnapshotAt?:string}
export interface RecoveryHistoryItem {id:string;time:string;reason:string;paths:string[]}
export interface RecoveryFiles {documents:SourceDocument[];errors:{path:string;message:string}[]}
export interface RecoveryConflict {path:string;draft:SourceBuffer;disk?:SourceDocument;error?:string}
