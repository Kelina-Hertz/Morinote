import type {Asset} from './types';
import type {SourceLocation} from './native-types';
import type {AssetType} from './asset-types';
export type Binding={kind:'original'|'label'|'file';key:string};
export interface VirtualEntry {
 id:string;runtime:{kind:'image'|'file'|'audio-variable';key:string};name:string;type:AssetType;
 character?:string;costume?:string;expression?:string;category?:string;requirement?:string;
 binding:Binding|null;temporary:boolean;override:boolean;status:'unbound'|'bound'|'temporary'|'broken';
 mediaAssetId?:string;path?:string;opaque?:boolean;fallbackAlias?:string;source?:SourceLocation;
 references:(SourceLocation&{text:string})[];props?:Record<string,number>;
}
export interface VirtualLibrary {
 version:1;path:string;entries:VirtualEntry[];deleted:string[];error?:string;
 resources:(Asset&{nativeGamePath:string})[];
 labels:{key:string;source?:SourceLocation;asset?:string;props:Record<string,number>;opaque?:boolean}[];
}
export const virtualStatus={unbound:'缺失',bound:'',temporary:'缺失 · 临时替代',broken:'缺失'};
