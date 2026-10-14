import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const proof=JSON.parse(await fs.readFile(repo+'/docs/production/battle-cast-animation-proof.json','utf8'));
const test=proof.tests.find(t=>t.fullTestPath==='Daedalus.Battle.CastAnimations');
if(!test||test.state!=='Success'||test.errors||test.warnings)throw Error('Missing native proof');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const norm=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const prior=[['Assets','A1:Q348'],['Production','A1:H24'],['Mechanics','A1:E52'],['Unreal verification','A8:H36']].map(([s,r])=>[s,r,norm(wb.worksheets.getItem(s).getRange(r).values),JSON.stringify(wb.worksheets.getItem(s).getRange(r).formulas)]);
const runs=wb.worksheets.getItem('Unreal verification'),mechanics=wb.worksheets.getItem('Mechanics');
if(runs.getRange('A37').values[0][0]||mechanics.getRange('A53').values[0][0])throw Error('Expected unused rows');
for(let row=37;row<=38;row++){const r=runs.getRange(`A${row}:H${row}`);r.copyFrom(runs.getRange('A36:H36'),'all');r.format.rowHeight=80;}
runs.getRange('A37:H38').values=[
 ['BUILD-CAST','Full plugin with per-mesh battle clips','All casts','Verified',proof.seconds,'151-file snapshot c419b8b4','battle-cast-animation-proof.json','Later utility interfaces are outside this build snapshot.'],
 ['CAST-CLIPS',test.fullTestPath,'All casts','Verified',test.duration,'Native synthetic two-skeleton test body','battle-cast-animation-proof.json','Own clips, override compatibility, missing/null refusal. Imported art and rendered battle remain open.']];
runs.getRange('B5').formulas=[['=COUNTIF(D8:D38,"Verified")']];runs.getRange('E5').formulas=[['=COUNTIF(D8:D38,"Pending")']];
mechanics.getRange('A53:E53').copyFrom(mechanics.getRange('A52:E52'),'all');mechanics.getRange('A53:E53').format.rowHeight=80;
mechanics.getRange('A53:E53').values=[['PORT11','Each battle character uses its own skeleton clips','Bounded folder-local discovery with compatible explicit overrides','Synthetic native selection verified for two distinct skeletons','Imported clip names, director wiring, idle return and rendered battle still pending.']];
wb.recalculate();if(runs.getRange('B5').values[0][0]!==26||runs.getRange('E5').values[0][0]!==5)throw Error('Summary mismatch');
runs.getRange('D38').values=[['Pending']];wb.recalculate();if(runs.getRange('E5').values[0][0]!==6||runs.getRange('B5').values[0][0]!==25)throw Error('Dependency mismatch');
runs.getRange('D38').values=[['Verified']];wb.recalculate();
for(const[s,r,v,f]of prior){const c=wb.worksheets.getItem(s).getRange(r);if(norm(c.values)!==v||JSON.stringify(c.formulas)!==f)throw Error('Prior records changed: '+s);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const[s,r,n]of [['Unreal verification','A37:H38','cast-runs'],['Unreal verification','A2:H5','counts'],['Mechanics','A53:E53','cast-mechanic']])await fs.writeFile(out+'/'+n+'.png',new Uint8Array(await(await wb.render({sheetName:s,range:r,scale:1,format:'png'})).arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('BATTLE_TRACKER_PASS 26 scoped verifications / 5 pending; old records preserved.');
