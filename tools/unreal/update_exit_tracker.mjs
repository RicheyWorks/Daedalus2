import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const assets=wb.worksheets.getItem('Assets'),mechanics=wb.worksheets.getItem('Mechanics');
const sheet=wb.worksheets.getItem('Unreal verification');
const savedAssets=JSON.stringify(assets.getRange('A1:Q344').values);
const savedMechanics=JSON.stringify(mechanics.getRange('A1:E40').values);
const original=JSON.stringify(sheet.getRange('A8:H17').values);
const pending=JSON.stringify(sheet.getRange('A19:H22').values);
if(sheet.getRange('D18').values[0][0]!=='Pending')throw Error('Expected pending remote exit row');
const proof=JSON.parse(await fs.readFile(repo+'/docs/production/ocean-exit-network-proof.json','utf8'));
if(proof.passed.length!==2||!proof.passed.every(p=>p.remote_dock_roundtrip_verified&&p.exit_key_dispatch_verified))throw Error('Missing round-trip proof');
for(const [i,p]of proof.passed.entries()){
 const row=i===0?18:23;
 sheet.getRange(`A${row}:H${row}`).values=[[`EXIT-${p.mode}`,`Remote ${p.mode} boarding and E-key exit`,'Ocean','Verified',p.elapsed_seconds,'Startup, handshake and round trip','ocean-exit-network-proof.json','Engine key event; physical device, art and realm loading pending']];
 sheet.getRange(`A${row}:H${row}`).format.font={name:'Arial',size:10};
 sheet.getRange(`A${row}:H${row}`).format.rowHeight=70;
 sheet.getRange(`B${row}:H${row}`).format.wrapText=true;
 sheet.getRange(`D${row}`).format.fill='#E8F5E9';
 sheet.getRange(`E${row}`).setNumberFormat('0.000');
}
sheet.getRange('B5').formulas=[['=COUNTIF(D8:D23,"Verified")']];
sheet.getRange('E5').formulas=[['=COUNTIF(D8:D23,"Pending")']];
sheet.getRange('D23').dataValidation={rule:{type:'list',values:['Verified','Pending']}};
mechanics.getRange('D41').values=[['Native and localhost E-key exit verified; art/physical controls pending']];
mechanics.getRange('D42').values=[['Localhost boat/submarine boarding and exit passed']];
wb.recalculate();
if(Number(sheet.getRange('B5').values[0][0])!==11||Number(sheet.getRange('E5').values[0][0])!==5)throw Error('Counter mismatch');
sheet.getRange('D23').values=[['Pending']];wb.recalculate();
if(Number(sheet.getRange('B5').values[0][0])!==10||Number(sheet.getRange('E5').values[0][0])!==6)throw Error('Counter dependency mismatch');
sheet.getRange('D23').values=[['Verified']];wb.recalculate();
if(savedAssets!==JSON.stringify(assets.getRange('A1:Q344').values)||savedMechanics!==JSON.stringify(mechanics.getRange('A1:E40').values)||original!==JSON.stringify(sheet.getRange('A8:H17').values)||pending!==JSON.stringify(sheet.getRange('A19:H22').values))throw Error('Unrelated records changed');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [name,range,suffix]of [['Unreal verification','A17:H23','exit'],['Unreal verification','A2:H5','counts'],['Mechanics','A41:E43','mechanics']]){
 const picture=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(out+'/'+suffix+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('EXIT_TRACKER_PASS: 11 verified runs, 5 pending checks; asset and unrelated records preserved');
