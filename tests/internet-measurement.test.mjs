import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const source=fs.readFileSync(new URL('../src/services/internetMeasurement.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {InternetMeasurement}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));

test('internet measurements bypass localhost and never disclose campus tokens',async()=>{
 const calls=[];
 let clock=0;
 const measure=new InternetMeasurement(async(url,options)=>{
  calls.push({url,options});
  const size=Number(new URL(url).searchParams.get('bytes')||0);
  return new Response(new Uint8Array(size),{status:200});
 },()=>{clock+=100;return clock;});
 const result=await measure.measure({base_url:'http://localhost:8001',measurement_token:'private-campus-token'});
 assert.equal(result.status,'completed');
 assert.ok(result.download_mbps>0&&result.upload_mbps>0&&result.latency_ms>0);
 assert.ok(calls.every(c=>new URL(c.url).hostname==='speed.cloudflare.com'));
 assert.ok(calls.every(c=>!c.options.headers?.Authorization));
 assert.ok(calls.some(c=>c.options.method==='POST'&&c.options.body.byteLength>0));
});

test('unreachable internet endpoint produces a failure without invented metrics',async()=>{
 const result=await new InternetMeasurement(async()=>{throw new TypeError('Failed to fetch');}).measure({});
 assert.equal(result.status,'failed');
 assert.equal(result.download_mbps,undefined);
 assert.equal(result.upload_mbps,undefined);
});

test('cancelling a test prevents further transfers',async()=>{
 const abort=new AbortController();abort.abort();
 await assert.rejects(()=>new InternetMeasurement(async()=>assert.fail('Should not transfer')).measure({},{signal:abort.signal}),{name:'AbortError'});
});
