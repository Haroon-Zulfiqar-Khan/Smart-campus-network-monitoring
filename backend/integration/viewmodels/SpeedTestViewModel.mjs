import { newSubmissionId } from '../models/identity.mjs';
import { ObservableViewModel } from './ObservableViewModel.mjs';
import { testPresentation } from '../models/CampusApi.mjs';
export class SpeedTestViewModel extends ObservableViewModel {
  constructor(api,measurement) {
    super({busy:false,stage:'idle',result:null,error:null,pendingSave:false});
    this.api=api;this.measurement=measurement;this.pending=null;this.controller=null;
  }
  cancel() { this.controller?.abort(); }
  async run(locationId,endpointId) {
    if (this.state.busy || this.pending) return;
    this.controller=new AbortController();
    this.set({busy:true,stage:'starting',result:null,error:null,pendingSave:false});
    let session;
    try {
      session=await this.api.startTest({location_id:locationId,endpoint_id:endpointId,submission_id:newSubmissionId(),campus_wifi_confirmed:true});
      let outcome;
      try {
        outcome=await this.measurement.measure(session,{signal:this.controller.signal,onProgress:stage=>this.set({stage})});
      } catch(error) {
        outcome = this.controller.signal.aborted ? {status:'cancelled',reason:'Cancelled by user'} : {status:'failed',reason:error.message.slice(0,500)};
      }
      this.pending={id:session.id,outcome};
      await this.retrySave();
    } catch(error) { this.set({error:error.message,stage:this.pending?'save_pending':'error',pendingSave:!!this.pending}); }
    finally {this.controller=null;this.set({busy:false});}
  }
  async retrySave() {
    if (!this.pending) return;
    const pending=this.pending;
    this.set({stage:'saving',error:null});
    try {
      const saved=await this.api.saveTest(pending.id,pending.outcome);
      this.pending=null;this.set({result:testPresentation(saved),pendingSave:false,stage:'finished'});
    } catch(error) {this.set({error:error.message,pendingSave:true,stage:'save_pending'});throw error;}
  }
  // For an offline draft, persist only this non-secret payload with the current account ID.
  // Restore only to that same account; the backend can reject an expired session.
  exportPending() {return this.pending ? structuredClone(this.pending) : null;}
}
