/** Device-side HTTP throughput and application RTT. Does not infer Wi-Fi signal or packet loss. */
export class BrowserMeasurement {
  constructor(fetcher = globalThis.fetch.bind(globalThis), clock = () => performance.now()) { this.fetcher = fetcher; this.clock = clock; }
  async response(session, path, options, signal) {
    const timer = AbortSignal.timeout(30000);
    const combined = signal ? AbortSignal.any([signal, timer]) : timer;
    const response = await this.fetcher(session.base_url + path, {
      ...options, cache: 'no-store', signal: combined,
      headers: { ...options?.headers, Authorization: `Bearer ${session.measurement_token}` },
    });
    if (!response.ok) throw new Error(`Measurement endpoint returned HTTP ${response.status}`);
    // The combined signal remains attached during body consumption.
    return response;
  }
  async measure(session, { signal, onProgress = () => {} } = {}) {
    const values = { download_mbps: null, upload_mbps: null, latency_ms: null, jitter_ms: null };
    const errors = [];
    const abortCheck = () => { if (signal?.aborted) throw new DOMException('Test cancelled', 'AbortError'); };
    const stage = async (name, fn) => {
      abortCheck(); onProgress(name);
      try { await fn(); } catch (error) { abortCheck(); errors.push(`${name}: ${error.message}`); }
    };
    await stage('latency', async () => {
      // First request warms the connection and is excluded from the RTT median.
      const warm = await this.response(session, '/ping', {}, signal); await warm.arrayBuffer();
      const samples = [];
      for (let i = 0; i < 5; i++) {
        abortCheck(); const start = this.clock();
        const response = await this.response(session, `/ping?nonce=${i}-${Date.now()}`, {}, signal);
        await response.arrayBuffer(); samples.push(this.clock() - start);
      }
      const sorted = [...samples].sort((a,b) => a-b); values.latency_ms = sorted[2];
      values.jitter_ms = samples.slice(1).reduce((sum,value,i) => sum + Math.abs(value - samples[i]), 0) / 4;
    });
    await stage('download', async () => {
      const size = session.limits.download_bytes;
      const start = this.clock(); const response = await this.response(session, `/download?bytes=${size}`, {}, signal);
      const data = await response.arrayBuffer(); const seconds = Math.max((this.clock()-start)/1000, .001);
      if (data.byteLength !== size) throw new Error('Download length does not match expected bytes');
      values.download_mbps = data.byteLength * 8 / seconds / 1_000_000;
    });
    await stage('upload', async () => {
      const size = session.limits.upload_bytes;
      const data = new Uint8Array(size);
      // crypto.getRandomValues has a 65,536-byte call limit.
      for (let i=0;i<size;i+=65536) crypto.getRandomValues(data.subarray(i,Math.min(i+65536,size)));
      const start = this.clock();
      const response = await this.response(session, '/upload', { method: 'POST', body: data, headers: { 'Content-Type': 'application/octet-stream' } }, signal);
      const receipt = await response.json(); const seconds = Math.max((this.clock()-start)/1000,.001);
      if (receipt.received_bytes !== size) throw new Error('Server did not confirm the complete upload');
      values.upload_mbps = receipt.received_bytes * 8 / seconds / 1_000_000;
    });
    abortCheck();
    const count = ['download_mbps','upload_mbps','latency_ms'].filter(key => values[key] !== null).length;
    if (count === 0) return { status: 'failed', reason: errors.join('; ').slice(0,500) || 'No valid measurements' };
    return { ...values, status: count === 3 ? 'completed' : 'partial', ...(count === 3 ? {} : { reason: errors.join('; ').slice(0,500) || 'Measurement incomplete' }) };
  }
}

