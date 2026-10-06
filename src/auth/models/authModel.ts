// @ts-nocheck
import {api,liveMode} from '../../services/backendClient';
// @ts-nocheck
/** Auth domain model following MVVM architecture. */
export const USER_TYPES = [];

export function validateCredentials(values, mode) {
  const errors = {};
  if (mode === 'signup' && !values.fullName?.trim()) errors.fullName = 'Enter your full name.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) errors.email = 'Enter a valid university email.';
  if (!values.password || values.password.length < (liveMode&&mode==='signup'?10:8)) errors.password = liveMode&&mode==='signup'?'Use at least 10 characters.':'Use at least 8 characters.';
  if (mode === 'signup' && values.confirmPassword !== values.password) errors.confirmPassword = 'Passwords do not match.';
  if (mode === 'signup' && !values.terms) errors.terms = 'Please accept the terms to continue.';
  return errors;
}

export async function authenticate(values,mode){
 if(!liveMode)return {ok:true,mode,name:values.fullName||values.email.split('@')[0]};
 let user;
 if(mode==='signup'){const campuses=await api.request('/auth/campuses',{authenticated:false});const campusId=import.meta.env.VITE_CAMPUS_ID||(campuses.length===1?campuses[0].id:null);if(!campusId)throw new Error('Campus registration is not configured. Contact your administrator.');const result=await api.request('/auth/register',{method:'POST',authenticated:false,body:{name:values.fullName,email:values.email,password:values.password,campus_id:campusId}});api.setTokens(result);user=result.user;}else user=await api.login(values.email,values.password);
 return {ok:true,mode,name:user.name,email:user.email,user};
}
