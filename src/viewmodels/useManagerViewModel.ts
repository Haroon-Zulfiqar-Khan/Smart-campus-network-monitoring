import { useMemo } from 'react';
import { CampusVM } from './useCampusViewModel';
export function useManagerViewModel(vm:CampusVM){
 const complaints=vm.data.complaints.filter(c=>vm.locations.some(l=>l.id===c.locationId));
 const problems=useMemo(()=>{const counts=new Map<string,number>();complaints.forEach(c=>counts.set(c.category,(counts.get(c.category)||0)+1));return [...counts].map(([category,count])=>({category,count})).sort((a,b)=>b.count-a.count||a.category.localeCompare(b.category));},[vm.data.complaints,vm.locations]);
 const activities=(vm.data.supportActivities||[]).filter(a=>vm.locations.some(l=>l.id===a.locationId));
 const notes=(vm.data.maintenanceNotes||[]).filter(n=>vm.locations.some(l=>l.id===n.locationId));
 const tests=vm.data.tests.filter(t=>vm.locations.some(l=>l.id===t.locationId));
 const staff=vm.data.users.filter(u=>u.role==='IT Support').map(u=>({name:u.name,assigned:complaints.filter(c=>c.assignee===u.name&&c.status!=='Resolved').length,resolved:complaints.filter(c=>c.assignee===u.name&&c.status==='Resolved').length,notes:notes.filter(n=>n.author===u.name).length}));
 const events=[...activities.map(a=>({...a,text:a.status+' · '+a.assignee+(a.note?' — '+a.note:''),author:a.actor})),...notes.map(n=>({...n,text:n.text}))].sort((a,b)=>Date.parse(b.createdAt)-Date.parse(a.createdAt));
 function exportSummary(){try{const rows=[['Section','Name','Count'],['Reports','Tests',tests.length],['Reports','Complaints',complaints.length],...problems.map(p=>['Problem',p.category,p.count]),...staff.flatMap(s=>[['Support',s.name+' active assignments',s.assigned],['Support',s.name+' resolved',s.resolved],['Support',s.name+' maintenance notes',s.notes]])];const csv=rows.map(r=>r.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='manager-campus-summary.csv';a.click();URL.revokeObjectURL(url);vm.feedback('success','Summary report download started. Check your browser downloads.');}catch{vm.feedback('error','Unable to generate the summary report. Please try again.');}}
 return {complaints,problems,staff,events,tests,exportSummary};
}
