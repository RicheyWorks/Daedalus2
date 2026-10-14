import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,delivery,proofPath,out]=process.argv.slice(2);
await fs.mkdir(out,{recursive:true});
const manifest=JSON.parse(await fs.readFile(delivery+'/manifest.json','utf8'));
const proof=JSON.parse(await fs.readFile(proofPath,'utf8'));
if(manifest.assets.length!==3||!proof.rendered_inspection_capture||proof.rendered_gameplay_verified)throw Error('Inspection scope mismatch');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const norm=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const preserved=[['Assets','A1:Q345'],['Mechanics','A1:E49'],['Unreal verification','A8:H30']].map(([s,r])=>[s,r,norm(wb.worksheets.getItem(s).getRange(r).values),JSON.stringify(wb.worksheets.getItem(s).getRange(r).formulas)]);
const assets=wb.worksheets.getItem('Assets'),production=wb.worksheets.getItem('Production'),runs=wb.worksheets.getItem('Unreal verification'),mechanics=wb.worksheets.getItem('Mechanics');
if(assets.getRange('A346').values[0][0]||runs.getRange('A31').values[0][0]||mechanics.getRange('A50').values[0][0])throw Error('Expected append rows');
for(let i=0;i<3;i++)assets.getRange(`A${346+i}:Q${346+i}`).copyFrom(assets.getRange('A345:Q345'),'all');
assets.getRange('A346:Q348').values=manifest.assets.map(a=>[a.id,'Prop','Ocean Realm',a.role,a.triangles,'static',0,'Validated','Private import','Dock travel binding pending','ocean-vessels/'+a.file,a.sha256,0,'n.a.','n.a.',0,'Original Codex Blender mesh; private Unreal inspection']);
for(const range of ['D7:H12','B14:B15']){const r=production.getRange(range);r.formulas=r.formulas.map(row=>row.map(f=>f.replaceAll('$345','$348').replaceAll(':E345',':E348').replaceAll(':B345',':B348').replaceAll(':C345',':C348')));}
production.getRange('A17').values=[['343 unique asset references. Three Ocean props add no character roles. Export and inspection are not Play proof.']];
production.getRange('A18').values=[['Ocean character-role target is not set yet; terrain and vessel props add no character roles.']];
runs.getRange('A31:H31').copyFrom(runs.getRange('A30:H30'),'all');
runs.getRange('A31:H31').values=[['HARBOR-RENDER','Private Ocean harbor inspection','Ocean','Verified',proof.elapsed_seconds,proof.scope,'ocean-scene-http-proof.json','64 chunks and 3 props rendered; controls and realm transfer pending']];
runs.getRange('A31:H31').format.rowHeight=88;
runs.getRange('B5').formulas=[['=COUNTIF(D8:D31,"Verified")']];runs.getRange('E5').formulas=[['=COUNTIF(D8:D31,"Pending")']];
mechanics.getRange('A50:E50').copyFrom(mechanics.getRange('A49:E49'),'all');
mechanics.getRange('A50:E50').values=[['OCE10','Boat and submarine boarding at docks','Original skiff, submarine and dock; waterline pivots and +X forward','3 static exports validated; private Unreal harbor capture verified','Boarding, hull collision and destination streaming acceptance pending']];
mechanics.getRange('A50:E50').format.rowHeight=88;
wb.recalculate();
function verify(){if(production.getRange('B14').values[0][0]!==379408||production.getRange('B15').values[0][0]!==134||production.getRange('H12').values[0][0]!==4||runs.getRange('B5').values[0][0]!==19||runs.getRange('E5').values[0][0]!==5)throw Error('Summary mismatch');}
verify();
assets.getRange('E348').values=[[8353]];runs.getRange('D31').values=[['Pending']];wb.recalculate();
if(production.getRange('B14').values[0][0]!==379409||runs.getRange('E5').values[0][0]!==6)throw Error('Dependency failure');
assets.getRange('E348').values=[[8352]];runs.getRange('D31').values=[['Verified']];wb.recalculate();verify();
for(const[s,r,v,f]of preserved){const current=wb.worksheets.getItem(s).getRange(r);if(norm(current.values)!==v||JSON.stringify(current.formulas)!==f)throw Error('Prior records changed: '+s);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const[s,r,n]of [['Production','A6:H18','production'],['Assets','A346:J348','assets'],['Unreal verification','A31:H31','inspection'],['Mechanics','A50:E50','mechanic']])await fs.writeFile(out+'/'+n+'.png',new Uint8Array(await(await wb.render({sheetName:s,range:r,scale:1,format:'png'})).arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('OCEAN_SCENE_TRACKER_PASS 343 assets / 379408 triangles / 19 scoped verifications / 5 pending');
