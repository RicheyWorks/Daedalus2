import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const read=async name=>JSON.parse(await fs.readFile(repo+'/docs/production/'+name,'utf8'));
const build=await read('ocean-effective-url-build-proof.json'),proof=await read('ocean-effective-url-redirect-proof.json');
if(proof.cases.length!==4||proof.cases[0].observed!=='accepted'||!proof.cases.slice(1).every(c=>c.observed==='refused'&&c.token_absent_from_logs))throw Error('Missing HTTP proof');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const norm=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const prior=[['Assets','A1:Q348'],['Production','A1:H24'],['Mechanics','A1:E51'],['Unreal verification','A8:H34']].map(([s,r])=>[s,r,norm(wb.worksheets.getItem(s).getRange(r).values),JSON.stringify(wb.worksheets.getItem(s).getRange(r).formulas)]);
const runs=wb.worksheets.getItem('Unreal verification'),mechanics=wb.worksheets.getItem('Mechanics');
if(runs.getRange('A35').values[0][0]||mechanics.getRange('A52').values[0][0])throw Error('Expected unused rows');
for(let row=35;row<=36;row++){const r=runs.getRange(`A${row}:H${row}`);r.copyFrom(runs.getRange('A34:H34'),'all');r.format.rowHeight=80;r.format.verticalAlignment='center';}
runs.getRange('A35:H36').values=[
 ['BUILD-URL','Full plugin with effective URL check','Ocean','Verified',build.seconds,'148-file production snapshot dab439d6','ocean-effective-url-build-proof.json','Five native Ocean tests passed. Later main metadata fixes are outside this snapshot.'],
 ['HTTP-URL','Direct response and three redirect refusals','Ocean','Verified',proof.cases.reduce((a,c)=>a+c.elapsed_seconds,0),'Four sequential UE loopback processes','ocean-effective-url-redirect-proof.json','Fixture build 261.13s. Same-origin credential forwarded. TLS and pre-forward prevention unproven.']];
runs.getRange('B5').formulas=[['=COUNTIF(D8:D36,"Verified")']];runs.getRange('E5').formulas=[['=COUNTIF(D8:D36,"Pending")']];
mechanics.getRange('A52:E52').copyFrom(mechanics.getRange('A51:E51'),'all');mechanics.getRange('A52:E52').format.rowHeight=80;
mechanics.getRange('A52:E52').values=[['OCE12','Accept chunks only from exact requested URL','Case-sensitive effective URL comparison before payload publication','Direct accepted. Path, port and path-case redirects refused in actual UE.','TLS, credential forwarding policy and live authenticated travel remain open.']];
wb.recalculate();
if(runs.getRange('B5').values[0][0]!==24||runs.getRange('E5').values[0][0]!==5)throw Error('Summary mismatch');
runs.getRange('D36').values=[['Pending']];wb.recalculate();if(runs.getRange('E5').values[0][0]!==6||runs.getRange('B5').values[0][0]!==23)throw Error('Dependency mismatch');
runs.getRange('D36').values=[['Verified']];wb.recalculate();
for(const[s,r,v,f]of prior){const c=wb.worksheets.getItem(s).getRange(r);if(norm(c.values)!==v||JSON.stringify(c.formulas)!==f)throw Error('Prior records changed: '+s);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const[s,r,n]of [['Unreal verification','A35:H36','redirect-runs'],['Unreal verification','A2:H5','counts'],['Mechanics','A52:E52','redirect-mechanic']])await fs.writeFile(out+'/'+n+'.png',new Uint8Array(await(await wb.render({sheetName:s,range:r,scale:1,format:'png'})).arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('REDIRECT_TRACKER_PASS 24 scoped verifications / 5 pending. Prior records unchanged.');
