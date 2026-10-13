import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,root,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const assets=wb.worksheets.getItem('Assets'),summary=wb.worksheets.getItem('Production'),mechanics=wb.worksheets.getItem('Mechanics');
const old=assets.getRange('A6:N163').values;if(old.length!==158||old.some(r=>!r[0]))throw Error('Unexpected baseline');
const data=[];
for(const [folder,realm] of [['gallery-buildout/cast','Gallery City'],['portal-hero-polish','Portal Realm'],['portal-hero-lods','Portal Realm'],['portal-slime-polish','Portal Realm']]){
 const manifest=JSON.parse(await fs.readFile(root+'/'+folder+'/manifest.json','utf8'));
 const checked=new Set(JSON.parse(await fs.readFile(root+'/'+folder+'/validation.json','utf8')).passed.map(r=>r.asset));
 for(const a of manifest.assets){
  if(folder==='portal-hero-lods'&&a.lod_level===0)continue;
  if(!checked.has(a.id))throw Error('Unvalidated export '+a.id);
  data.push({...a,realm,file:folder+'/'+a.file});
 }
}
const ids=new Set(old.map(r=>r[0]));for(const a of data){if(ids.has(a.id))throw Error('Duplicate '+a.id);ids.add(a.id);}
if(data.length!==26)throw Error('Expected twenty-six additive exports');
const first=164,end=189;
assets.getRange(`A${first}:N${end}`).values=data.map(a=>[a.id,'Character',a.realm,a.role,a.triangles,a.rig,'Idle, Walk, Attack, Hurt','Validated','Pending','Binding pending',a.file,a.sha256,a.role_count??1,a.source_monster??'n.a.']);
assets.getRange('O5:P5').values=[['Population ID','LOD level']];
assets.getRange(`O${first}:P${end}`).values=data.map(a=>[a.population_id??'n.a.',a.lod_level??0]);
assets.getRange('O5:P5').format={fill:'#243746',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'}};
assets.getRange(`A${first}:P${end}`).format.font={name:'Arial',size:10};assets.getRange(`A${first}:P${end}`).format.rowHeight=38;
assets.getRange(`D${first}:D${end}`).format.wrapText=true;assets.getRange(`G${first}:G${end}`).format.wrapText=true;
assets.getRange(`E${first}:E${end}`).setNumberFormat('#,##0');assets.getRange(`M${first}:M${end}`).setNumberFormat('0');
assets.getRange(`I${first}:I${end}`).dataValidation={rule:{type:'list',values:['Pending','Imported','Play proven']}};
assets.getRange(`J${first}:J${end}`).dataValidation={rule:{type:'list',values:['Binding pending','Core tested','Play proven']}};
assets.getRange('A4').values=[['Codex export register; excludes other teams. Validation is not visual approval or Play proof. LODs count as exports, not new roles.']];
for(const r of [7,8,9,10,11])summary.getRange(`D${r}:H${r}`).formulas=[[
 `=SUMIFS(Assets!$M$6:$M$${end},Assets!$C$6:$C$${end},A${r})`,
 `=COUNTIFS(Assets!$C$6:$C$${end},A${r},Assets!$B$6:$B$${end},"Character",Assets!$H$6:$H$${end},"Validated")`,
 `=COUNTIFS(Assets!$C$6:$C$${end},A${r},Assets!$B$6:$B$${end},"Character",Assets!$I$6:$I$${end},"Play proven")`,
 `=C${r}-D${r}`,`=COUNTIFS(Assets!$C$6:$C$${end},A${r})`]];
summary.getRange('B14').formulas=[[`=SUM(Assets!E6:E${end})`]];
summary.getRange('B15').formulas=[[`=COUNTIFS(Assets!B6:B${end},"Prop")+COUNTIFS(Assets!B6:B${end},"Item")`]];
summary.getRange('A17').values=[['Codex kit only. Refined hero/slime individuals and LODs add exports without new role types.']];
summary.getRange('A20:E22').values=[['Approved population','Target individuals','Validated candidates','Play proven','Remaining art'],['Enemies',500,10,0,490],['Friendlies',500,0,0,500]];
summary.getRange('A20:E20').format={fill:'#243746',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'}};
summary.getRange('A24').values=[['50 types × 10 each per side. Population IDs linked to ten slime candidates. Boss designs are separate proposals.']];
mechanics.getRange('A25:E31').values=[
 ['PORT09','Kings favours, rescues, unicorn requests','Ordered quest core','Core tested; persistence and rewards pending','Royal roads connect rescued towns and helpful herds'],
 ['PORT10','Additive 3D battle presentation','Battle director + presentation actor','Isolated UE compile/link; live binding pending','Preserve classic rules and improve expressive battles'],
 ['PORT11','Hero/slime polish and hero detail levels','Hero + 10 slimes + 2 reduced exports','Exports validated; visual/native acceptance pending','Distinct silhouettes retain the raw realm identity'],
 ['PORT12','Dragon egg and configured land annotations','Java egg + DRR codec parity','Targeted Java parity tested; ownership authority pending','Native drake semantics preserved without demo deed authority'],
 ['SEA01','Boats/submarines enter ocean; shores return; underwater docks connect worlds','Dock route core','Core tested; vessels/live transitions pending','Explore sea routes and drowned settlements'],
 ['LAND01','Long prairie range and submerged seabed','Terrain core + native actor','Isolated UE compile/link; placement pending','Buffalo ranges, travel corridors and ocean exploration'],
 ['CAST01','50 enemy and 50 friendly types, 10 each','1000 individual production IDs','10 enemy candidates validated; others planned','Kings, rescues and unicorn biddings drive the cast']];
mechanics.getRange('A25:E31').format.font={name:'Arial',size:10};mechanics.getRange('A25:E31').format.rowHeight=52;mechanics.getRange('B25:E31').format.wrapText=true;
wb.recalculate();if(Number(summary.getRange('D8').values[0][0])!==13||Number(summary.getRange('E9').values[0][0])!==77)throw Error('Counts failed');
const previous=assets.getRange('I177').values[0][0],proof=Number(summary.getRange('F9').values[0][0]);assets.getRange('I177').values=[['Play proven']];wb.recalculate();
if(Number(summary.getRange('F9').values[0][0])!==proof+1)throw Error('Proof formula failed');assets.getRange('I177').values=[[previous]];wb.recalculate();
if(Number(summary.getRange('F9').values[0][0])!==proof||JSON.stringify(assets.getRange('A6:N163').values)!==JSON.stringify(old))throw Error('Existing data/status changed');
console.log((await wb.inspect({kind:'region',sheetId:summary.name,range:'A6:H15',maxChars:1800,tableMaxRows:12,tableMaxCols:8})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:700})).ndjson);
for(const [sheet,range,suffix] of [['Production','A1:H24',''],['Assets','A164:J172','-new'],['Mechanics','A25:E31','-new']]){
 const picture=await wb.render({sheetName:sheet,range,scale:1,format:'png'});await fs.writeFile(out+'/'+sheet+suffix+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');console.log('TRACKER_PASS 184 unique exports; prior statuses preserved');
