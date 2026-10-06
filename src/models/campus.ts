import { Permission } from './permissions';
export type Role = 'Student' | 'IT Support' | 'Manager' | 'Administrator';
export type Status = 'Open' | 'Assigned' | 'In Progress' | 'Resolved';
export interface Location { id: string; name: string; building: string; floor: string; score: number; download: number; upload: number; ping: number; tests: number; latitude?: number; longitude?: number; coordinateSource?: 'demo' | 'manual'; userReported?: boolean; x: number; y: number; }
export interface Complaint { id: string; locationId: string; category: string; description: string; status: Status; assignee: string; assigneeId?: string; createdAt: string; owner: string; notes: string[]; attachedTest?: Test; }
export interface Test { id: string; locationId: string; download: number; upload: number; ping: number; score: number; testedAt: string; simulated: boolean; outcome?: string; }
export interface MaintenanceNote { id:string; locationId:string; text:string; author:string; createdAt:string; }
export interface SupportActivity { id:string; complaintId:string; locationId:string; status:Status; assignee:string; actor:string; note:string; createdAt:string; }
export interface CampusAlert { id:string; message:string; kind:'success'|'error'|'info'; createdAt:string; recipients:Role[]; readBy:Role[]; }
export interface CampusState { alerts?:CampusAlert[]; permissions?:Partial<Record<Role,Permission[]>>; supportActivities?:SupportActivity[]; maintenanceNotes?:MaintenanceNote[]; locations: Location[]; complaints: Complaint[]; tests: Test[]; users: {id:string;name:string;role:Role;active:boolean}[]; thresholds: { good:number; excellent:number }; }
export const seed: CampusState = {
 locations: [
 {id:'LIB-F2-01',name:'Reading Area',building:'Library',floor:'Floor 2',score:92,download:95.4,upload:48.7,ping:12,tests:34,x:32,y:38,latitude:25.4071,longitude:68.2592,coordinateSource:'demo'},
 {id:'SCI-L1',name:'Computer Lab 1',building:'Science',floor:'Floor 1',score:82,download:72.5,upload:32.4,ping:24,tests:28,x:64,y:28,latitude:25.4078,longitude:68.2615,coordinateSource:'demo'},
 {id:'ENG-F3',name:'Design Studio',building:'Engineering',floor:'Floor 3',score:58,download:28.2,upload:12.1,ping:74,tests:19,x:75,y:66,latitude:25.4052,longitude:68.2622,coordinateSource:'demo'},
 {id:'HOS-A',name:'Common Room',building:'Hostel',floor:'Ground floor',score:31,download:6.2,upload:2.3,ping:155,tests:23,x:29,y:74,latitude:25.4048,longitude:68.2587,coordinateSource:'demo'},
 {id:'CAF-01',name:'Dining Hall',building:'Cafeteria',floor:'Ground floor',score:44,download:12.8,upload:4.2,ping:110,tests:16,x:51,y:57,latitude:25.4058,longitude:68.2606,coordinateSource:'demo'},
 {id:'ADM-01',name:'Reception',building:'Administration',floor:'Ground floor',score:88,download:86.1,upload:41.2,ping:18,tests:17,x:47,y:19,latitude:25.4084,longitude:68.2603,coordinateSource:'demo'}],
 complaints:[
 {id:'SC-1042',locationId:'HOS-A',category:'No Internet',description:'The connection drops repeatedly in the hostel common room. Several students are affected.',status:'Open',assignee:'Unassigned',createdAt:'2026-10-01T04:50:00Z',owner:'student-demo',notes:[]},
 {id:'SC-1041',locationId:'CAF-01',category:'Slow Internet',description:'Pages are taking a long time to load during lunch.',status:'In Progress',assignee:'Sarah Khan',createdAt:'2026-10-01T03:45:00Z',owner:'student-demo',notes:['Checking access point utilization.']},
 {id:'SC-1040',locationId:'ENG-F3',category:'High Latency',description:'Video calls freeze in the design studio.',status:'Assigned',assignee:'Omar Ali',createdAt:'2026-09-30T08:30:00Z',owner:'other-demo',notes:[]},
 {id:'SC-1039',locationId:'LIB-F2-01',category:'Disconnections',description:'Wi-Fi briefly disconnected this morning.',status:'Resolved',assignee:'Sarah Khan',createdAt:'2026-09-30T04:20:00Z',owner:'student-demo',notes:['Access point restarted; connection verified.']}],
 tests:[],
 users:[{id:'student-demo',name:'Alex Johnson',role:'Student',active:true},{id:'it-demo',name:'Sarah Khan',role:'IT Support',active:true},{id:'manager-demo',name:'Omar Ali',role:'Manager',active:true},{id:'admin-demo',name:'Ayesha Ahmed',role:'Administrator',active:true}],
 thresholds:{good:75,excellent:90}
};
export function health(score:number, thresholds=seed.thresholds) { return !Number.isFinite(score)?'Unknown':score>=thresholds.excellent?'Excellent':score>=thresholds.good?'Good':score>=50?'Fair':score>=25?'Poor':'Critical'; }
