/** Stable snapshots bind to React useSyncExternalStore, Vue subscriptions or plain DOM Views. */
export class ObservableViewModel {
  constructor(initial) { this.state = Object.freeze(initial); this.listeners = new Set(); }
  getSnapshot = () => this.state;
  subscribe = listener => { this.listeners.add(listener); return () => this.listeners.delete(listener); };
  set(patch) { this.state = Object.freeze({ ...this.state, ...patch }); for (const listener of this.listeners) listener(); }
}
