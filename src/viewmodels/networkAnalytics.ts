import type { CampusVM } from './useCampusViewModel';

/** Aggregate actual measurements in campus time; empty buckets have no invented values. */
export function recordedTrend(vm:CampusVM) {
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Karachi',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const cutoff=Date.now()-7*24*60*60*1000;
 const buckets=new Map<string,{download:number[];upload:number[]}>();
 for(const test of vm.data.tests){
  if(!vm.locations.some(l=>l.id===test.locationId))continue;
  const stamp=new Date(test.testedAt);
  const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Karachi',year:'numeric',month:'2-digit',day:'2-digit'}).format(stamp);
  if(vm.range==='Today'?day!==today:stamp.getTime()<cutoff)continue;
  const key=vm.range==='Today'?new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Karachi',hour:'2-digit',hourCycle:'h23'}).format(stamp)+':00':day;
  const bucket=buckets.get(key)||{download:[],upload:[]};
  if(Number.isFinite(test.download))bucket.download.push(test.download);
  if(Number.isFinite(test.upload))bucket.upload.push(test.upload);
  buckets.set(key,bucket);
 }
 const mean=(values:number[])=>values.length?Math.round(values.reduce((s,n)=>s+n,0)/values.length*10)/10:null;
 return [...buckets].sort(([a],[b])=>a.localeCompare(b)).map(([time,b])=>({time,download:mean(b.download),upload:mean(b.upload)}));
}
