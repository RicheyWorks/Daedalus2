import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const assets=wb.worksheets.getItem('Assets'),production=wb.worksheets.getItem('Production'),mechanics=wb.worksheets.getItem('Mechanics');
const previous=JSON.stringify(assets.getRange('A6:Q344').values);
const native=JSON.stringify(wb.worksheets.getItem('Unreal verification').getRange('A1:H23').values);
const story=JSON.stringify(mechanics.getRange('A1:E43').values);
if(assets.getRange('A345').values[0][0])throw Error('Expected unused asset row');
const p=JSON.parse(await fs.readFile(repo+'/docs/production/ocean-terrain-proof.json','utf8'));
assets.getRange('A345:Q345').values=[['Terrain_Ocean_Seed42013_Sector','Terrain','Ocean Realm','Seeded sea sector and floating dock',p.triangles,'static',0,'Generated','Pending','Server registration and realm loading pending',p.delivery_directory+'/ocean.glb',p.files['ocean.glb'].sha256,0,'n.a.','n.a.',0,'Codex procedural terrain; generator v1']];
assets.getRange('A345:Q345').format.font={name:'Arial',size:10};assets.getRange('A345:Q345').format.wrapText=true;assets.getRange('A345:Q345').format.rowHeight=96;
assets.getRange('H345:I345').format.fill='#FFF2CC';
for(let row=7;row<=11;row++)for(const col of ['D','E','F','H']){
 const range=production.getRange(col+row);range.formulas=[[range.formulas[0][0].replaceAll('$344','$345')]];
}
production.getRange('A12:H12').values=[['Ocean Realm','Sol / Codex','',0,0,0,'',1]];
production.getRange('D12').formulas=[['=SUMIFS(Assets!$M$6:$M$345,Assets!$C$6:$C$345,A12)']];
production.getRange('E12').formulas=[['=COUNTIFS(Assets!$C$6:$C$345,A12,Assets!$B$6:$B$345,"Character",Assets!$H$6:$H$345,"Validated")']];
production.getRange('F12').formulas=[['=COUNTIFS(Assets!$C$6:$C$345,A12,Assets!$B$6:$B$345,"Character",Assets!$I$6:$I$345,"Play proven")']];
production.getRange('G12').formulas=[['=IF(C12="","",C12-D12)']];
production.getRange('H12').formulas=[['=COUNTIF(Assets!C6:C345,A12)']];
production.getRange('A12:H12').format.font={name:'Arial',size:10};
production.getRange('B14').formulas=[['=SUM(Assets!E6:E345)']];
production.getRange('B15').formulas=[['=COUNTIFS(Assets!B6:B345,"Prop")+COUNTIFS(Assets!B6:B345,"Item")']];
production.getRange('A17').values=[['340 unique asset references, including one unchanged AMF reuse and one generated Ocean sector. Export is not Play proof.']];
production.getRange('A18').values=[['Ocean character-role target is not set yet; the generated terrain adds no character roles.']];
mechanics.getRange('A44:E44').values=[['OCE04','Seeded open sea and floating dock','Chunk generation; existing save/mesh formats','706 core tests passed; server registration and Unreal acceptance pending','Generate nearby sea chunks; preserve player edits before regeneration']];
mechanics.getRange('A44:E44').format.font={name:'Arial',size:10};mechanics.getRange('A44:E44').format.wrapText=true;mechanics.getRange('A44:E44').format.rowHeight=76;
wb.recalculate();
if(Number(production.getRange('B14').values[0][0])!==362614||Number(production.getRange('B15').values[0][0])!==131||Number(production.getRange('H12').values[0][0])!==1||Number(production.getRange('F12').values[0][0])!==0)throw Error('Ocean totals mismatch');
assets.getRange('E345').values=[[p.triangles+1]];wb.recalculate();if(Number(production.getRange('B14').values[0][0])!==362615)throw Error('Total dependency failure');
assets.getRange('E345').values=[[p.triangles]];wb.recalculate();
if(previous!==JSON.stringify(assets.getRange('A6:Q344').values)||native!==JSON.stringify(wb.worksheets.getItem('Unreal verification').getRange('A1:H23').values)||story!==JSON.stringify(mechanics.getRange('A1:E43').values))throw Error('Prior records changed');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [sheetName,range,name]of [['Production','A6:H18','production'],['Assets','A345:J345','asset'],['Assets','K345:Q345','asset-source']]){
 const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(out+'/'+name+'.png',new Uint8Array(await blob.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('OCEAN_TRACKER_PASS340refs362614tri131props;339priorassetsandnativeproofunchanged');
