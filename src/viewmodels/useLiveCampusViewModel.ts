// @ts-nocheck
import {useState,useEffect,useRef,useMemo} from 'react';
import {toast} from 'sonner';
import {api,roleLabel} from '../services/backendClient';
import {BrowserMeasurement} from '../services/browserMeasurement';
import {seed} from '../models/campus';
import type {CampusVM} from './useCampusViewModel';
const blank={...seed,locations:[],tests:[],complaints:[],users:[],alerts:[],maintenanceNotes:[],supportActivities:[]};
const categories={'No Internet':'no_internet','Slow Internet':'slow_internet','High Latency':'high_ping','Disconnections':'frequent_disconnection','Weak Signal':'weak_signal','Website / Service Unavailable':'service_unavailable','Other':'other'};
export function useLiveCampusViewModel():CampusVM{
 const [data,setData]=useState(blank),[ready,setReady]=useState(false),[page,setPage]=useState('Dashboard'),[building,setBuilding]=useState('All buildings'),[query,setQuery]=useState(''),[locationId,setLocationId]=useState(''),[progress,setProgress]=useState(0),[running,setRunning]=useState(false),[lastTestId,setLastTestId]=useState(''),[range,setRange]=useState('Today');
 const controller=useRef(null),busy=useRef(false),mounted=useRef(true);
 const role=roleLabel(data.user?.role)||'Student';
 const feedback=(kind,message)=>toast[kind](message,{duration:kind==='error'?7000:4500});
 async function refresh(){const next=await api.request('/workspace');if(!mounted.current)return;setData(next);setLocationId(id=>next.locations.some(l=>l.id===id)?id:next.locations[0]?.id||'');setReady(true);}
 useEffect(()=>{mounted.current=true;refresh().catch(e=>feedback('error',message(e)));const timer=setInterval(()=>refresh().catch(()=>{}),30000);return()=>{mounted.current=false;clearInterval(timer);controller.current?.abort();};},[]);
 function message(e){return e.status===401?'Your session has expired. Sign out and sign in again.':e.status===403?'You do not have permission for this action. Contact your administrator.':e instanceof TypeError?'Unable to reach the campus server. Check your connection and try again.':typeof e.message==='string'?e.message:'The request could not be completed. Please try again.';}
 async function action(fn,success){if(busy.current){feedback('info','Please wait for the current request to complete.');return false;}busy.current=true;try{const result=await fn();if(success)feedback('success',success);try{await refresh();}catch{feedback('error','Your action was saved, but the updated view could not be loaded. Refresh to try again.');}return result===undefined?true:result;}catch(e){feedback('error',message(e));return false;}finally{busy.current=false;}}
 const locations=useMemo(()=>data.locations.filter(l=>(building==='All buildings'||l.building===building)&&`${l.name} ${l.building}`.toLowerCase().includes(query.toLowerCase())),[data,building,query]);
 const complaints=data.complaints.filter(c=>locations.some(l=>l.id===c.locationId));
 const location=data.locations.find(l=>l.id===locationId)||data.locations[0];const lastTest=data.tests.find(t=>t.id===lastTestId)||data.tests.find(t=>t.owner===data.user?.id&&t.locationId===locationId);
 const can=cap=>(data.permissions?.[role]||[]).includes(cap);
 async function performTest(loc){
  const abort=new AbortController();controller.current=abort;setRunning(true);setProgress(0);
  try{
   const session=await api.request('/workspace/internet-test-sessions',{method:'POST',body:{location_id:loc,submission_id:crypto.randomUUID()}});
   let outcome;
   try{outcome=await new BrowserMeasurement().measure(session,{signal:abort.signal,onProgress:stage=>setProgress(({latency:15,download:40,upload:75})[stage]||5)});}
   catch(e){outcome={status:abort.signal.aborted?'cancelled':'failed',reason:message(e).slice(0,500)};}
   const saved=await api.saveTest(session.id,outcome);
   if(saved.result)setLastTestId(saved.attempt.id);
   setProgress(saved.attempt.status==='completed'?100:0);
   return saved;
  }finally{controller.current=null;setRunning(false);}
 }
 async function runTest(){
  if(busy.current||running){feedback('info','Please wait for the current request to complete.');return;}
  return action(async()=>{const saved=await performTest(locationId);
   feedback(saved.attempt.status==='completed'?'success':'info',saved.attempt.status==='completed'?'Internet speed test completed. Results saved in Test History.':saved.attempt.status==='partial'?'Some measurements could not finish. Available results were saved.':saved.attempt.status==='cancelled'?'Test cancelled.':'Unable to measure the internet connection. No speed values were fabricated.');
   return saved;});
 }
 const submitComplaint=(category,description,loc,include)=>action(async()=>{
  let test;
  if(include){feedback('info','Testing your connection before submitting the complaint…');test=await performTest(loc);
   if(test.attempt.status==='cancelled')throw new Error('Submission cancelled. Your complaint has not been sent.');
   if(test.attempt.status!=='completed')feedback('info','The test did not fully complete. Its available results or failure record will be attached.');}
  return api.submitComplaint({location_id:loc,category:categories[category],description,submission_id:crypto.randomUUID(),...(test?{test_id:test.attempt.id}:{})});
 },'Complaint submitted'+(include?' with the fresh connection test.':'.'));
 async function updateComplaint(id,status,assignee,note){return action(async()=>{const staff=await api.request('/workspace/staff');const person=staff.find(u=>u.id===assignee);return api.request('/workspace/complaints/'+id,{method:'PATCH',body:{status,assignee_id:person?.id,note}});},'Complaint '+(status==='Assigned'?'assigned':status==='Resolved'?'resolved':'updated')+'.');}

 const addLocation=(name,b,floor,lat,lng)=>action(()=>api.request('/workspace/locations',{method:'POST',body:{name,building:b,floor,latitude:lat,longitude:lng}}),'Campus location added.');
 const addCustomLocation=(name,lat,lng)=>action(async()=>{const l=await api.request('/workspace/locations',{method:'POST',body:{name,latitude:lat,longitude:lng}});return l.id;},'Custom location saved and selected.');
 const updateLocation=(id,name,b,floor,lat,lng)=>action(()=>api.request('/workspace/locations/'+id,{method:'PATCH',body:{name,building:b,floor,latitude:lat,longitude:lng}}),'Campus location updated.');
 const addMaintenanceNote=(loc,text)=>action(()=>api.request('/workspace/maintenance-notes',{method:'POST',body:{location_id:loc,text}}),'Maintenance note saved.');
 const changeUserRole=(id,next)=>action(()=>api.request('/admin/users/'+id,{method:'PATCH',body:{role:({'Student':'student','IT Support':'support',Manager:'manager'})[next]}}),'User role updated.');
 const toggleUser=id=>action(()=>api.request('/admin/users/'+id,{method:'PATCH',body:{is_active:!data.users.find(u=>u.id===id)?.active}}),'Account status updated.');
 const savePermissions=(target,permissions)=>action(()=>api.request('/workspace/permissions/'+({'IT Support':'support',Manager:'manager'})[target],{method:'PATCH',body:{permissions}}),'Role permissions saved.');
 const setThresholds=(good,excellent)=>action(async()=>{const current=await api.request('/admin/thresholds');return api.request('/admin/thresholds',{method:'POST',body:{...current.config,good,excellent}});},'Network health thresholds saved.');
 const alerts=data.alerts||[];const unreadAlerts=alerts.filter(a=>!a.readBy.includes(role)).length;
 const markAlertsRead=()=>action(()=>Promise.all(alerts.filter(a=>!a.readBy.includes(role)).map(a=>api.readNotification(a.id))),'Notifications marked as read.');
 function exportReport(){if(!can('reports'))return feedback('error','Your account does not have report permission.');const rows=[['Building','Location','Health score','Download Mbps','Upload Mbps','Latency ms'],...locations.map(l=>[l.building,l.name,l.score,l.download,l.upload,l.ping])];const csv=rows.map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='campus-network-report.csv';a.click();URL.revokeObjectURL(url);feedback('success','Report download started.');}
 return {data,ready,role,switchRole:()=>feedback('info','Your workspace is determined by your authenticated account.'),page,setPage,building,setBuilding,query,setQuery,range,setRange,locations,complaints,locationId,setLocationId,location,progress,running,lastTest,runTest,cancelTest:()=>controller.current?.abort(),submitComplaint,updateComplaint,addLocation,addCustomLocation,updateLocation,updateCoordinates:()=>false,addMaintenanceNote,changeUserRole,toggleUser,savePermissions,setThresholds,can,feedback,alerts,unreadAlerts,markAlertsRead,exportReport};
}
