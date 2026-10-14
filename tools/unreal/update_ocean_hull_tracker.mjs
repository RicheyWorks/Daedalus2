import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out,input=repo+'/docs/production/Realm-production-2026-10-13.xlsx']=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const read=async name=>JSON.parse((await fs.readFile(repo+'/docs/production/'+name,'utf8')).replace(/^\uFEFF/,''));
const build=await read('ocean-hull-profile-build-proof.json'),runtime=await read('ocean-hull-profile-runtime-proof.json'),network=await read('ocean-hull-profile-network-proof.json');
const test=runtime.tests.find(t=>t.fullTestPath==='Daedalus.Ocean.HullProfile');
if(!test||test.state!=='Success'||network.passed.length!==2||!network.passed.every(t=>t.hull_profile_replication_verified))throw Error('Missing hull verification');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(input));
const norm=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const prior=[['Assets','A1:Q348'],['Production','A1:H24'],['Mechanics','A1:E50'],['Unreal verification','A8:H31']].map(([s,r])=>[s,r,norm(wb.worksheets.getItem(s).getRange(r).values),JSON.stringify(wb.worksheets.getItem(s).getRange(r).formulas)]);
const runs=wb.worksheets.getItem('Unreal verification'),mechanics=wb.worksheets.getItem('Mechanics');
if(runs.getRange('A32').values[0][0]||mechanics.getRange('A51').values[0][0])throw Error('Expected unused rows');
for(let row=32;row<=34;row++){const r=runs.getRange(`A${row}:H${row}`);r.copyFrom(runs.getRange('A31:H31'),'all');r.format.rowHeight=64;r.format.verticalAlignment='center';}
runs.getRange('A32:H34').values=[
 ['BUILD-HULL','Full plugin with configurable hulls','Ocean','Verified',build.seconds,'Full 136-file source snapshot','ocean-hull-profile-build-proof.json','No shared editor or fixture overlay in production build'],
 ['HULL-PROFILE',test.fullTestPath,'Ocean','Verified',test.duration,'Native test body; excludes startup','ocean-hull-profile-runtime-proof.json','Bounds, overlap, occupied refusal and real wall sweeps'],
 ['HULL-NET','Replicated boat and submarine body dimensions','Ocean','Verified',network.passed.reduce((a,b)=>a+b.elapsed_seconds,0),'Sum of two separate server/client scenarios','ocean-hull-profile-network-proof.json','Both client colliders match; client resize refused; rendered travel pending']];
runs.getRange('B5').formulas=[['=COUNTIF(D8:D34,"Verified")']];runs.getRange('E5').formulas=[['=COUNTIF(D8:D34,"Pending")']];
mechanics.getRange('A51:E51').copyFrom(mechanics.getRange('A50:E50'),'all');mechanics.getRange('A51:E51').format.rowHeight=64;mechanics.getRange('A51:E51').format.verticalAlignment='center';
mechanics.getRange('A51:E51').values=[['OCE11','Vessel body collision fits its art','Bounded unoccupied authority configuration replicated to peers','Native wall sweeps and two-process profile replication verified','Rendered piloting, rotation clearance and dock travel pending']];
wb.recalculate();
if(runs.getRange('B5').values[0][0]!==22||runs.getRange('E5').values[0][0]!==5)throw Error('Summary counts mismatch');
runs.getRange('D34').values=[['Pending']];wb.recalculate();if(runs.getRange('E5').values[0][0]!==6)throw Error('Counter dependency failed');
runs.getRange('D34').values=[['Verified']];wb.recalculate();
for(const[s,r,v,f]of prior){const c=wb.worksheets.getItem(s).getRange(r);if(norm(c.values)!==v||JSON.stringify(c.formulas)!==f)throw Error('Prior records changed: '+s);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const[s,r,n]of [['Unreal verification','A32:H34','hull-runs'],['Unreal verification','A2:H5','counts'],['Mechanics','A51:E51','hull-mechanic']])await fs.writeFile(out+'/'+n+'.png',new Uint8Array(await(await wb.render({sheetName:s,range:r,scale:1,format:'png'})).arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('HULL_TRACKER_PASS 22 scoped verifications / 5 pending; prior assets and records unchanged');
