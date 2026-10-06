import { MapPin } from 'lucide-react';
import { CampusVM } from '../viewmodels/useCampusViewModel';
import { useCustomLocationViewModel } from '../viewmodels/useCustomLocationViewModel';
import { CoordinatePicker } from './OpenStreetMapView';
export function CustomLocationEditor({vm,onSaved,onCancel}:{vm:CampusVM;onSaved:(id:string)=>void;onCancel:()=>void}){
 const model=useCustomLocationViewModel(vm,onSaved);
 return <div className="custom-location-editor"><h3>Add your location</h3><label>Custom location name<input aria-label="Custom location name" maxLength={80} placeholder="e.g. Outside the central library" value={model.name} onChange={e=>model.setName(e.target.value)}/></label><CoordinatePicker point={model.point} onPick={(lat,lng)=>model.setPoint([lat,lng])}/><p className="custom-pin-status" role="status"><MapPin size={15}/>{model.point?`Pin selected: ${model.point[0].toFixed(6)}, ${model.point[1].toFixed(6)}`:'Click the map to choose your location.'}</p><small>Saved as a user-reported location. Network health starts as unknown.</small><div className="form-actions"><button type="button" className="secondary" onClick={onCancel}>Cancel location</button><button type="button" className="primary" disabled={!model.canSave} onClick={model.save}>Save custom location</button></div></div>;
}
