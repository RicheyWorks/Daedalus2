import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,root,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const sheet=wb.worksheets.getItem('Assets'),summary=wb.worksheets.getItem('Production');
const old=sheet.getRange('A6:P189').values;if(old.length!==184||old.some(row=>!row[0]))throw Error('Unexpected184baseline');
const ids=new Set(old.map(row=>row[0]));
const data=JSON.parse(await fs.readFile(root+'/production-data.json','utf8')).filter(a=>!ids.has(a.id));
if(data.length!==43||new Set(data.map(a=>a.id)).size!==43)throw Error('Expected43newGalleryexports');
const first=190,end=232;
sheet.getRange(`A${first}:P${end}`).values=data.map(a=>[a.id,a.kind,a.realm,a.role,a.triangles,a.rig,a.clips,
 'Validated','Pending','Binding pending','gallery-buildout/'+a.file,a.sha256,a.role_count,a.source_monster??'n.a.','n.a.',0]);
sheet.getRange(`A${first}:P${end}`).format.font={name:'Arial',size:10};sheet.getRange(`A${first}:P${end}`).format.rowHeight=38;
sheet.getRange(`D${first}:D${end}`).format.wrapText=true;sheet.getRange(`G${first}:G${end}`).format.wrapText=true;
sheet.getRange(`E${first}:E${end}`).setNumberFormat('#,##0');sheet.getRange(`M${first}:M${end}`).setNumberFormat('0');
sheet.getRange(`I${first}:I${end}`).dataValidation={rule:{type:'list',values:['Pending','Imported','Play proven']}};
sheet.getRange(`J${first}:J${end}`).dataValidation={rule:{type:'list',values:['Binding pending','Core tested','Play proven']}};
for(const row of [7,8,9,10,11])summary.getRange(`D${row}:H${row}`).formulas=[[
 `=SUMIFS(Assets!$M$6:$M$${end},Assets!$C$6:$C$${end},A${row})`,
 `=COUNTIFS(Assets!$C$6:$C$${end},A${row},Assets!$B$6:$B$${end},"Character",Assets!$H$6:$H$${end},"Validated")`,
 `=COUNTIFS(Assets!$C$6:$C$${end},A${row},Assets!$B$6:$B$${end},"Character",Assets!$I$6:$I$${end},"Play proven")`,
 `=C${row}-D${row}`,`=COUNTIFS(Assets!$C$6:$C$${end},A${row})`]];
summary.getRange('B14').formulas=[[`=SUM(Assets!E6:E${end})`]];
summary.getRange('B15').formulas=[[`=COUNTIFS(Assets!B6:B${end},"Prop")+COUNTIFS(Assets!B6:B${end},"Item")`]];
summary.getRange('A17').values=[['Codex first kits only. Gallery 56 exports; native behaviors/visual acceptance pending. LODs are not new roles.']];
const mechanics=wb.worksheets.getItem('Mechanics');
mechanics.getRange('A32:E34').values=[
 ['GAL01','Living paintings and colour knowledge','32 role cast with 19 creature/mount/pet visuals','Art validated; abilities proposed','Restore city murals and make colour useful'],
 ['GAL02','Frame streets, workstations, drone/sea arrival docks','24 modular props, 2 m snap grid','Static validation; collision/interaction pending','Connect framed plazas, workshops and visiting realms'],
 ['GAL03','Curator reward must require actual objective proof','Existing DCS found choice + FRAME_PLATE','Owner notified; authoritative gating pending','Claims of a rescue/discovery must reflect completed actions']];
mechanics.getRange('A32:E34').format.font={name:'Arial',size:10};mechanics.getRange('A32:E34').format.rowHeight=52;mechanics.getRange('B32:E34').format.wrapText=true;
wb.recalculate();if(Number(summary.getRange('D8').values[0][0])!==32||Number(summary.getRange('H8').values[0][0])!==56)throw Error('Gallerycountswrong');
const previous=sheet.getRange('I190').values[0][0],proof=Number(summary.getRange('F8').values[0][0]);sheet.getRange('I190').values=[['Play proven']];wb.recalculate();
if(Number(summary.getRange('F8').values[0][0])!==proof+1)throw Error('Proof formula failed');sheet.getRange('I190').values=[[previous]];wb.recalculate();
if(JSON.stringify(sheet.getRange('A6:P189').values)!==JSON.stringify(old)||Number(summary.getRange('F8').values[0][0])!==proof)throw Error('Old status changed');
console.log((await wb.inspect({kind:'region',sheetId:summary.name,range:'A6:H15',maxChars:1800,tableMaxRows:12,tableMaxCols:8})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:600})).ndjson);
for(const [name,range,suffix] of [['Production','A1:H24',''],['Assets','A209:J217','-props'],['Mechanics','A32:E34','-gallery']]){
 const picture=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(out+'/'+name+suffix+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');console.log('GALLERY_TRACKER_PASS227 unique exports');
