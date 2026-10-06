// @ts-nocheck
/** Real device-to-internet transfers. Never routes speed traffic through the local API. */
export class InternetMeasurement {
 constructor(fetcher=globalThis.fetch.bind(globalThis),clock=()=>performance.now()) {this.fetcher=fetcher;this.clock=clock;}
 async request(path,options,signal){
  const timeout=AbortSignal.timeout(30000);
  const response=await this.fetcher('https://speed.cloudflare.com'+path,{...options,
   credentials:'omit',cache:'no-store',signal:signal?AbortSignal.any([signal,timeout]):timeout});
  if(!response.ok)throw new Error('The internet measurement server could not complete the transfer.');
  return response;
 }
 async measure(session,{signal,onProgress=()=>{}}={}){
  const values={download_mbps:null,upload_mbps:null,latency_ms:null,jitter_ms:null},errors=[];
  const check=()=>{if(signal?.aborted)throw new DOMException('Test cancelled','AbortError');};
  const nonce=()=>crypto.randomUUID();
  const stage=async(name,fn)=>{check();onProgress(name);try{await fn();}catch(e){check();errors.push(name+': '+(e.name==='TimeoutError'?'Transfer timed out.':e.message));}};
  await stage('latency',async()=>{
   await (await this.request('/__down?bytes=0&nonce='+nonce(),{},signal)).arrayBuffer();
   const samples=[];
   for(let i=0;i<7;i++){check();const start=this.clock();await (await this.request('/__down?bytes=0&nonce='+nonce(),{},signal)).arrayBuffer();samples.push(this.clock()-start);}
   values.latency_ms=[...samples].sort((a,b)=>a-b)[3];
   values.jitter_ms=samples.slice(1).reduce((sum,n,i)=>sum+Math.abs(n-samples[i]),0)/(samples.length-1);
  });
  await stage('download',async()=>{
   let bytes=0,elapsed=0;
   // Warm up with 1 MiB, then use two larger transfers to reduce startup bias.
   for(const size of [1048576,4194304,8388608]){
    check();const start=this.clock();const response=await this.request('/__down?bytes='+size+'&nonce='+nonce(),{},signal);
    const body=await response.arrayBuffer();const duration=this.clock()-start;
    if(body.byteLength!==size)throw new Error('The download was incomplete.');
    if(size>1048576){bytes+=body.byteLength;elapsed+=duration;}
   }
   values.download_mbps=bytes*8/Math.max(elapsed/1000,.001)/1e6;
  });
  await stage('upload',async()=>{
   let bytes=0,elapsed=0;
   for(const size of [1048576,4194304,8388608]){
    check();const body=new Uint8Array(size);
    for(let i=0;i<size;i+=65536)crypto.getRandomValues(body.subarray(i,Math.min(i+65536,size)));
    const start=this.clock();const response=await this.request('/__up?nonce='+nonce(),{method:'POST',body},signal);
    await response.arrayBuffer();
    if(size>1048576){bytes+=size;elapsed+=this.clock()-start;}
   }
   values.upload_mbps=bytes*8/Math.max(elapsed/1000,.001)/1e6;
  });
  check();const count=['download_mbps','upload_mbps','latency_ms'].filter(k=>values[k]!==null).length;
  if(!count)return {status:'failed',reason:'Internet measurement failed. Check your connection or try again later.'};
  return {...values,status:count===3?'completed':'partial',...(count===3?{}:{reason:errors.join('; ').slice(0,500)})};
 }
}
