import { ObservableViewModel } from './ObservableViewModel.mjs';
export class DashboardViewModel extends ObservableViewModel {
  constructor(api){super({data:null,busy:false,error:null,filters:{}});this.api=api;this.sequence=0;}
  async load(filters=this.state.filters){
    const sequence=++this.sequence;this.set({busy:true,error:null,filters});
    try{const data=await this.api.dashboard(filters);if(sequence===this.sequence)this.set({data});}
    catch(error){if(sequence===this.sequence)this.set({error:error.message});}
    finally{if(sequence===this.sequence)this.set({busy:false});}
  }
}
