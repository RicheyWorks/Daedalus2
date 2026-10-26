import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out,mode='store']=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
if(!['store','window','host'].includes(mode))throw Error('Unknown tracker mode');
const row=mode==='host'?47:mode==='window'?46:45;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const normalized=values=>JSON.stringify(values.map(row=>row.map(value=>value===null?'':value)));
const unchanged=[['Assets','A1:Q345'],['Production','A1:H24'],['Unreal verification','A1:H23'],['Mechanics',`A1:E${row-1}`]]
 .map(([name,range])=>[name,range,normalized(wb.worksheets.getItem(name).getRange(range).values),JSON.stringify(wb.worksheets.getItem(name).getRange(range).formulas)]);
const sheet=wb.worksheets.getItem('Mechanics');
if(sheet.getRange(`A${row}`).values[0][0])throw Error('Expected unused mechanic row');
sheet.getRange(`A${row}:E${row}`).values=[mode==='host'
 ?['OCE07','Authenticated sea-sector chunk reads','Existing chunk DTO; bounded sector; per-key quota','18 Ocean core + 14 server/auth tests; real prod HTTP/restart passed','Opt-in API verified; native client, realm registration and public hosting pending']
 :mode==='window'
 ?['OCE06','Nearby sea chunks use a bounded resident window','Nearest-first warmup; write-through edits; safe eviction','718 core tests and separate-process cache restart probe passed','Local cache verified; authenticated host routes and Unreal streaming pending']
 :['OCE05','Visited sea chunks retain edits, including empty chunks','Exclusive writer; seed/version checks; staged atomic saves','712 core tests and separate-JVM restart/OS lock probe passed','Local storage verified; host integration, public recovery and realm loading pending']];
sheet.getRange(`A${row}:E${row}`).format.font={name:'Arial',size:10};
sheet.getRange(`A${row}:E${row}`).format.wrapText=true;sheet.getRange(`A${row}:E${row}`).format.rowHeight=88;
wb.recalculate();
for(const [name,range,prior,formulas]of unchanged){
 const current=wb.worksheets.getItem(name).getRange(range).values;
 // Recalculation normalizes an imported blank cached formula from null to "".
 if(prior!==normalized(current)||formulas!==JSON.stringify(wb.worksheets.getItem(name).getRange(range).formulas)){
  throw Error('Unrelated cells changed: '+name);
 }
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
const picture=await wb.render({sheetName:'Mechanics',range:`A${row}:E${row}`,scale:1,format:'png'});
await fs.writeFile(out+'/mechanic.png',new Uint8Array(await picture.arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('STORE_TRACKER_PASS: '+mode+' mechanic added; prior records and summary formulas preserved');
