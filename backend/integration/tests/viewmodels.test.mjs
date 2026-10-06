import test from 'node:test';
import assert from 'node:assert/strict';
import { SpeedTestViewModel } from '../viewmodels/SpeedTestViewModel.mjs';
import { DashboardViewModel } from '../viewmodels/DashboardViewModel.mjs';
import { testPresentation, CampusApi } from '../models/CampusApi.mjs';
import { BrowserMeasurement } from '../models/BrowserMeasurement.mjs';

test('pending save retains same test ID and result rather than rerunning measurements',async()=>{
  let saves=0,measurements=0;
  const outcome={status:'partial',download_mbps:12,upload_mbps:null,latency_ms:30,reason:'Upload failed'};
  const saved={attempt:{id:'test-1',location_id:'loc',status:'partial',finished_at:'2026-10-01T05:00:00Z'},result:{download_mbps:12,upload_mbps:null,latency_ms:30,score:48,health:'poor'}};
  const api={startTest:async()=>({id:'test-1'}),saveTest:async(id,data)=>{assert.equal(id,'test-1');assert.deepEqual(data,outcome);if(++saves===1)throw new Error('Offline');return saved;}};
  const vm=new SpeedTestViewModel(api,{measure:async()=>{measurements++;return outcome;}});
  await vm.run('loc','endpoint');assert.equal(vm.state.pendingSave,true);
  await vm.run('loc','endpoint');assert.equal(measurements,1);
  await vm.retrySave();assert.equal(vm.state.pendingSave,false);assert.equal(vm.state.result.health_score,48);assert.equal(saves,2);
});
test('cancellation reports cancelled without fabricated metrics',async()=>{
  let vm,body;
  const api={startTest:async()=>({id:'test-1'}),saveTest:async(id,data)=>{body=data;return {attempt:{id,location_id:'loc',status:data.status},result:null};}};
  vm=new SpeedTestViewModel(api,{measure:async()=>{vm.cancel();throw new Error('aborted');}});
  await vm.run('loc','endpoint');assert.equal(body.status,'cancelled');assert.equal(vm.state.result.download_mbps,null);
});
test('late dashboard response cannot overwrite newer filter selection',async()=>{
  let oldResolve;
  const api={dashboard:filters=>filters.building_id==='old'?new Promise(r=>{oldResolve=r;}):Promise.resolve({building:'new'})};
  const vm=new DashboardViewModel(api);const old=vm.load({building_id:'old'});await vm.load({building_id:'new'});
  oldResolve({building:'old'});await old;assert.equal(vm.state.data.building,'new');
});
test('zero measurement remains zero in presentation mapping',()=>{
  const result=testPresentation({attempt:{id:'a',location_id:'l',status:'partial'},result:{download_mbps:0,upload_mbps:null,latency_ms:1,score:0,health:'critical'}});
  assert.equal(result.download_mbps,0);assert.equal(result.health_score,0);assert.equal(result.packet_loss_percent,null);
});
test('API client rotates session once then retries original request',async()=>{
  const calls=[];
  const api=new CampusApi('http://api',async(url,options)=>{
    calls.push([url,options.headers.Authorization]);
    if(url.endsWith('/auth/refresh'))return new Response(JSON.stringify({access_token:'new',refresh_token:'next'}));
    if(options.headers.Authorization==='Bearer old')return new Response('{}',{status:401});
    return new Response(JSON.stringify({name:'Alice'}));
  });
  api.setTokens({access_token:'old',refresh_token:'refresh'});
  assert.equal((await api.me()).name,'Alice');assert.equal(calls.length,3);assert.equal(api.refreshToken,'next');
});
test('device measurement uses received byte counts and server upload confirmation',async()=>{
  let clock=0;
  const measurement=new BrowserMeasurement(async(url,options)=>{
    clock+=100;
    if(url.includes('/download'))return new Response(new Uint8Array(1024));
    if(url.endsWith('/upload')){assert.equal(options.body.byteLength,1024);return new Response(JSON.stringify({received_bytes:1024}));}
    return new Response('pong');
  },()=>clock);
  const result=await measurement.measure({base_url:'http://measure',measurement_token:'test',limits:{download_bytes:1024,upload_bytes:1024}});
  assert.equal(result.status,'completed');assert.equal(result.latency_ms,100);assert.equal(result.download_mbps,.08192);assert.equal(result.upload_mbps,.08192);
});
