import { newSubmissionId } from '../models/identity.mjs';
import { ObservableViewModel } from './ObservableViewModel.mjs';
export class ComplaintsViewModel extends ObservableViewModel {
  constructor(api) {super({items:[],total:0,busy:false,error:null,selected:null});this.api=api;this.draft=null;}
  async load(filters={}) {
    this.set({busy:true,error:null});
    try {const page=await this.api.complaints(filters);this.set({items:page.items,total:page.total});}
    catch(error){this.set({error:error.message});}finally{this.set({busy:false});}
  }
  async submit(form) {
    if(this.state.busy)return;
    // Preserve this draft/submission ID for a safe retry; changing the form needs discardDraft().
    this.draft??={...form,submission_id:newSubmissionId()};
    this.set({busy:true,error:null});
    try {const saved=await this.api.submitComplaint(this.draft);this.draft=null;this.set({selected:saved});return saved;}
    catch(error){this.set({error:error.message});throw error;}finally{this.set({busy:false});}
  }
  discardDraft(){this.draft=null;}
  async details(id){this.set({selected:await this.api.complaint(id)});}
  async assign(id,assigneeId){await this.api.assignComplaint(id,assigneeId);await this.details(id);}
  async transition(id,status,note,testIds=[]){await this.api.transitionComplaint(id,status,note,testIds);await this.details(id);}
}
