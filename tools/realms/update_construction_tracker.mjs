import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [source,out,repo,mode]=process.argv.slice(2);
await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const runs=wb.worksheets.getItem('Unreal verification'), mechanics=wb.worksheets.getItem('Mechanics');
const render=async(s,r,n)=>fs.writeFile(out+'/'+n+'.png',new Uint8Array(await(await wb.render({sheetName:s,range:r,scale:1,format:'png'})).arrayBuffer()));
if(mode==='preview') {
  console.log((await wb.inspect({kind:'table',range:'Unreal verification!A41:H43',include:'values,formulas',tableMaxRows:3,tableMaxCols:8,maxChars:1200})).ndjson);
  await render('Unreal verification','A41:H43','before');
  process.exit(0);
}
const norm=v=>JSON.stringify(v.map(r=>r.map(c=>c===null?'':c)));
const kept=[['Assets','A1:Q348'],['Production','A1:H24'],['Mechanics','A1:E57'],['Unreal verification','A8:H43']].map(([s,r])=>[s,r,norm(wb.worksheets.getItem(s).getRange(r).values),JSON.stringify(wb.worksheets.getItem(s).getRange(r).formulas)]);
if(runs.getRange('A44').values[0][0]||mechanics.getRange('A58').values[0][0])throw Error('Append destination occupied');
const rows=[
 ['LAB-TERRAIN','Persistent walkable Labyrinth starter','Labyrinth','Verified',196,'1,591 reactor tests. Five seed connectivity, reload and edit preservation.','PR91 / labyrinth-terrain-proof.json','189 m starter export. Unreal import, collision and walkthrough pending.'],
 ['TEST-STORAGE','Production tests isolate developer saves','Java host','Verified',58.231,'14 checks across five prod-profile integration classes.','PR92 / PROD-TEST-STORAGE-ISOLATION.md','No ecology persistence warning in the focused run. Production settings unchanged.'],
 ['OCE-CATALOG','Ocean inventory definitions and theme','Ocean','Verified',24.736,'Java package: six tests. Native: 48/48. Six-catalog parity and packaged JWT HTTP passed.','PR93 / ocean-inventory-packaged-proof.json','Seconds cover Java package only. 13 definitions; live Unreal panel pending.'],
 ['OCE-EFFECTS','Ocean pickups, item effects and rewards','Ocean','Pending',null,'Inspection only. No item grants, repairs, oxygen or quest completion verified.','OCEAN-INVENTORY.md','Integrate existing authoritative bag and quest systems, then prove in game.']
];
for(let i=0;i<rows.length;i++){const r=44+i;runs.getRange(`A${r}:H${r}`).copyFrom(runs.getRange('A43:H43'),'all');runs.getRange(`A${r}:H${r}`).format.rowHeight=110;runs.getRange(`A${r}:H${r}`).values=[rows[i]];}
const pending=runs.getRange('D8:D43').values.findIndex(row=>row[0]==='Pending');
if(pending<0)throw Error('Missing source pending style');
runs.getRange('D47').copyFrom(runs.getRange('D'+(8+pending)),'all');
runs.getRange('D47').values=[['Pending']];
runs.getRange('D47').format.verticalAlignment='center';
const text=await fs.readFile(repo+'/engines/unreal/DaedalusLink/Content/Inventory/ocean.dic','utf8');
const items=text.split(/\r?\n/).filter(l=>l.startsWith('item ')).map(l=>{const f=l.split(' ');return{id:f[1],tab:f[2],actions:f[4],name:f.slice(5).join(' ')};});
if(items.length!==13||items.some(i=>i.actions!=='INSPECT'))throw Error('Unexpected catalog');
const additions=[
 ['LAB11','Walk a persistent starter maze','31x31 logical cells. Three-metre passages, two open boundary entrances.','Floor, headroom and all reachable corridor voxels checked for five seeds.','Live collision and entry alignment pending. Existing art preserved.'],
 ['OCE13','Browse Ocean inventory in shared tabs','Navigation, Diving, Salvage, Vessel and Quests plus All. Navy, teal and brass theme.','13 shared definitions, 48 native checks, Java/C++ parity and packaged authenticated reads.','Live UI and authoritative item effects remain pending.'],
 ...items.map((i,n)=>['OCE-ITEM-'+String(n+1).padStart(2,'0'),i.name,i.tab+' / '+i.id,'INSPECT definition verified in shared catalog.','Pickup, use, crafting and rewards pending; no grants from browsing.'])
];
for(let i=0;i<additions.length;i++){const r=58+i;mechanics.getRange(`A${r}:E${r}`).copyFrom(mechanics.getRange('A57:E57'),'all');mechanics.getRange(`A${r}:E${r}`).format.rowHeight=90;mechanics.getRange(`A${r}:E${r}`).values=[additions[i]];}
runs.getRange('B5').formulas=[['=COUNTIF(D8:D47,"Verified")']];runs.getRange('E5').formulas=[['=COUNTIF(D8:D47,"Pending")']];
wb.recalculate();
if(runs.getRange('B5').values[0][0]!==34||runs.getRange('E5').values[0][0]!==6)throw Error('Counts do not reconcile');
runs.getRange('D46').values=[['Pending']];wb.recalculate();
if(runs.getRange('B5').values[0][0]!==33||runs.getRange('E5').values[0][0]!==7)throw Error('Count formula does not react');
runs.getRange('D46').values=[['Verified']];wb.recalculate();
for(const[s,r,v,f]of kept){const cells=wb.worksheets.getItem(s).getRange(r);if(norm(cells.values)!==v||JSON.stringify(cells.formulas)!==f)throw Error('Prior rows changed: '+s);}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const[s,r,n]of [['Unreal verification','A44:H47','runs'],['Unreal verification','A2:H5','counts'],['Mechanics','A58:E64','mechanics-1'],['Mechanics','A65:E72','mechanics-2']])await render(s,r,n);
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');
console.log('TRACKER_PASS 34 scoped verification records,6 pending. Prior asset/production/mechanics/test rows preserved.');
