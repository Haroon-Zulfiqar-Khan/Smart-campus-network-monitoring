// Copy the integration directory into frontend/src; adjust imports to its location.
// Views render state and invoke commands. They never fetch or calculate network scores.
import { useMemo, useSyncExternalStore } from 'react';
import { CampusApi } from './models/CampusApi.mjs';
import { BrowserMeasurement } from './models/BrowserMeasurement.mjs';
import { SpeedTestViewModel } from './viewmodels/SpeedTestViewModel.mjs';
export function useViewModel(viewModel) {
  return useSyncExternalStore(viewModel.subscribe, viewModel.getSnapshot, viewModel.getSnapshot);
}
// Share this Model through your app's dependency/context provider.
export const campusApi = new CampusApi('http://localhost:8000');
export function SpeedTestView({locationId,endpointId}) {
  const vm=useMemo(()=>new SpeedTestViewModel(campusApi,new BrowserMeasurement()),[]);
  const state=useViewModel(vm);
  return <section>
    <p>Confirm you are on campus Wi-Fi. Testing transfers up to 16 MiB of data.</p>
    <button disabled={state.busy||state.pendingSave} onClick={()=>vm.run(locationId,endpointId)}>Run test</button>
    {state.busy&&<button onClick={()=>vm.cancel()}>Cancel</button>}
    <p aria-live="polite">{state.stage}</p>
    {state.error&&<p role="alert">{state.error}</p>}
    {state.pendingSave&&<button onClick={()=>vm.retrySave().catch(()=>{})}>Retry saving</button>}
    {state.result&&<div>
      <p>Outcome: {state.result.outcome}</p>
      <p>Download: {state.result.download_mbps??'Not measured'} Mbps</p>
      <p>Upload: {state.result.upload_mbps??'Not measured'} Mbps</p>
      <p>Application RTT: {state.result.latency_ms??'Not measured'} ms</p>
      <p>Health: {state.result.health_score??'Insufficient data'} / 100 — {state.result.health_status}</p>
    </div>}
  </section>;
}
