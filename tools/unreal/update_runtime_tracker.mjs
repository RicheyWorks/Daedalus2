import fs from 'node:fs/promises';
import {SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const [repo,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(repo+'/docs/production/Realm-production-2026-10-13.xlsx'));
const assets=wb.worksheets.getItem('Assets'),production=wb.worksheets.getItem('Production'),mechanics=wb.worksheets.getItem('Mechanics');
const before=JSON.stringify(assets.getRange('A6:Q344').values),oldMechanics=JSON.stringify(mechanics.getRange('A1:E40').values);
if(assets.getRange('A6:A344').values.filter(r=>r[0]).length!==339)throw Error('Expected339assetreferences');
const read=async name=>JSON.parse(await fs.readFile(repo+'/docs/production/'+name,'utf8'));
const build=await read('ocean-owned-build-proof.json'),native=await read('ocean-owned-runtime-proof.json');
const rows=[['BUILD','Complete plugin reflection/compile/link','Ocean','Verified',build.seconds,'44 build actions; full process','ocean-owned-build-proof.json','Compilation is not shipped gameplay']];
for(const t of native.tests)rows.push([t.fullTestPath.endsWith('HostEligibility')?'NATIVE':'HERO',t.fullTestPath,'Ocean','Verified',t.duration,'Automation test body; excludes engine startup','ocean-owned-runtime-proof.json','Headless function path, not physical device input']);
for(const [file,id,label]of [['ocean-owned-network-proof.json','BOARD','Remote Hero interaction boards vessel'],['ocean-keyboard-network-proof.json','KEY','Keyboard event propulsion/dive'],['ocean-gamepad-network-proof.json','PAD','Analog event propulsion/dive']]){
 const proof=await read(file);for(const r of proof.passed)rows.push([id+'-'+r.mode,(r.mode==='boat'?label.replace('propulsion/dive','propulsion'):label)+' — '+r.mode,'Ocean','Verified',r.elapsed_seconds,'Server/client startup, handshake and scenario',file,id==='BOARD'?'No physical E/X dispatch or realm transfer':'Engine events; no physical hardware or rendered acceptance']);
}
for(const [id,action,limit]of [['HW','Physical Interact/controller hardware','Requires actual device/viewport run'],['EXIT','Remote exit input and restoration','Local exit tested; remote input not wired'],['REALM','Portal ↔ Ocean / underwater realm transfer','Loader, anchors and persistent session integration'],['ART','Live vessel/dock art and camera composition','Export/model assignment is not live acceptance'],['AUTH','Production login and travel permissions','Test fixtures do not prove real account policy'],['HOST','Public hosting, restart and recovery','Requires deployment and end-to-end verification']])rows.push([id,action,'Ocean','Pending',null,'Not measured',null,limit]);
if(rows.length!==15)throw Error('Unexpected verification run count');
const sheet=wb.worksheets.add('Unreal verification');
sheet.getRange('A2').values=[['Native ocean verification runs']];sheet.getRange('A2').format.font={name:'Arial',size:16,bold:true};
sheet.getRange('A4').values=[['Scoped evidence, not every Unreal action. Seconds cover the stated scope; no mixed-scope total.']];
sheet.getRange('A5').values=[['Verified runs']];sheet.getRange('B5').formulas=[['=COUNTIF(D8:D22,"Verified")']];
sheet.getRange('D5').values=[['Pending checks']];sheet.getRange('E5').formulas=[['=COUNTIF(D8:D22,"Pending")']];
sheet.getRange('A7:H7').values=[['ID','Behavior / run','Realm','State','Seconds','Measured scope','Evidence in docs/production','Limit / remaining work']];
sheet.getRange('A7:H7').format={fill:'#243746',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'}};
sheet.getRange('A8:H22').values=rows;sheet.getRange('A8:H22').format.font={name:'Arial',size:10};
sheet.getRange('A8:H22').format.rowHeight=58;sheet.getRange('B8:H22').format.wrapText=true;
for(const [column,width]of [['A',15],['B',38],['C',14],['D',14],['E',15],['F',35],['G',39],['H',45]])sheet.getRange(column+'1:'+column+'22').format.columnWidth=width;
sheet.getRange('E8:E22').setNumberFormat('0.000');sheet.getRange('D8:D16').format.fill='#E8F5E9';sheet.getRange('D17:D22').format.fill='#FFF2CC';
sheet.getRange('D8:D22').dataValidation={rule:{type:'list',values:['Verified','Pending']}};
mechanics.getRange('A41:E43').values=[
 ['OCE01','Board/exit at configured docks','Native possession, hull and camera checks','Headless native verification; art/remote exit pending','Boats and submarines support journeys from docks'],
 ['OCE02','Owned remote boarding request','Server derives Hero from component owner','Localhost boat/submarine function paths passed','Host session permissions still need integration'],
 ['OCE03','Sea realm travel and shore return','Approved boat/submarine and underwater dock rules','Route core exists; loader/persistence integration pending','Dragon Warrior shores return to land; underwater docks link realms']];
mechanics.getRange('A41:E43').format.font={name:'Arial',size:10};mechanics.getRange('A41:E43').format.rowHeight=58;mechanics.getRange('B41:E43').format.wrapText=true;
wb.recalculate();if(Number(sheet.getRange('B5').values[0][0])!==9||Number(sheet.getRange('E5').values[0][0])!==6)throw Error('Counter failure');
sheet.getRange('D17').values=[['Verified']];wb.recalculate();if(Number(sheet.getRange('B5').values[0][0])!==10)throw Error('Counter dependency failure');
sheet.getRange('D17').values=[['Pending']];wb.recalculate();
if(before!==JSON.stringify(assets.getRange('A6:Q344').values)||oldMechanics!==JSON.stringify(mechanics.getRange('A1:E40').values))throw Error('Prior records changed');
if(Number(production.getRange('B14').values[0][0])!==311464)throw Error('Asset totals changed');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [name,range,suffix]of [['Unreal verification','A1:H16',''],['Unreal verification','A17:H22','-pending'],['Mechanics','A41:E43','-ocean']]){
 const picture=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(out+'/'+name+suffix+'.png',new Uint8Array(await picture.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out+'/Realm-production.xlsx');console.log('RUNTIME_TRACKER_PASS9verifiedruns6pendinggates339assetrecordsunchanged');
