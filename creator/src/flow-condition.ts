import type {Project} from './types';
import {comparisonExpression,globalStateChoices,visualCondition} from './flow-authoring';

export interface FlowConditionDraft {
 variable:string;operator:string;value:string;valueType:string;custom:boolean;expression:string;
}

export function initialCondition(project:Project,expression=''):FlowConditionDraft {
 const parsed=visualCondition(expression,globalStateChoices(project));
 return {...(parsed||{variable:'',operator:'truthy',value:'0',valueType:'number'}),custom:!!expression&&!parsed,expression};
}

export function conditionResult(project:Project,draft:FlowConditionDraft):{expression:string;title:string;error:string} {
 try {
  const states=globalStateChoices(project);
  if(!draft.custom&&!states.some(state=>state.name===draft.variable))throw new Error('请选择已有的全局状态。');
  const expression=draft.custom?draft.expression.trim():comparisonExpression(draft.variable,draft.operator,draft.value,draft.valueType);
  if(!expression)throw new Error('请填写判断条件。');
  const parsed=draft.custom?visualCondition(expression,states):draft;
  let title='自定义判断';
  if(parsed){
   const operator=({truthy:'为真',falsy:'为假','==':'＝','!=':'≠','>=':'≥','<=':'≤'} as Record<string,string>)[parsed.operator]||parsed.operator;
   const value=['truthy','falsy'].includes(parsed.operator)?'':parsed.valueType==='boolean'?(parsed.value==='true'?'是':'否'):parsed.value;
   title=`${parsed.variable} ${operator}${value?' '+value:''}`;
  }
  return {expression,title:title.slice(0,120),error:''};
 }catch(error){return {expression:'',title:'条件判断',error:error instanceof Error?error.message:String(error)};}
}
