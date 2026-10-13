import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const normalized=values=>JSON.stringify(values.map(row=>row.map(value=>value===null?'':value)));
const unchanged=[['Assets','A1:Q345'],['Production','A1:H24'],['Unreal verification','A1:H23'],['Mechanics','A1:E44']]
 .map(([name,range])=>[name,range,normalized(wb.worksheets.getItem(name).getRange(range).values),JSON.stringify(wb.worksheets.getItem(name).getRange(range).formulas)]);
const sheet=wb.worksheets.getItem('Mechanics');
if(sheet.getRange('A45').values[0][0])throw Error('Expected unused mechanic row');
sheet.getRange('A45:E45').values=[['OCE05','Visited sea chunks retain edits, including empty chunks','Exclusive writer; seed/version checks; staged atomic saves','712 core tests and separate-JVM restart/OS lock probe passed','Local storage verified; host integration, public recovery and realm loading pending']];
sheet.getRange('A45:E45').format.font={name:'Arial',size:10};
sheet.getRange('A45:E45').format.wrapText=true;sheet.getRange('A45:E45').format.rowHeight=88;
wb.recalculate();
for(const [name,range,prior,formulas]of unchanged){
 const current=wb.worksheets.getItem(name).getRange(range).values;
 // Recalculation normalizes an imported blank cached formula from null to "".
 if(prior!==normalized(current)||formulas!==JSON.stringify(wb.worksheets.getItem(name).getRange(range).formulas)){
  throw Error('Unrelated cells changed: '+name);
 }
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
const picture=await wb.render({sheetName:'Mechanics',range:'A45:E45',scale:1,format:'png'});
await fs.writeFile(out+'/mechanic.png',new Uint8Array(await picture.arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('STORE_TRACKER_PASS: OCE05 added; prior records and summary formulas preserved');
