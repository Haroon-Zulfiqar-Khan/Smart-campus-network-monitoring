import { CampusState, seed } from '../models/campus';
import { validCoordinates } from '../models/mapConfig';
/** Device-local demonstration repository. Replace with your authenticated API adapter. */
export interface CampusRepository { load(): CampusState; save(state: CampusState): void; }
const KEY='smart-campus-demo-v1';
export const demoRepository: CampusRepository = {
 load() { try { const saved=localStorage.getItem(KEY); if(saved) { const value=JSON.parse(saved); if(Array.isArray(value.locations)&&Array.isArray(value.complaints)&&Array.isArray(value.users)&&Array.isArray(value.tests)&&value.thresholds) return {...value,locations:value.locations.map((l:CampusState['locations'][number])=>{if(validCoordinates(l.latitude,l.longitude))return l;const sample=seed.locations.find(s=>s.id===l.id);return sample?{...l,latitude:sample.latitude,longitude:sample.longitude,coordinateSource:'demo'}:{...l,latitude:undefined,longitude:undefined};})}; } } catch {} return structuredClone(seed); },
 save(state) { localStorage.setItem(KEY,JSON.stringify(state)); }
};
