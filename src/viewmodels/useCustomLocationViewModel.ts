import { useState } from 'react';
import { CampusVM } from './useCampusViewModel';
import { validCoordinates } from '../models/mapConfig';
export function useCustomLocationViewModel(vm:CampusVM,onSaved:(id:string)=>void){
 const [name,setName]=useState('');const [point,setPoint]=useState<[number,number]|undefined>();
 const canSave=name.trim().length>=2&&name.trim().length<=80&&!!point&&validCoordinates(point[0],point[1]);
 async function save(){if(!canSave||!point)return;const id=await vm.addCustomLocation(name,point[0],point[1]);if(id)onSaved(id);}
 return {name,setName,point,setPoint,canSave,save};
}
