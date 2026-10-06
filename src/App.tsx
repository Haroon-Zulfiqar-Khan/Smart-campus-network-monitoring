// @ts-nocheck
import {useState,useEffect} from 'react';
import AuthScreen from './auth/views/AuthScreen';import {useAuthViewModel} from './auth/viewmodels/useAuthViewModel';import {CampusApp} from './views/CampusApp';import {api,liveMode} from './services/backendClient';
interface Session {name:string;email:string;remember:boolean;user?:{id:string;role:string}}
const KEY='campusnet-api-session';
export function App(){const [session,setSession]=useState<Session|null>(null);const [restoring,setRestoring]=useState(liveMode);useEffect(()=>{if(!liveMode)return;let cancelled=false;try{const raw=sessionStorage.getItem(KEY);if(raw){api.setTokens(JSON.parse(raw));api.me().then(user=>{if(!cancelled)setSession({name:user.name,email:user.email,remember:true,user});}).catch(()=>{api.clearTokens();sessionStorage.removeItem(KEY);}).finally(()=>{if(!cancelled)setRestoring(false);});}else setRestoring(false);}catch{setRestoring(false);}return()=>{cancelled=true;};},[]);
 const auth=useAuthViewModel((next:Session)=>{if(liveMode)try{if(next.remember)sessionStorage.setItem(KEY,JSON.stringify({access_token:api.accessToken,refresh_token:api.refreshToken}));else sessionStorage.removeItem(KEY);}catch{}setSession(next);});async function signOut(){try{if(liveMode)await api.logout();}catch{}finally{api.clearTokens();sessionStorage.removeItem(KEY);setSession(null);auth.changeMode('login');}}
 if(restoring)return <div className="auth-shell"><p className="auth-demo-note" role="status">Restoring your campus session…</p></div>;
 return session?<CampusApp session={session} onSignOut={signOut}/>:<div className="auth-shell">{!liveMode&&<div className="auth-demo-note">Demo sign-in · Accounts are not verified by a server.</div>}<AuthScreen {...auth}/></div>;
}
