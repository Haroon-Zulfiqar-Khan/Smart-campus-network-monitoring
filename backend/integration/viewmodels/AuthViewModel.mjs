import { ObservableViewModel } from './ObservableViewModel.mjs';
export class AuthViewModel extends ObservableViewModel {
  constructor(api) { super({ user: null, busy: false, error: null }); this.api = api; }
  async login(email,password) {
    this.set({busy:true,error:null});
    try { this.set({ user: await this.api.login(email,password) }); }
    catch(error) { this.set({error:error.message}); }
    finally { this.set({busy:false}); }
  }
  async logout() { try { await this.api.logout(); } finally { this.set({user:null}); } }
}
