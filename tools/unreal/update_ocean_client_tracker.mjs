import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out,mode='client']=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
if(!['client','view'].includes(mode))throw Error('Unknown tracker mode');
const view=mode==='view',first=view?28:24,last=view?30:27,mechanicRow=view?49:48,expected=view?18:15;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const normalized=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const preserved=[['Assets','A1:Q345'],['Production','A1:H24'],['Mechanics',`A1:E${mechanicRow-1}`],['Unreal verification',`A8:H${first-1}`]]
 .map(([name,range])=>[name,range,normalized(wb.worksheets.getItem(name).getRange(range).values),JSON.stringify(wb.worksheets.getItem(name).getRange(range).formulas)]);
const read=async name=>JSON.parse((await fs.readFile(repo+'/docs/production/'+name,'utf8')).replace(/^\uFEFF/,''));
const prefix=view?'ocean-view':'ocean-client';
const build=await read(prefix+'-build-proof.json'),runtime=await read(prefix+'-runtime-proof.json'),http=await read(prefix+'-http-proof.json');
const decoder=runtime.tests.find(t=>t.fullTestPath===(view?'Daedalus.Ocean.SectorGeometry':'Daedalus.Ocean.HostChunkDecoder'));
if(!decoder||decoder.state!=='Success'||!http.packaged_server_to_native_client)throw Error('Missing verification proof');
const sheet=wb.worksheets.getItem('Unreal verification');
if(sheet.getRange(`A${first}`).values[0][0])throw Error('Expected unused verification rows');
sheet.getRange(`A${first}:H${last}`).values=view?[
 ['BUILD-VIEW','Complete 135-file plugin build','Ocean','Verified',build.builds[0].seconds,'48 build/link actions; full process','ocean-view-build-proof.json','Full source hashes and production DLL recorded'],
 ['GEOMETRY',decoder.fullTestPath,'Ocean','Verified',decoder.duration,'Native test body; excludes engine startup','ocean-view-runtime-proof.json','Seams/capacity/revisions/collision flags; no rendered acceptance'],
 ['HTTP-VIEW','Java saved terrain to native procedural mesh','Ocean','Verified',http.elapsed_seconds,http.scope,'ocean-view-http-proof.json','Clear revision removes old mesh; appearance/travel pending']
]:[
 ['BUILD-CLIENT','Complete 131-file plugin build','Ocean','Verified',build.builds[0].seconds,'46 build/link actions; full process','ocean-client-build-proof.json','Fresh base plus separately recorded lifecycle rebuild'],
 ['LIFECYCLE','Final EndPlay session-cancellation rebuild','Ocean','Verified',build.builds[1].seconds,'5 incremental compile/link actions','ocean-client-build-proof.json','All final production input hashes verified'],
 ['DECODE',decoder.fullTestPath,'Ocean','Verified',decoder.duration,'Native test body; excludes engine startup','ocean-client-runtime-proof.json','Headless DTO/session validation'],
 ['HTTP-CLIENT','Packaged Java to native Ocean client','Ocean','Verified',http.elapsed_seconds,http.scope,'ocean-client-http-proof.json','TLS/redirect, rendered gameplay and realm transfer pending']];
sheet.getRange(`A${first}:H${last}`).format.font={name:'Arial',size:10};sheet.getRange(`A${first}:H${last}`).format.wrapText=true;sheet.getRange(`A${first}:H${last}`).format.rowHeight=88;
sheet.getRange(`D${first}:D${last}`).format.fill='#E8F5E9';sheet.getRange(`E${first}:E${last}`).setNumberFormat('0.000');
sheet.getRange(`D${first}:D${last}`).dataValidation={rule:{type:'list',values:['Verified','Pending']}};
sheet.getRange('B5').formulas=[['=COUNTIF(D8:D'+last+',"Verified")']];sheet.getRange('E5').formulas=[['=COUNTIF(D8:D'+last+',"Pending")']];
const mechanics=wb.worksheets.getItem('Mechanics');
if(mechanics.getRange(`A${mechanicRow}`).values[0][0])throw Error('Expected unused mechanic row');
mechanics.getRange(`A${mechanicRow}:E${mechanicRow}`).values=[view
 ?['OCE09','Server sea chunks become native scene geometry','Canonical palette; neighbour remesh; local offsets; revisions preserved','135-file plugin / 4 native / 719 core tests pass; real geometry HTTP proof','Geometry verified; material appearance, rendered Play and realm travel pending']
 :['OCE08','Native client receives authenticated sea chunks','One in flight; bounded receive; strict DTO; stale-session guard','131-file plugin and 3 native tests pass; real Java/native HTTP passed','Local transport verified; scene meshes, TLS/redirect audit and travel pending']];
mechanics.getRange(`A${mechanicRow}:E${mechanicRow}`).format.font={name:'Arial',size:10};mechanics.getRange(`A${mechanicRow}:E${mechanicRow}`).format.wrapText=true;mechanics.getRange(`A${mechanicRow}:E${mechanicRow}`).format.rowHeight=88;
wb.recalculate();
if(Number(sheet.getRange('B5').values[0][0])!==expected||Number(sheet.getRange('E5').values[0][0])!==5)throw Error('Counter mismatch');
sheet.getRange(`D${last}`).values=[['Pending']];wb.recalculate();if(Number(sheet.getRange('B5').values[0][0])!==expected-1||Number(sheet.getRange('E5').values[0][0])!==6)throw Error('Counter dependency failure');
sheet.getRange(`D${last}`).values=[['Verified']];wb.recalculate();
for(const [name,range,values,formulas]of preserved){const r=wb.worksheets.getItem(name).getRange(range);if(values!==normalized(r.values)||formulas!==JSON.stringify(r.formulas))throw Error('Unrelated records changed: '+name);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [sheetName,range,name]of [['Unreal verification',`A${first}:H${last}`,'runs'],['Unreal verification','A2:H5','counts'],['Mechanics',`A${mechanicRow}:E${mechanicRow}`,'mechanic']]){
 const picture=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(out+'/'+name+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('NATIVE_TRACKER_PASS '+mode+' '+expected+' verified/5 pending; prior records preserved');
