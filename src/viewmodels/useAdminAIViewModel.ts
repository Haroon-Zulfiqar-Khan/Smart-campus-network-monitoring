import {useState,useEffect,useRef} from 'react';
import {api,liveMode} from '../services/backendClient';
import type {CampusVM} from './useCampusViewModel';

export type AICategory='no_internet'|'slow_internet'|'high_ping'|'frequent_disconnection'|'weak_signal'|'service_unavailable'|'other';
export const aiCategoryLabels:Record<AICategory,string>={no_internet:'No Internet',slow_internet:'Slow Internet',high_ping:'High Latency',frequent_disconnection:'Disconnections',weak_signal:'Weak Signal',service_unavailable:'Website / Service Unavailable',other:'Other'};
interface Analysis {category:AICategory;original_category:AICategory;confidence:number;reason:string;method:'gemini'|'keyword_rules';warning:string|null;applied:boolean;analyzed_at:string}
export interface AIComplaint {id:string;reference:string;description:string;category:AICategory;location:string;analysis:Analysis|null}
interface Summary {summary:string;observations:string[];recommendations:string[];limitations:string[];method:string;model:string|null;warning:string|null;hours:number;generated_at:string;facts:{test_count:number;complaint_count:number;locations_with_data:number;timezone:string}}
interface Workspace {configured:boolean;model:string;complaints:AIComplaint[];last_summary:Summary|null}

export function useAdminAIViewModel(vm:CampusVM){
 const [data,setData]=useState<Workspace|null>(null),[hours,setHours]=useState('72'),[busy,setBusy]=useState(''),[error,setError]=useState('');
 const mounted=useRef(true),pending=useRef(false);
 async function load(){const result=await api.request('/admin/ai');if(mounted.current){setData(result);setError('');}}
 useEffect(()=>{mounted.current=true;
  if(liveMode)load().catch(()=>setError('Unable to load AI tools. Check the campus server and try again.'));
  else setError('AI tools require the authenticated backend. They are unavailable in local demo mode.');
  return()=>{mounted.current=false;};},[]);
 async function action(id:string,fn:()=>Promise<unknown>,message:string){
  if(pending.current)return;pending.current=true;setBusy(id);setError('');
  try{await fn();await load();vm.feedback('success',message);}
  catch(e){const message=e instanceof Error?e.message:'The AI request could not be completed. Please try again.';if(mounted.current)setError(message);vm.feedback('error',message);}
  finally{pending.current=false;if(mounted.current)setBusy('');}
 }
 const classify=(id:string)=>action(id,()=>api.request('/admin/ai/complaints/'+id+'/classify',{method:'POST'}),'Complaint classification is ready for review.');
 const apply=(id:string)=>action(id,()=>api.request('/admin/ai/complaints/'+id+'/apply',{method:'POST'}),'Complaint category updated.');
 const classifyPending=()=>action('pending',()=>api.request('/admin/ai/classify-pending',{method:'POST',body:{limit:1}}),'The next pending complaint has been classified.');
 const generate=()=>action('summary',()=>api.request('/admin/ai/network-summary?hours='+hours,{method:'POST'}),'Network summary is ready.');
 return {data,hours,setHours,busy,error,classify,apply,classifyPending,generate,reload:()=>action('reload',load,'AI tools refreshed.')};
}
