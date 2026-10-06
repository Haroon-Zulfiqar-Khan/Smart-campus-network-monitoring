'use client';
import {liveMode} from '../services/backendClient';
import { useEffect, useRef } from 'react';
import { CampusVM } from './useCampusViewModel';
type Tool={name:string;description:string;inputSchema:object;annotations:{readOnlyHint:boolean};execute:(input:unknown)=>unknown};
type Context={registerTool:(tool:Tool,options:{signal:AbortSignal})=>void|Promise<void>};
/** Optional agent access to the same location filter shown in the UI. */
export function useCampusTools(vm:CampusVM){
 const latest=useRef(vm);latest.current=vm;
 useEffect(()=>{if(liveMode)return;const context=(document as Document&{modelContext?:Context}).modelContext;if(!context?.registerTool)return;const lifecycle=new AbortController();const tools:Tool[]=[
 {name:'read_campus_demo_locations',description:'Read current demo campus locations and their sample network metrics. These are not live measurements.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute(input){if(!input||typeof input!=='object'||Object.keys(input).length)throw new Error('Expected an empty object.');return {demo:true,locations:latest.current.locations};}},
 {name:'set_campus_building_filter',description:'Set the visible building filter in the campus demo dashboard.',inputSchema:{type:'object',properties:{building:{type:'string'}},required:['building'],additionalProperties:false},annotations:{readOnlyHint:false},execute(input){if(!input||typeof input!=='object'||Object.keys(input).some(k=>k!=='building'))throw new Error('Expected a building name.');const building=(input as {building?:unknown}).building;const valid=['All buildings',...latest.current.data.locations.map(l=>l.building)];if(typeof building!=='string'||!valid.includes(building))throw new Error('Unknown building.');latest.current.setBuilding(building);return {building,demo:true};}}
 ];for(const tool of tools){try{void Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}}return()=>lifecycle.abort();},[]);
}
