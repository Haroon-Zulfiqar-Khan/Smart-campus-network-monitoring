import { useMemo, useState } from 'react';
import { CampusVM } from './useCampusViewModel';
import { health } from '../models/campus';
import { validCoordinates } from '../models/mapConfig';
export const mapFilters=['All health','Healthy','Fair','Poor / Critical','Unknown'];
export function useMapViewModel(vm:CampusVM){
 const [healthFilter,setHealthFilter]=useState('All health');
 const locations=useMemo(()=>vm.locations.filter(l=>{if(healthFilter==='All health')return true;if(healthFilter==='Unknown')return !l.tests;if(!l.tests)return false;if(healthFilter==='Healthy')return l.score>=vm.data.thresholds.good;if(healthFilter==='Fair')return l.score>=50&&l.score<vm.data.thresholds.good;return l.score<50;}),[vm.locations,vm.data.thresholds.good,healthFilter]);
 const pins=useMemo(()=>locations.filter(l=>validCoordinates(l.latitude,l.longitude)).map(l=>({...l,status:l.tests?health(l.score,vm.data.thresholds):'Unknown',tone:!l.tests?'unknown':l.score>=vm.data.thresholds.good?'good':l.score>=50?'fair':'poor',complaintCount:vm.data.complaints.filter(c=>c.locationId===l.id&&c.status!=='Resolved').length})),[locations,vm.data.thresholds,vm.data.complaints]);
 const selected=pins.find(l=>l.id===vm.locationId)||pins[0];
 return {healthFilter,setHealthFilter,pins,selected,missing:locations.length-pins.length,demo:pins.some(l=>l.coordinateSource==='demo'),select:vm.setLocationId};
}
export type CampusMapVM=ReturnType<typeof useMapViewModel>;
