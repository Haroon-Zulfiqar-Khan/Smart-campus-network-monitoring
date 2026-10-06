/** MUET main campus, Jamshoro. Approximate OSM-derived campus center; not a building survey. */
export const campusMapConfig = {
 name: 'MUET · Jamshoro campus',
 center: [25.40646, 68.26032] as [number, number],
 zoom: 16,
 tileUrl: import.meta.env.VITE_OSM_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
 attribution: import.meta.env.VITE_OSM_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
 source: 'https://www.openstreetmap.org/way/998338227',
};
export function validCoordinates(latitude:unknown,longitude:unknown):boolean {
 return typeof latitude==='number'&&Number.isFinite(latitude)&&latitude>=-90&&latitude<=90&&typeof longitude==='number'&&Number.isFinite(longitude)&&longitude>=-180&&longitude<=180;
}
