// SPDX-License-Identifier: MIT
// Bounded actual-function/canonical-catalog checks; no assets, browser, build, native runtime or game loop.
"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const build = fs.readFileSync(path.join(__dirname, "build_demo.py"), "utf8");
const data = name => JSON.parse(fs.readFileSync(path.join(__dirname, "../../data/rpg", name + ".json"), "utf8"));
const clone = x => JSON.parse(JSON.stringify(x));
const tuples = name => JSON.parse(build.match(new RegExp("^" + name + " = (\\[.*\\])", "m"))[1].replace(/\(/g, "[").replace(/\)/g, "]"));
const original = tuples("QUEST"), optional = tuples("OPTIONAL_QUEST"), raw = data("dungeons"), bosses = data("prism-bosses").bosses;
const dungeons = original.concat(optional).map(([landmark, name], i) => ({ ...clone(raw.dungeons.prism.find(d => d.name === name)),
  landmark, final: i === 3, optional: i >= original.length, boss_data: clone(bosses.find(b => b.dungeon === name)), boss_backdrop: "ruins" }));
const partyData = data("party").party.prism, interiors = data("interiors"), worldData = data("worldmap-tiles"), townData = data("town-tiles");
const gear = {};
for (const realm of ["portal", "prism"]) for (const shop of Object.values(interiors.interiors[realm]))
  for (const item of shop.stock || []) if (item.attack != null || item.defence != null || item.effect) gear[item.name] = item;
function between(start, end) { const a = html.indexOf(start), b = html.indexOf(end, a + start.length); assert.ok(a >= 0 && b > a, start); return html.slice(a, b); }
function line(prefix) { const s = html.split(/\r?\n/).find(x => x.startsWith(prefix)); assert.ok(s, prefix); return s; }
const source = [line("const CHARS ="), line("const hit ="), line("function clearActionButtons()"),
  between("const START_LEVEL =", "/* ---------- maps"), line("let mode ="), line("const opened ="), line("let journeySerial ="),
  between("const AIR_SPEED =", "/* The shard quest:"), between("let grids =", "/* ---------- waystones"),
  between("function townMap()", "/* ---------- dialog"), between("let dlg = null;", "function wrap("), line("function wrap("),
  between("const LINES =", "function innPrompt("), between("function openChest(", "/* ---------- shops"),
  between("function villageRequest(", "function castLine("),
  between("function enterDungeon(", "function fieldTick("), between("let menu = null;", "function drawStatus("),
  between("const STATUS =", "/* ---------- bestiary"), between("const BEHAVIOUR_TEXT =", "function drawBestiary("),
  between("let B = null;", "function playChord("), between("function nextChooser(", "function spellHint("),
  between("function titlePrompt(", "function drawTitle("),
  "this.api = { begin: () => { party = buildParty(); map = worldMap(); mode = 'field'; }, interact, enterDungeon, stepDone, dungeonMap, worldMap, townMap, interiorMap, " +
  "boardAirship, airship, flying, openChest, shardBosses, shardCount, chestKey, follyDungeon, follyCleared, " +
  "recruit, roster, canEquip, openMenu, menuTick, drawMenu, rowH, rowY, beastInfo, startBattle, doAction, hurtFoe, endRound, finishBattle, bossGate, " +
  "party: () => party, reserve: () => reserve, bag: () => bag, gold: () => gold, battle: () => B, dialog: () => dlg, menu: () => menu, " +
  "setMap: m => { map = m; }, map: () => map, mode: () => mode, setParty: r => { party = r.slice(0,4); reserve = r.slice(4); }, clearDialog: () => { dlg = null; }, " +
  "fade: () => { if (fadeCb) { const cb = fadeCb; fadeCb = null; cb(); } fade = 0; }, keys: () => Object.keys(CHARS) }; this.state=state; this.opened=opened;"
].join("\n");
let checks = 0;
function check(label, fn) { try { fn(); checks++; } catch (e) { e.message = label + ": " + e.message; throw e; } }
function session(production = source) {
  const draws = [], sounds = [], notices = [], c = { D: { realm_key: "prism", party: clone(partyData), gear: clone(gear), dungeons: clone(dungeons),
      dungeon_walkable: raw.walkable, dungeon_interact: raw.interact, world: clone(worldData.demo_maps.prism),
      world_tiles: Object.fromEntries(worldData.tiles.filter(t => t.realm === "prism").map(t => [t.tile,t])),
      town: clone(townData.demo_towns.prism), town_tiles: Object.fromEntries(townData.tiles.filter(t => t.realm === "prism").map(t => [t.tile,t])),
      interiors: clone(interiors.interiors.prism), interior_tiles: Object.fromEntries(interiors.tiles.filter(t => t.realm === "prism").map(t => [t.tile,t])),
      village: clone(data("prism-village")), frames: {}, menus: clone(data("menus").layouts.prism), zones: {}, sky_caches: [],
      backdrop_for_zone: { ruins: "ruins", sewer: "sewer" }, foes: {}, spells: clone(data("spells").spells.filter(s => s.realm === "prism")) },
    T: 16, W: 320, H: 224, PAD: null, window: {}, pressed: {}, held: {}, now: 0,
    performance: { now: () => c.now }, sfx: x => sounds.push(x), cue() {}, toast: (...x) => notices.push(x),
    fieldPoison() {}, passTime() {}, isNight: () => false, clockText: () => "D1 08:00", waystoneStep: () => false,
    STEP_MIN: { world:4, dungeon:1, town:2 }, clamp: (n,a,b) => Math.max(a,Math.min(b,n)), rnd: (a,b) => (a+b)/2, ri: a => a,
    drawField() {}, gauge() {}, spr: (...args) => draws.push({ kind:"sprite", args }), tw: x => String(x).length*6,
    win: (x,y,w,h) => draws.push({ kind:"window",x,y,w,h }), text: (value,x,y) => draws.push({ kind:"text",value:String(value).toUpperCase(),x,y }),
    cursor: (x,y) => draws.push({kind:"cursor",x,y}), g: { fillRect() {} },
    saveGame() { throw new Error("field progression must not save implicitly"); }, workshopPrompt() {}, playChord() {} };
  vm.createContext(c); vm.runInContext(production, c, { timeout:1000 }); c.api.begin();
  return { c, api:c.api, draws, sounds, notices, tap(...keys) { keys.forEach(k => c.pressed[k] = true); c.api.menuTick(); },
    place(m,x,y,dir="up") { c.api.setMap(m); vm.runInContext("P.x="+x+";P.y="+y+";P.dir="+JSON.stringify(dir),c); } };
}
const allShards = s => s.api.shardBosses().forEach(n => s.c.state.beaten.add(n));
function enter(s, di=4) { s.api.enterDungeon(di); const dlg = s.api.dialog(); if (dlg && dlg.then) { s.api.clearDialog(); dlg.then(); } s.api.fade(); }
function earn(s) { for (const d of dungeons.slice(0,3)) { s.c.state.beaten.add(d.boss_data.name); s.api.recruit(d.name); } return s; }
check("original four indices/chest keys remain; Folly has three canonical floors and no shard", () => {
  const s=session(); assert.deepEqual(original.map(x=>x[1]), ["Cinder Forge","Windcut Aerie","Sunwell Sanctum","The Shattered Heart"]);
  assert.equal(dungeons.length,5); assert.equal(dungeons[4].floors.length,3); assert.equal(dungeons[4].boss_data.shard,"-");
  assert.equal(s.api.chestKey(0,0,1,2),"dungeon0/0:1,2"); assert.equal(s.api.chestKey(3,1,2,3),"dungeon3/1:2,3");
  assert.equal(s.api.shardBosses().length,3); assert.equal(s.api.shardCount(),0);
});
check("Folly and final shrine require the same existing three shards", () => {
  for (let n=0;n<=3;n++) for (const di of [3,4]) { const s=session(); s.api.shardBosses().slice(0,n).forEach(k=>s.c.state.beaten.add(k));
    s.api.enterDungeon(di); if(n<3) { assert.equal(s.api.map().kind,"world"); assert.match(s.api.dialog().pages.join(" "),/SEALED|SEAL HOLDS/); }
    else { const dlg=s.api.dialog(); if(dlg&&dlg.then){s.api.clearDialog();dlg.then();} s.api.fade(); assert.equal(s.api.map().dungeon,di); }
  }
});
check("all original routes still enter their original indices", () => {
  for(let di=0;di<4;di++){const s=session();allShards(s);const p=s.c.D.world.flatMap((r,y)=>r.map((t,x)=>t===dungeons[di].landmark?[x,y]:null).filter(Boolean))[0];
    s.place(s.api.worldMap(),p[0],p[1]);s.api.stepDone();s.api.fade();assert.equal(s.api.map().dungeon,di);}
});
check("adjacent grounded Confirm enters Folly while same-tile and walk-on retain skiff priority", () => {
  const s=session();allShards(s); const pad=s.c.D.world.flatMap((r,y)=>r.map((t,x)=>t==="AirshipPad"?[x,y]:null).filter(Boolean))[0];
  s.place(s.api.worldMap(),pad[0],pad[1]+1);s.api.interact();assert.match(s.api.dialog().pages[0],/GEARWRIGHT'S FOLLY/);
  assert.equal(s.api.airship().aboard,false);s.api.clearDialog();s.place(s.api.worldMap(),pad[0],pad[1]);s.api.interact();assert.equal(s.api.airship().aboard,true);
  s.api.airship().aboard=false;s.api.clearDialog();s.api.stepDone();assert.equal(s.api.airship().aboard,true);assert.equal(s.api.map().kind,"world");
});
check("cache reward/dialog precedes walk-on boarding; facing elsewhere does not enter Folly", () => {
  const s=session();allShards(s);const a=s.api.airship();s.c.D.sky_caches=[{x:a.x,y:a.y,item:"Scale Coat"}];s.place(s.api.worldMap(),a.x,a.y);
  s.api.stepDone();assert.equal(a.aboard,false);assert.equal(s.api.bag()["Scale Coat"],1);assert.match(s.api.dialog().pages.join(" "),/FOUND SCALE COAT/);
  s.api.clearDialog();s.place(s.api.worldMap(),a.x,a.y+1,"down");s.api.interact();assert.equal(s.api.dialog(),null);
});
check("three floors have real forward/back stairs and unchanged boss gate", () => {
  const s=session();allShards(s);enter(s);assert.equal(s.api.map().floor,0);
  for(let i=0;i<3;i++){
    const floor=dungeons[4].floors[i],m=s.api.dungeonMap(4,i),q=[[floor.stairs_up.x,floor.stairs_up.y]],seen=new Set([q[0].join(",")]);
    for(let at=0;at<q.length;at++)for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){
      const x=q[at][0]+dx,y=q[at][1]+dy,key=x+","+y;if(seen.has(key)||!m.grid[y]||!m.walk(m.grid[y][x]))continue;seen.add(key);q.push([x,y]);
    }
    if(i<2)assert.ok(seen.has(floor.stairs_down.x+","+floor.stairs_down.y),"actual walkable floor reaches its down stairs");
    else assert.ok([[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>seen.has((floor.boss.gate.x+dx)+","+(floor.boss.gate.y+dy))),"actual walkable final floor reaches a facing position at BossGate");
  }
  for(let i=0;i<2;i++){const f=dungeons[4].floors[i];s.place(s.api.map(),f.stairs_down.x,f.stairs_down.y);s.api.stepDone();s.api.fade();assert.equal(s.api.map().floor,i+1);}
  const last=dungeons[4].floors[2];assert.ok(last.boss);assert.equal(s.api.map().grid[last.boss.gate.y][last.boss.gate.x],"BossGate");
  for(let i=2;i>0;i--){const f=dungeons[4].floors[i];s.place(s.api.map(),f.stairs_up.x,f.stairs_up.y);s.api.stepDone();s.api.fade();assert.equal(s.api.map().floor,i-1);}
});
check("Colossus retains canonical stats, Tide weakness, sleep and retreat refusals", () => {
  const s=earn(session());s.api.openMenu();s.api.menu().sub="order";s.api.menu().pick=-1;s.api.menu().ii=s.api.roster().findIndex(m=>m.job==="Chronoseer");
  s.tap("a");s.api.menu().ii=0;s.tap("a");s.tap("b");s.tap("b");enter(s);const b=s.c.D.dungeons[4].boss_data;s.api.startBattle("sewer",b);s.api.fade();const f=s.api.battle().foes[0];
  assert.equal(f.hp,b.hp);assert.equal(f.atk,b.attack);assert.equal(f.def,b.defence);assert.equal(f.weak,"water");
  s.api.doAction({kind:"run",who:s.api.party()[0]});assert.match(s.api.battle().msg,/COLOSSUS BLOCKS YOUR RETREAT/);
  const drowse=s.c.D.spells.find(x=>x.status==="sleep"&&!x.power);assert.ok(drowse);const caster=s.api.party().find(m=>m.spells.includes(drowse.name));assert.ok(caster&&caster.mp>=drowse.mp);
  s.api.doAction({kind:"magic",who:caster,spell:drowse,target:f});assert.ok(!f.status||!f.status.sleep);assert.match(s.api.battle().msg,/COLOSSUS DOES NOT SLEEP/);
  assert.equal(s.api.beastInfo("warden:"+b.name).beh,"boss");
});
check("actual Colossus victory grants ordinary rewards/recruit and no shard or ending", () => {
  const s=earn(session());enter(s);const fl=s.c.D.dungeons[4].floors[2];s.api.setMap(s.api.dungeonMap(4,2));const b=s.c.D.dungeons[4].boss_data;
  const gold=s.api.gold();s.api.startBattle("sewer",b);s.api.fade();const f=s.api.battle().foes[0];s.api.hurtFoe(f,f.hp);s.api.endRound();
  assert.equal(s.api.gold()-gold,b.level*80);assert.match(s.api.battle().msg,new RegExp(b.level*150+" EXP"));
  assert.equal(s.api.roster().length,8);const brannoc=s.api.reserve().find(m=>m.job==="Gearwright");assert.ok(brannoc);assert.ok(s.api.canEquip(brannoc,"Iron Axe"));
  assert.ok(!s.api.battle().endLines.some(x=>/SHARD OF -|SUMMON NOW/.test(x)));let i=0;while(s.api.battle().endLines.length&&i++<100)s.api.finishBattle();s.api.finishBattle();s.api.fade();
  assert.equal(s.api.shardCount(),3);assert.ok(s.c.state.beaten.has(b.name));assert.equal(s.api.mode(),"field");assert.equal(s.api.map().grid[fl.boss.gate.y][fl.boss.gate.x],"Floor");
  assert.match(s.api.dialog().pages.join(" "),/NO SHARD.*CALIBRATION BENCH/);assert.ok(s.api.interiorMap("Inn").npcs.some(n=>n.type==="Brannoc"&&n.fieldSprite==="NPC_Merchant"));
  s.api.recruit(dungeons[4].name);assert.equal(s.api.roster().length,8);
});
check("eight-member ORDER moves Brannoc into battle with equipment unchanged", () => {
  const s=earn(session());s.api.recruit(dungeons[4].name);const brannoc=s.api.roster()[7],equip=JSON.stringify(brannoc.equip);
  s.api.openMenu();s.api.menu().sub="order";s.api.menu().pick=-1;s.api.menu().ii=7;s.tap("a");s.api.menu().ii=0;s.tap("a");
  assert.equal(s.api.party()[0],brannoc);assert.equal(JSON.stringify(brannoc.equip),equip);assert.equal(s.api.reserve().length,4);
});
check("actual ORDER paint keeps all seven/eight rows and selected cursor clear of feedback", () => {
  for(const n of [7,8]){const s=earn(session());if(n===8)s.api.recruit(dungeons[4].name);s.api.openMenu();const menu=s.api.menu();menu.sub="order";menu.ii=n-1;menu.pick=-1;menu.msg="CHOOSE TWO TO SWAP.";
    s.api.drawMenu();assert.equal(s.api.rowH(),22);const panel=s.draws.findLastIndex(d=>d.kind==="window"&&d.y===190);assert.ok(panel>=0);
    for(let i=0;i<n;i++){const m=s.api.roster()[i],y=s.api.rowY(i);for(const [value,dy] of [[m.name.toUpperCase(),2],[m.hp+"/"+m.max,14]]){
      const at=s.draws.findIndex(d=>d.kind==="text"&&d.value===value&&d.y===y+dy&&d.x===40);assert.ok(at>=0&&at<panel);assert.ok(y+dy+8<190);}
    }const cursor=s.draws.find(d=>d.kind==="cursor"&&d.y===s.api.rowY(n-1)+2);assert.ok(cursor&&cursor.y+8<190);
  }
  const s=session();assert.equal(s.api.rowH(),52);s.api.recruit(dungeons[0].name);assert.equal(s.api.rowH(),30);s.api.recruit(dungeons[1].name);assert.equal(s.api.rowH(),30);
});
check("Elder supplies physical Confirm guidance without changing shard directions", () => {
  const s=session(),m=s.api.townMap(),elder=m.npcs.find(n=>n.type==="Elder");assert.ok(elder);s.place(m,elder.x,elder.y+1);s.api.interact();
  const pages=s.api.dialog().pages;assert.match(pages.slice(0,2).join(" "),/CINDER FORGE.*WINDCUT AERIE.*SUNWELL SANCTUM/);assert.match(pages.join(" "),/PRESS Z\/SPACE OR TAP A TO EXAMINE/);
  for(const p of pages)assert.ok(p.split(" ").every(w=>w.length<=48)&&p.length<192);
  assert.ok(s.c.opened.has("story/folly/discovered"));
});
check("Portal bossless projection has no Folly, extra shard, NPC or Elder branch", () => {
  const s=session();s.c.D.dungeons=[{name:"Portal road",boss_data:null,final:false}];assert.equal(s.api.shardCount(),0);assert.equal(s.api.follyDungeon(),undefined);
  assert.ok(!s.api.interiorMap("Inn").npcs.some(n=>n.type==="Brannoc"));
});
check("Folly discovery preserves Windmere Elder's authored once-only fish request", () => {
  const s=session(),v=s.c.D.village,elder=v.npcs.find(n=>n.type==="Elder");assert.ok(elder&&elder.request);const m={kind:"village",npcs:clone(v.npcs),grid:clone(v.grid)};
  s.place(m,elder.x,elder.y+1);s.api.bag()[elder.request.item]=1;const gold=s.api.gold();s.api.interact();
  const dlg=s.api.dialog();assert.ok(dlg.choice);dlg.choice.then(0);assert.equal(s.api.gold()-gold,600);assert.equal(s.api.bag()[elder.request.item],0);
  s.api.clearDialog();s.api.interact();assert.equal(s.api.gold()-gold,600);assert.ok(!s.c.opened.has("story/folly/discovered"));
});
const inline=html.match(/<script>\s*([\s\S]*?)<\/script>/);assert.ok(inline);new vm.Script(inline[1],{filename:"index.html:inline"});
console.log("Prismheart Folly progress checks: "+checks+" passed; full inline script compiles.");
