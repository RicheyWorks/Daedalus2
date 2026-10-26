import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,root,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const assets=wb.worksheets.getItem('Assets'),summary=wb.worksheets.getItem('Production');
const old=assets.getRange('A6:P232').values;if(old.length!==227||old.some(row=>!row[0]))throw Error('Expected227baseline');
const data=JSON.parse(await fs.readFile(root+'/production-data.json','utf8'));const ids=new Set(old.map(r=>r[0]));
if(data.length!==56||data.filter(a=>a.reused_source).length!==1||data.some(a=>ids.has(a.id)))throw Error('Invalid additive/reuse set');
const first=233,end=288;
assets.getRange(`A${first}:P${end}`).values=data.map(a=>[a.id,a.kind,a.realm,a.role,a.triangles,a.rig,a.clips,
 'Validated','Pending','Binding pending','parcels-buildout/'+a.file,a.sha256,a.role_count,'n.a.','n.a.',0]);
assets.getRange('Q5').values=[['Provenance']];assets.getRange('Q5').format={fill:'#243746',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'}};
assets.getRange(`Q${first}:Q${end}`).values=data.map(a=>[a.reused_source?'Reused original AMF; owner retained':'Codex original']);
assets.getRange(`Q5:Q${end}`).format.columnWidth=42;assets.getRange(`Q${first}:Q${end}`).format.wrapText=true;
assets.getRange(`A${first}:Q${end}`).format.font={name:'Arial',size:10};assets.getRange(`A${first}:Q${end}`).format.rowHeight=38;
assets.getRange(`D${first}:D${end}`).format.wrapText=true;assets.getRange(`G${first}:G${end}`).format.wrapText=true;
assets.getRange(`E${first}:E${end}`).setNumberFormat('#,##0');assets.getRange(`M${first}:M${end}`).setNumberFormat('0');
assets.getRange(`I${first}:I${end}`).dataValidation={rule:{type:'list',values:['Pending','Imported','Play proven']}};
assets.getRange(`J${first}:J${end}`).dataValidation={rule:{type:'list',values:['Binding pending','Core tested','Play proven']}};
for(const row of [7,8,9,10,11])summary.getRange(`D${row}:H${row}`).formulas=[[
 `=SUMIFS(Assets!$M$6:$M$${end},Assets!$C$6:$C$${end},A${row})`,
 `=COUNTIFS(Assets!$C$6:$C$${end},A${row},Assets!$B$6:$B$${end},"Character",Assets!$H$6:$H$${end},"Validated")`,
 `=COUNTIFS(Assets!$C$6:$C$${end},A${row},Assets!$B$6:$B$${end},"Character",Assets!$I$6:$I$${end},"Play proven")`,
 `=C${row}-D${row}`,`=COUNTIFS(Assets!$C$6:$C$${end},A${row})`]];
summary.getRange('B14').formulas=[[`=SUM(Assets!E6:E${end})`]];
summary.getRange('B15').formulas=[[`=COUNTIFS(Assets!B6:B${end},"Prop")+COUNTIFS(Assets!B6:B${end},"Item")`]];
summary.getRange('A17').values=[['Codex kits: 283 unique asset references, including one unchanged AMF reuse. Export validation is not Play proof.']];
const mechanics=wb.worksheets.getItem('Mechanics');mechanics.getRange('A35:E37').values=[
 ['PAR01','Mail, farming and boundary guidance','32 cast/creature/mount/pet role models','Art validated; behaviors pending','Help neighbours and reconnect isolated plots'],
 ['PAR02','Roads, fields, mail stations, helipad and ocean docks','23 original props + one reused AMF trough','Static validation; interactions/transport pending','Farm roads connect village work to wider journeys'],
 ['PAR03','Reuse existing geometry without copying authority','Original AMF trough ID/SHA retained','No tonic transaction behavior inherited','Water supplies and companion care use explicit host rules']];
mechanics.getRange('A35:E37').format.font={name:'Arial',size:10};mechanics.getRange('A35:E37').format.rowHeight=52;mechanics.getRange('B35:E37').format.wrapText=true;
wb.recalculate();if(Number(summary.getRange('D11').values[0][0])!==32||Number(summary.getRange('H11').values[0][0])!==56)throw Error('Parcels counts failed');
const previous=assets.getRange('I233').values[0][0],proof=Number(summary.getRange('F11').values[0][0]);assets.getRange('I233').values=[['Play proven']];wb.recalculate();
if(Number(summary.getRange('F11').values[0][0])!==proof+1)throw Error('Proof formula failed');assets.getRange('I233').values=[[previous]];wb.recalculate();
if(JSON.stringify(assets.getRange('A6:P232').values)!==JSON.stringify(old)||Number(summary.getRange('F11').values[0][0])!==proof)throw Error('Prior statuses changed');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:600})).ndjson);
for(const [name,range,suffix] of [['Production','A1:H24',''],['Mechanics','A35:E37','-parcels'],['Assets','A280:Q288','-reuse']]){
 const picture=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(out+'/'+name+suffix+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');console.log('PARCELS_TRACKER_PASS283 references,1 reuse');
