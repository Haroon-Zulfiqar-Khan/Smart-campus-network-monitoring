import { useMemo, useState } from 'react';
import { CampusVM } from './useCampusViewModel';
export function useCampusStatusHistoryViewModel(vm:CampusVM){
 const [view,setView]=useState('Current status');const [from,setFrom]=useState('');const [to,setTo]=useState('');
 const invalidRange=!!from&&!!to&&from>to;
 const records=useMemo(()=>((vm.data as any).networkHistory||vm.data.tests).filter((t:any)=>{const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Karachi',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t.testedAt));return !invalidRange&&vm.locations.some(l=>l.id===t.locationId)&&(!from||day>=from)&&(!to||day<=to);}).sort((a:any,b:any)=>Date.parse(b.testedAt)-Date.parse(a.testedAt)),[vm.data,vm.locations,from,to,invalidRange]);
 return {view,setView,from,setFrom,to,setTo,invalidRange,records};
}
