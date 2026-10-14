import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const normalized=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const preserved=[['Assets','A1:Q345'],['Production','A1:H24'],['Mechanics','A1:E47'],['Unreal verification','A8:H23']]
 .map(([name,range])=>[name,range,normalized(wb.worksheets.getItem(name).getRange(range).values),JSON.stringify(wb.worksheets.getItem(name).getRange(range).formulas)]);
const read=async name=>JSON.parse((await fs.readFile(repo+'/docs/production/'+name,'utf8')).replace(/^\uFEFF/,''));
const build=await read('ocean-client-build-proof.json'),runtime=await read('ocean-client-runtime-proof.json'),http=await read('ocean-client-http-proof.json');
const decoder=runtime.tests.find(t=>t.fullTestPath==='Daedalus.Ocean.HostChunkDecoder');
if(!decoder||decoder.state!=='Success'||!http.packaged_server_to_native_client)throw Error('Missing verification proof');
const sheet=wb.worksheets.getItem('Unreal verification');
if(sheet.getRange('A24').values[0][0])throw Error('Expected unused verification rows');
sheet.getRange('A24:H27').values=[
 ['BUILD-CLIENT','Complete 131-file plugin build','Ocean','Verified',build.builds[0].seconds,'46 build/link actions; full process','ocean-client-build-proof.json','Fresh base plus separately recorded lifecycle rebuild'],
 ['LIFECYCLE','Final EndPlay session-cancellation rebuild','Ocean','Verified',build.builds[1].seconds,'5 incremental compile/link actions','ocean-client-build-proof.json','All final production input hashes verified'],
 ['DECODE',decoder.fullTestPath,'Ocean','Verified',decoder.duration,'Native test body; excludes engine startup','ocean-client-runtime-proof.json','Headless DTO/session validation'],
 ['HTTP-CLIENT','Packaged Java to native Ocean client','Ocean','Verified',http.elapsed_seconds,http.scope,'ocean-client-http-proof.json','TLS/redirect, rendered gameplay and realm transfer pending']];
sheet.getRange('A24:H27').format.font={name:'Arial',size:10};sheet.getRange('A24:H27').format.wrapText=true;sheet.getRange('A24:H27').format.rowHeight=88;
sheet.getRange('D24:D27').format.fill='#E8F5E9';sheet.getRange('E24:E27').setNumberFormat('0.000');
sheet.getRange('D24:D27').dataValidation={rule:{type:'list',values:['Verified','Pending']}};
sheet.getRange('B5').formulas=[['=COUNTIF(D8:D27,"Verified")']];sheet.getRange('E5').formulas=[['=COUNTIF(D8:D27,"Pending")']];
const mechanics=wb.worksheets.getItem('Mechanics');
if(mechanics.getRange('A48').values[0][0])throw Error('Expected unused mechanic row');
mechanics.getRange('A48:E48').values=[['OCE08','Native client receives authenticated sea chunks','One in flight; bounded receive; strict DTO; stale-session guard','131-file plugin and 3 native tests pass; real Java/native HTTP passed','Local transport verified; scene meshes, TLS/redirect audit and travel pending']];
mechanics.getRange('A48:E48').format.font={name:'Arial',size:10};mechanics.getRange('A48:E48').format.wrapText=true;mechanics.getRange('A48:E48').format.rowHeight=88;
wb.recalculate();
if(Number(sheet.getRange('B5').values[0][0])!==15||Number(sheet.getRange('E5').values[0][0])!==5)throw Error('Counter mismatch');
sheet.getRange('D27').values=[['Pending']];wb.recalculate();if(Number(sheet.getRange('B5').values[0][0])!==14||Number(sheet.getRange('E5').values[0][0])!==6)throw Error('Counter dependency failure');
sheet.getRange('D27').values=[['Verified']];wb.recalculate();
for(const [name,range,values,formulas]of preserved){const r=wb.worksheets.getItem(name).getRange(range);if(values!==normalized(r.values)||formulas!==JSON.stringify(r.formulas))throw Error('Unrelated records changed: '+name);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [sheetName,range,name]of [['Unreal verification','A24:H27','runs'],['Unreal verification','A2:H5','counts'],['Mechanics','A48:E48','mechanic']]){
 const picture=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(out+'/'+name+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('NATIVE_CLIENT_TRACKER_PASS15verified5pending;priorassetsmechanicsandverificationrowspreserved');
