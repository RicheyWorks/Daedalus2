import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out,mode]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
if(mode==='preview'){
  await fs.writeFile(out+'/before.png',new Uint8Array(await(await wb.render({sheetName:'Unreal verification',range:'A39:H40',scale:1,format:'png'})).arrayBuffer()));
  console.log((await wb.inspect({kind:'table',range:'Unreal verification!A39:H40',include:'values,formulas',tableMaxRows:2,tableMaxCols:8})).ndjson);
  process.exit(0);
}
const proof=JSON.parse(await fs.readFile(repo+'/docs/production/realm-land-api-proof.json','utf8'));
const grid=JSON.parse(await fs.readFile(repo+'/docs/production/land-grid-parity-proof.json','utf8'));
const layout=JSON.parse(await fs.readFile(repo+'/docs/production/realm-layout-store-proof.json','utf8'));
if(!proof.verify?.test_summary_counts?.at(-1))throw Error('Missing API verification');
const norm=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const prior=[['Assets','A1:Q348'],['Production','A1:H24'],['Mechanics','A1:E54'],['Unreal verification','A8:H40']].map(([s,r])=>[s,r,norm(wb.worksheets.getItem(s).getRange(r).values),JSON.stringify(wb.worksheets.getItem(s).getRange(r).formulas)]);
const runs=wb.worksheets.getItem('Unreal verification'),mechanics=wb.worksheets.getItem('Mechanics');
if(runs.getRange('A41').values[0][0]||mechanics.getRange('A55').values[0][0])throw Error('Destination already occupied');
const rows=[
 ['LAND-GRID','Shared Java, native and Python plot addressing','All realms','Verified',grid.verify_seconds,`${grid.core_tests} core tests. 10,000 cell and 40,000 estate parity rows.`,'land-grid-parity-proof.json','Addressing only. Native gcc/clang CI checks Python against the Java-tested digest.'],
 ['LAND-STORE','Persistent physical estate placement','All realms','Verified',layout.verify_seconds,`${layout.core_tests} core tests. Restart, overlap, hub and stale-writer checks.`,'realm-layout-store-proof.json','10,000-estate snapshot. No wallet ownership, distributed store or editor-import claim.'],
 ['LAND-API','Authenticated district reads after server restart','Java host','Verified',proof.verify.seconds,`${proof.verify.test_summary_counts[0]} core / ${proof.verify.test_summary_counts.at(-1)} server tests.`,'realm-land-api-proof.json','Actual JWT HTTP restart, move, quota and corruption checks. Unreal consumer integration remains pending.']
];
for(let i=0;i<rows.length;i++){const r=41+i;runs.getRange(`A${r}:H${r}`).copyFrom(runs.getRange('A40:H40'),'all');runs.getRange(`A${r}:H${r}`).format.rowHeight=110;runs.getRange(`A${r}:H${r}`).values=[rows[i]];}
const mechanicsRows=[
 ['SYS02','Consistent land numbers in every realm','100x100 spiral and 10x10 districts. Estate identity is independent of current position.','All 10,000 cells and 40,000 estate candidates agree across languages.','Grid addresses do not establish mintable supply or ownership.'],
 ['SYS03','Estates can move while retaining identity','Explicit hub reservation and overlap checks. Atomic local snapshots and revision conflicts.','Restart and 10,000-estate persistence verified.','Authorized move API, production backups and distributed authority remain pending.'],
 ['SYS04','Load placed lands one district at a time','JWT district API returns current cells, seed strings and layout revision.','Actual HTTP restart and identity-preserving move verified.','Unreal subscription, terrain generation and editor layout import remain pending.']
];
for(let i=0;i<mechanicsRows.length;i++){const r=55+i;mechanics.getRange(`A${r}:E${r}`).copyFrom(mechanics.getRange('A54:E54'),'all');mechanics.getRange(`A${r}:E${r}`).format.rowHeight=110;mechanics.getRange(`A${r}:E${r}`).values=[mechanicsRows[i]];}
runs.getRange('B5').formulas=[['=COUNTIF(D8:D43,"Verified")']];runs.getRange('E5').formulas=[['=COUNTIF(D8:D43,"Pending")']];
wb.recalculate();if(runs.getRange('B5').values[0][0]!==31||runs.getRange('E5').values[0][0]!==5)throw Error('Summary mismatch');
runs.getRange('D43').values=[['Pending']];wb.recalculate();if(runs.getRange('B5').values[0][0]!==30||runs.getRange('E5').values[0][0]!==6)throw Error('Counter dependency mismatch');
runs.getRange('D43').values=[['Verified']];wb.recalculate();
for(const[s,r,v,f]of prior){const c=wb.worksheets.getItem(s).getRange(r);if(norm(c.values)!==v||JSON.stringify(c.formulas)!==f)throw Error('Prior records changed: '+s);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const[s,r,n]of [['Unreal verification','A41:H43','land-runs'],['Unreal verification','A2:H5','counts'],['Mechanics','A55:E57','land-mechanics']])await fs.writeFile(out+'/'+n+'.png',new Uint8Array(await(await wb.render({sheetName:s,range:r,scale:1,format:'png'})).arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('LAND_TRACKER_PASS 31 scoped verifications /5 pending. Prior records preserved.');
