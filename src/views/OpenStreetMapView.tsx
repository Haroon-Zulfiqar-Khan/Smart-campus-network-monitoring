import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocateFixed, MapPin, TriangleAlert } from 'lucide-react';
import { campusMapConfig } from '../models/mapConfig';
import { CampusMapVM } from '../viewmodels/useMapViewModel';

type Pin={id:string;latitude?:number;longitude?:number;name:string;building:string;floor:string;status:string;tone:string;score:number;tests:number;download:number;upload:number;ping:number;complaintCount:number;coordinateSource?:string};
function popupContent(pin:Pin){
 const root=document.createElement('div');root.className='campus-map-popup';
 const heading=document.createElement('strong');heading.textContent=`${pin.building} · ${pin.name}`;root.append(heading);
 const floor=document.createElement('p');floor.textContent=pin.floor;root.append(floor);
 const badge=document.createElement('span');badge.className=`badge ${pin.status.toLowerCase()}`;badge.textContent=pin.status;root.append(badge);
 const metrics=document.createElement('p');metrics.textContent=pin.tests?`${pin.download} Mbps down · ${pin.upload} Mbps up · ${pin.ping} ms RTT`:'No measurements yet';root.append(metrics);
 const complaints=document.createElement('p');complaints.textContent=`${pin.complaintCount} unresolved reports · ${pin.tests} sample tests`;root.append(complaints);
 const source=document.createElement('small');source.textContent=pin.coordinateSource==='demo'?'Demo building placement · not verified':'Coordinates entered by administrator';root.append(source);
 return root;
}
function pinIcon(pin:Pin,selected:boolean){
 const element=document.createElement('span');element.className=`osm-health-pin ${pin.tone}${selected?' selected':''}`;
 const inner=document.createElement('span');inner.textContent=pin.tests?String(pin.score):'?';element.append(inner);
 return L.divIcon({className:'osm-marker-container',html:element,iconSize:[34,34],iconAnchor:[17,17],popupAnchor:[0,-21]});
}
function MapCanvas({pins,selectedId,onSelect,fitRequest=0,point,onPick}:{pins:Pin[];selectedId?:string;onSelect?:(id:string)=>void;fitRequest?:number;point?:[number,number];onPick?:(lat:number,lng:number)=>void}){
 const container=useRef<HTMLDivElement>(null);const map=useRef<L.Map|null>(null);const layers=useRef<L.LayerGroup|null>(null);const picker=useRef<L.CircleMarker|null>(null);
 const select=useRef(onSelect);select.current=onSelect;const pick=useRef(onPick);pick.current=onPick;
 const [popupId,setPopupId]=useState('');const [tileError,setTileError]=useState(false);
 const pinKey=useMemo(()=>pins.map(p=>`${p.id}:${p.latitude},${p.longitude}`).join('|'),[pins]);
 useEffect(()=>{if(!container.current)return;const instance=L.map(container.current,{scrollWheelZoom:false,attributionControl:true}).setView(campusMapConfig.center,campusMapConfig.zoom);map.current=instance;
 const tiles=L.tileLayer(campusMapConfig.tileUrl,{attribution:campusMapConfig.attribution,maxZoom:19,updateWhenIdle:true,keepBuffer:1}).addTo(instance);
 tiles.on('tileerror',()=>setTileError(true));layers.current=L.layerGroup().addTo(instance);
 instance.on('click',(e:L.LeafletMouseEvent)=>pick.current?.(e.latlng.lat,e.latlng.lng));
 const observer=new ResizeObserver(()=>instance.invalidateSize({animate:false}));observer.observe(container.current);
 return()=>{observer.disconnect();instance.remove();map.current=null;layers.current=null;picker.current=null;};},[]);
 useEffect(()=>{const group=layers.current;if(!group)return;group.clearLayers();pins.forEach(pin=>{const label=`Inspect ${pin.building} ${pin.name} — ${pin.status}`;const marker=L.marker([pin.latitude!,pin.longitude!],{icon:pinIcon(pin,pin.id===selectedId),title:label,alt:label,keyboard:true}).addTo(group).bindPopup(popupContent(pin),{maxWidth:290,minWidth:200});marker.getElement()?.setAttribute('aria-label',label);marker.on('click',()=>{setPopupId(pin.id);select.current?.(pin.id);});if(pin.id===popupId)marker.openPopup();});},[pins,selectedId,popupId]);
 useEffect(()=>{const instance=map.current;if(!instance)return;const points=pins.map(p=>[p.latitude!,p.longitude!] as [number,number]);if(points.length)instance.fitBounds(L.latLngBounds(points),{padding:[40,40],maxZoom:17,animate:false});else instance.setView(campusMapConfig.center,campusMapConfig.zoom,{animate:false});},[pinKey,fitRequest]); // Selection preserves the user's zoom and pan.
 useEffect(()=>{const instance=map.current;if(!instance)return;if(picker.current){instance.removeLayer(picker.current);picker.current=null;}if(point){picker.current=L.circleMarker(point,{radius:9,color:'#fff',weight:3,fillColor:'#4089ef',fillOpacity:1}).addTo(instance);instance.panTo(point,{animate:false});}},[point?.[0],point?.[1]]);
 return <div className="osm-canvas-wrap"><div ref={container} className={`osm-canvas${onPick?' coordinate-picker':''}`} role="region" aria-label={onPick?'Choose location coordinates on OpenStreetMap':'OpenStreetMap campus network health map'}/>{tileError&&<div className="osm-tile-warning" role="status"><TriangleAlert size={14}/>Some map tiles could not load. Location details remain available.</div>}</div>;
}
export function OpenStreetMapView({model}:{model:CampusMapVM}){const [fit,setFit]=useState(0);return <><div className="osm-toolbar"><div><MapPin size={14}/><strong>{campusMapConfig.name}</strong><span>{model.pins.length} pins</span></div><button type="button" className="secondary small" onClick={()=>setFit(n=>n+1)}><LocateFixed size={14}/>Fit locations</button></div><MapCanvas pins={model.pins} selectedId={model.selected?.id} onSelect={model.select} fitRequest={fit}/><div className="osm-placement-note">{model.demo?'Demo building pins · exact MUET building positions are not verified.':'Building coordinates are entered by administrators.'}{model.missing>0&&<span> {model.missing} location{model.missing===1?'':'s'} without coordinates.</span>}</div>{!model.pins.length&&<p className="osm-empty">No mapped locations match the current filters.</p>}</>;}
export function CoordinatePicker({point,onPick}:{point?:[number,number];onPick:(lat:number,lng:number)=>void}){return <div className="coordinate-picker-wrap"><p>Click the map to set or move the location pin.</p><MapCanvas pins={[]} point={point} onPick={onPick}/></div>;}

