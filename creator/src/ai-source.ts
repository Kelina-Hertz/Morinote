import type {SourceBuffer} from './native-buffers';
import type {SourceDocument} from './native-types';
export type AISourceEdit={path:string;content:string;delete?:boolean;expected:SourceBuffer};
export type AISourceRequest={id:string;projectSession:string;action:'snapshot'|'refresh'|'commit'|'operate'|'revert'|'conflict';payload:{path?:string;base?:SourceDocument;disk?:SourceDocument;local?:string;edits?:AISourceEdit[];adapter?:string;operation?:Record<string,unknown>;files?:{path:string;before:string|null;after:string|null}[];identity?:{conversationId:string;callId:string;observed?:SourceBuffer[]}}};
export type AISourceReceipt={documents:SourceDocument[];transaction:string;files?:{path:string;before:string|null;after:string|null}[];batchId?:string};
