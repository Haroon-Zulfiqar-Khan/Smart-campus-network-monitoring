import { useMemo, useState } from 'react';
import { CampusVM } from './useCampusViewModel';
export function useTestHistoryViewModel(vm:CampusVM){
 const [locationId,setLocationId]=useState('All locations');
 const tests=useMemo(()=>vm.data.tests.filter(t=>locationId==='All locations'||t.locationId===locationId).sort((a,b)=>Date.parse(b.testedAt)-Date.parse(a.testedAt)),[vm.data.tests,locationId]);
 function runAgain(id:string){vm.setLocationId(id);vm.setPage('Test Connection');}
 return {tests,locationId,setLocationId,runAgain};
}
