/** Frontend Model: API access only; no DOM, React, routing or display state. */
export class ApiError extends Error {
  constructor(message, status, details) { super(message); this.status = status; this.details = details; }
}
export class CampusApi {
  constructor(baseUrl = 'http://localhost:8000', fetcher = globalThis.fetch.bind(globalThis)) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); this.fetcher = fetcher;
    this.accessToken = null; this.refreshToken = null; this.refreshing = null;
  }
  setTokens(tokens) { this.accessToken = tokens.access_token; this.refreshToken = tokens.refresh_token; }
  clearTokens() { this.accessToken = null; this.refreshToken = null; }
  async request(path, { method = 'GET', body, signal, authenticated = true, retry = true } = {}) {
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (authenticated && this.accessToken) headers.Authorization = `Bearer ${this.accessToken}`;
    const response = await this.fetcher(this.baseUrl + path, {
      method, headers, signal, cache: 'no-store', body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 401 && authenticated && retry && this.refreshToken) {
      if (!this.refreshing) {
        this.refreshing = this.request('/auth/refresh', { method: 'POST', body: { refresh_token: this.refreshToken }, authenticated: false, retry: false })
          .then(tokens => this.setTokens(tokens)).catch(error => { this.clearTokens(); throw error; })
          .finally(() => { this.refreshing = null; });
      }
      await this.refreshing;
      return this.request(path, { method, body, signal, authenticated, retry: false });
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(data.error?.message ?? data.detail ?? `HTTP ${response.status}`, response.status, data.error?.details);
    return data;
  }
  async login(email, password) {
    const data = await this.request('/auth/login', { method: 'POST', body: { email, password }, authenticated: false });
    this.setTokens(data); return data.user;
  }
  async logout() { try { await this.request('/auth/logout', { method: 'POST' }); } finally { this.clearTokens(); } }
  me() { return this.request('/auth/me'); }
  query(path, filters = {}) {
    const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k,v]) => [k,String(v)]));
    return this.request(path + (params.size ? '?' + params : ''));
  }
  locations(filters) { return this.query('/locations', filters); }
  endpoints() { return this.request('/endpoints'); }
  startTest(data) { return this.request('/test-sessions', { method: 'POST', body: data }); }
  saveTest(id, data) { return this.request(`/test-sessions/${id}/result`, { method: 'POST', body: data }); }
  tests(filters) { return this.query('/tests', filters); }
  complaints(filters) { return this.query('/complaints', filters); }
  submitComplaint(data) { return this.request('/complaints', { method: 'POST', body: data }); }
  complaint(id) { return this.request(`/complaints/${id}`); }
  assignComplaint(id, assigneeId) { return this.request(`/complaints/${id}/assignment`, { method: 'PATCH', body: { assignee_id: assigneeId } }); }
  transitionComplaint(id, status, note, testIds = []) { return this.request(`/complaints/${id}/transitions`, { method: 'POST', body: { status, note, verification_test_ids: testIds } }); }
  addComplaintNote(id, note, visibility = 'public') { return this.request(`/complaints/${id}/notes`, { method: 'POST', body: { note, visibility } }); }
  dashboard(filters) { return this.query('/dashboard', filters); }
  analytics(filters) { return this.query('/analytics', filters); }
  notifications(filters) { return this.query('/notifications', filters); }
  readNotification(id) { return this.request(`/notifications/${id}/read`, { method: 'PATCH' }); }
}
/** Canonical presentation contract from the task brief, mapped from the raw API. */
export function testPresentation({ attempt, result }) {
  return {
    test_id: attempt.id, location_id: attempt.location_id,
    download_mbps: result?.download_mbps ?? null, upload_mbps: result?.upload_mbps ?? null,
    latency_ms: result?.latency_ms ?? null, packet_loss_percent: null,
    health_score: result?.score ?? null,
    health_status: result ? result.health.split('_').map(s => s[0].toUpperCase() + s.slice(1)).join(' ') : 'Not measured',
    outcome: attempt.status, tested_at: attempt.finished_at ?? attempt.created_at,
    explanation: result?.explanation ?? null,
  };
}

