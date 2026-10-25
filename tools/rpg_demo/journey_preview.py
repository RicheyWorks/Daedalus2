# SPDX-License-Identifier: MIT
"""Write focused Prismheart UI diagnostics without running the asset packer.

python tools/rpg_demo/journey_preview.py OUTPUT_DIRECTORY
Then serve that directory on loopback with the existing Python http.server.
Production handlers/painters are copied verbatim. Canonical records seed disposable
scenes; font/window/terrain/sprite/audio/input/storage peers are explicit substitutes.
This does not boot the game, execute battle actions, or establish art, device,
persistence, quest traversal, browser or native runtime acceptance.
"""
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "data" / "rpg"


def load(name):
    return json.loads((DATA / (name + ".json")).read_text(encoding="utf-8"))


def write_preview(destination):
    source = (HERE / "index.html").read_text(encoding="utf-8")

    def between(start, end):
        a = source.index(start)
        return source[a:source.index(end, a + len(start))]

    def line(prefix):
        return next(row for row in source.splitlines() if row.startswith(prefix))

    pins = {}
    for node in ast.parse((HERE / "build_demo.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("QUEST", "OPTIONAL_QUEST", "FINAL"):
                pins[name] = ast.literal_eval(node.value)
    catalog = load("dungeons")["dungeons"]["prism"]
    bosses = load("prism-bosses")["bosses"]
    routes = []
    for landmark, name in pins["QUEST"] + pins["OPTIONAL_QUEST"]:
        original = next(d for d in catalog if d["name"] == name)
        routes.append(dict(name=original["name"], landmark=landmark, theme=original["theme"],
                           floors=original["floors"],
                           final=name == pins["FINAL"], optional=(landmark, name) in pins["OPTIONAL_QUEST"],
                           boss_data=next(b for b in bosses if b["dungeon"] == name)))
    village = load("prism-village")
    interiors = load("interiors")["interiors"]["prism"]
    party = load("party")["party"]["prism"]
    known = {spell for member in party["members"] for spell in member["spells"]}
    # Match build_demo.py's shared stock table: Prism starting armour also uses Portal entries.
    all_interiors = load("interiors")["interiors"]
    gear = {item["name"]: item for realm in ("portal", "prism") for shop in all_interiors[realm].values()
            for item in shop.get("stock", [])
            if item.get("attack") is not None or item.get("defence") is not None or item.get("effect")}
    for fish in load("prism-fish")["fish"]:
        gear[fish["name"]] = {"name": fish["name"], "effect": fish["effect"], "price": fish["price"], "fish": True}
    zones = load("prism-encounters")["zones"]
    formation = next(f["enemies"] for f in zones["plains"]["formations"]
                     if len(f["enemies"]) == 3 and len(set(f["enemies"])) == 1)
    payload = dict(realm_key="prism", dungeons=routes, menus=load("menus")["layouts"]["prism"],
                   world=load("worldmap-tiles")["demo_maps"]["prism"],
                   interiors=interiors, party=party, gear=gear,
                   spells=[s for s in load("spells")["spells"] if s["realm"] == "prism" and (s["name"] in known or s["tier"] <= 2)],
                   title=load("title")["realms"]["prism"], foes={f["key"]: f for f in load("prism-bestiary")["types"]},
                   zones=zones, diagnostic_formation=formation, backdrop_for_zone={"plains": "field"},
                   village={k: village[k] for k in ("name", "landmark")}, waystones=[], rects={"sprites": {}, "tiles": {}, "backdrops": {}, "spells": {}})
    handlers = "\n".join([
        line("const CHARS ="), between("const KEYMAP =", "const keyboardCodes ="),
        line("const hit ="), line("function clearActionButtons()"), line("const find ="),
        line("let journeySerial ="), between("function gauge(", "/* ---------- party ---------- */"),
        between("const START_LEVEL =", "/* ---------- maps"),
        between("const STEP_MIN =", "function dark("),
        line("function airUnlocked()"), between("const carriesShard =", "const chestKey ="),
        between("let menu = null;", "function drawStatus()"),
        between("const STATUS =", "/* ---------- bestiary:"), line("function wrap("),
        between("function startBattle(", "function pop("),
        between("function spellHint(", "/* ---------- title:"),
        line('let SAVE_KEY ='), between("function saveGame()", "function eraseSavedJourney()"),
        between("function titlePrompt(", "function drawTitle("),
        between("let nameEntry = null;", "/* ---------- ending ---------- */")
    ])
    summons = (HERE / "summons.js").read_text(encoding="utf-8")
    page = r"""<!doctype html><meta charset="utf-8"><title>Prismheart UI diagnostic</title>
<style>body{background:#080c20;color:#dae6f2;font:14px monospace;margin:24px}h1{font-size:22px}button,select{font:inherit;margin:4px;padding:6px;background:#16233c;color:#fff;border:1px solid #6884a5}canvas{image-rendering:pixelated;width:960px;max-width:95vw;display:block;margin:16px 0;border:1px solid #6884a5}pre{white-space:pre-wrap;color:#bcd5e9}p{max-width:920px}</style>
<h1>Prismheart UI diagnostic</h1><p><strong>Diagnostic only:</strong> actual production handlers and painters, with canonical records and explicitly seeded recruits, injuries, inventory, story unlocks and battle choices. Font, windows, terrain palette, sprite tokens, silent audio, input/focus adapter, deterministic initiative rolls and memory-only storage are substitutes. This is not the full game, original art, real controller lifecycle, durable storage, quest traversal, browser acceptance or native runtime acceptance.</p>
<button id="formation">Formation / call signs</button><button id="healing">Field MAGIC target</button><button id="pack">Field pack</button><button id="battle">Battle target</button><button id="plan">Battle PLAN</button>
<button id="menu">Open field menu</button><button data-stage="0">No shards</button><button data-stage="1">One shard</button><button data-stage="3">Three shards</button><button data-stage="4">Heart restored</button><button data-stage="5">All routes complete</button>
<label>Location <select id="location"><option>World</option><option>Town</option><option>Castle</option><option>Inn</option><option>Windmere</option><option>Cinder Forge</option><option>Gearwright's Folly</option></select></label>
<label>Canvas width <select id="width"><option>320</option><option>256</option></select></label>
<canvas id="screen" width="320" height="224" tabindex="0" aria-label="Prismheart diagnostic canvas"></canvas>
<div aria-label="Logical input peers"><button data-key="up">Up</button><button data-key="down">Down</button><button data-key="left">Left</button><button data-key="right">Right</button><button data-key="a">A / Confirm</button><button data-key="b">B / Back</button><button data-key="start">Start</button></div>
<p>Keyboard: Up from ITEM selects JOURNEY; Z/Space confirms, X/Esc returns. JOURNEY Left/Right switches notes/world map/current floor (inside a dungeon); Up/Down selects routes and Z pins. Formation: Up/Down chooses, Confirm picks/swaps, Start opens call signs. Naming uses the original typing and canvas-grid pointer handlers. Pack uses Up/Down for items and Left/Right for recipients. Battle uses the original chooser and Back undo; PLAN lists choices rather than initiative. Once initiative is built, this diagnostic stops before executing any actions. Scene buttons reset disposable state; no native browser storage is used.</p>
<p>STATUS, EQUIP, BESTIARY, fishing and shared Settings are excluded and show a diagnostic notice. Location/stage controls remain available; dungeon locations copy only their first floor. The original field-menu geometry is retained, while the featured pages render at 320 or 256 pixels.</p>
<p id="notice" role="status" aria-live="polite"></p><pre id="view" aria-live="polite"></pre><pre id="labels" aria-label="Canvas text output"></pre><pre id="error" role="alert"></pre>
<script>
(function(browserWindow){
'use strict';
const DATA=__DATA__, clone=value=>JSON.parse(JSON.stringify(value)), cv=document.getElementById('screen'),g=cv.getContext('2d');
const window={addEventListener:(...args)=>browserWindow.addEventListener(...args)};
const PrismSummons=(()=>{const module={exports:{}};
__SUMMONS__
return module.exports;})();window.PrismSummons=PrismSummons;
let D=clone(DATA),W=320,H=224,mode='field',map={kind:'world'},P={x:22,y:9},B=null,PAD=null,fade=0,fadeCb=null,dlg=null;
const IM={},opened=new Set(),pressed={},state={beaten:new Set(),ways:new Set(),air:null};
const memory=new Map(),memoryCalls={reads:0,writes:0},localStorage={setItem(key,value){memoryCalls.writes++;memory.set(key,String(value));},getItem(key){memoryCalls.reads++;return memory.has(key)?memory.get(key):null;},removeItem(key){memory.delete(key);}};
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n)),tw=s=>String(s).length*6;
let paints=[],scene='journey',stage=0,diagnosticRolls=0,audioEvents=[];const settingsFramePaused=true;
function rnd(a,b){diagnosticRolls++;return(a+b)/2;} // Explicit deterministic initiative peer; no action rolls are executed.
function text(value,x,y,color='#ffffff'){const s=String(value).toUpperCase();paints.push(s);g.fillStyle=color;g.font='8px monospace';for(let i=0;i<s.length;i++)g.fillText(s[i],x+i*6,y+7);}
function win(x,y,w,h){g.fillStyle='#101a32';g.fillRect(x,y,w,h);g.strokeStyle='#6884a5';g.strokeRect(x+1,y+1,w-2,h-2);}
function cursor(x,y){text('>',x,y,'#ffdf83');}
function spr(sheet,name,x,y,sx,sw,sh,scale=1){const size=112*scale;g.fillStyle=name.startsWith('Party_')?'#487b8e':'#806078';g.fillRect(x,y,size,size);g.strokeStyle='#e0e8e8';g.strokeRect(x,y,size,size);g.fillStyle='#fff';g.font='7px monospace';g.fillText(name.startsWith('Party_')?name.slice(6,9).toUpperCase():'FOE',x+2,y+Math.min(10,size));}
function sfx(event){audioEvents.push(event);audioEvents=audioEvents.slice(-8);}function cue(){}function meet(){} // Silent audio and excluded bestiary tracking peers.
function toast(title,detail=''){document.getElementById('notice').textContent=title+(detail?': '+detail:'');}
function drawField(){g.fillStyle='#080c20';g.fillRect(0,0,W,H);}function openSettings(){toast('Settings excluded','Shared Settings and device modules are outside this diagnostic.');}
function saveSummary(){return'DIAGNOSTIC MEMORY ONLY. '+memoryCalls.writes+' WRITE(S).';}
function gameplayInputBlocked(){return !!(document.activeElement&&document.activeElement.tagName==='SELECT');} // Select-editing peer; visibility/controller lifecycle is excluded.
function beginJourney(){throw Error('New Game/title flow is outside this diagnostic');}
// Register before copied capture handlers: they intentionally stop propagation and have no game frame loop here.
window.addEventListener('keydown',()=>{if(mode==='name')queueMicrotask(safeRender);},true);
cv.addEventListener('pointerdown',()=>{cv.focus();queueMicrotask(safeRender);});
__HANDLERS__
function clearEdges(){Object.keys(pressed).forEach(key=>{pressed[key]=false;});}
function applyStage(){state.beaten=new Set(D.dungeons.slice(0,Math.min(stage,3)).map(d=>d.boss_data.name));if(stage>=4)state.beaten.add(D.dungeons.find(d=>d.final).boss_data.name);if(stage>=5)state.beaten.add(D.dungeons.find(d=>d.optional).boss_data.name);}
function palettePeers(){const atlas=document.createElement('canvas'),p=atlas.getContext('2d'),keys=new Set(D.world.flat().map(tile=>'wm:'+tile));
  D.dungeons.forEach(d=>d.floors.forEach(f=>f.grid.forEach(row=>row.forEach(tile=>keys.add('dg:'+d.theme+':'+tile)))));atlas.width=256;atlas.height=Math.ceil(keys.size/16)*16;D.frames={};
  Array.from(keys).forEach((key,i)=>{const x=(i%16)*16,y=Math.floor(i/16)*16,tile=key.split(':').pop();p.fillStyle=/Void/.test(tile)?'#080c20':/Wall|Rubble|Pillar|Mountain|Cliff/.test(tile)?'#788293':/Water|Sea|Ocean/.test(tile)?'#326486':/Hazard/.test(tile)?'#bc5760':/Chest/.test(tile)?'#d8b365':/Gate/.test(tile)?'#ae78b6':/Stairs/.test(tile)?'#75bdc5':key.startsWith('wm:')?'#568567':'#354a63';p.fillRect(x,y,16,16);p.strokeStyle='#17273c';p.strokeRect(x,y,16,16);D.rects.tiles[key+'#0']=[x,y,16,16];D.frames[key]=1;});IM.tiles=atlas;
  D.party.members.forEach(m=>{D.rects.sprites['Party_'+m.job]=[0,0,112,112];});Object.keys(D.foes).forEach(key=>{D.rects.sprites['Foe_'+key]=[0,0,112,112];});}
function setLocation(name){P={x:1,y:2};map=name==='World'?{kind:'world'}:name==='Town'?{kind:'town'}:name==='Windmere'?{kind:'village'}:['Castle','Inn'].includes(name)?{kind:'interior',name}:null;
  if(!map){const di=D.dungeons.findIndex(d=>d.name===name),d=D.dungeons[di],info=d.floors[0],grid=info.grid.map(row=>row.slice());map={kind:'dungeon',dungeon:di,floor:0,info,grid,key:tile=>'dg:'+d.theme+':'+tile};const entry=find(grid,'StairsUp');if(entry)P={x:entry[0],y:entry[1]};}if(name==='World')P={x:22,y:9};if(menu)menu.jp=0;}
function fieldEntry(command){openMenu();menu.idx=MENU_CMDS.indexOf(command);pressed.a=true;menuTick();}
function chooseCommand(command){const commands=battleCmds(),index=commands.indexOf(command);if(index<0)throw Error('Diagnostic command unavailable: '+command);for(let i=0;B.cmd!==index&&i<commands.length;i++){pressed.down=true;battleTick(0);}pressed.a=true;battleTick(0);}
function resetScene(next,seedStory=false){scene=next;if(seedStory&&(next==='battle'||next==='plan'))stage=3;D=clone(DATA);Object.keys(GEAR).forEach(key=>delete GEAR[key]);party=buildParty();
  Object.assign(state,{beaten:new Set(),ways:new Set(),air:null,seen:{},quests:{},fish:{},returnTo:null,steps:0,sinceBattle:0,day:1,minute:480});opened.clear();clearEdges();menu=null;nameEntry=null;B=null;dlg=null;fade=0;fadeCb=null;journeySerial++;diagnosticRolls=0;audioEvents=[];memory.clear();memoryCalls.reads=0;memoryCalls.writes=0;
  D.dungeons.forEach(d=>recruit(d.name));applyStage();palettePeers();setLocation(document.getElementById('location').value);roster()[0].hp=Math.max(1,roster()[0].max-70);roster()[1].mp=Math.max(0,roster()[1].mmax-12);roster()[4].hp=0;roster()[4].status={poison:true};roster()[5].hp=Math.max(1,roster()[5].max-55);roster()[5].status={poison:true};
  bag={};for(const item of D.interiors.Item.stock||[])if(GEAR[item.name]&&GEAR[item.name].effect)bag[item.name]=2;for(const name of Object.keys(GEAR))if(GEAR[name].fish)bag[name]=2;
  if(next==='formation')fieldEntry('ORDER');else if(next==='healing'){fieldEntry('MAGIC');menu.who=roster().findIndex(m=>m.job==='Lightmender');pressed.a=true;menuTick();pressed.a=true;menuTick();for(let i=0;i<5;i++){pressed.down=true;menuTick();}}
  else if(next==='pack')fieldEntry('ITEM');else if(next==='battle'||next==='plan'){startBattle('plains',null,D.diagnostic_formation.slice());if(fadeCb){const cb=fadeCb;fadeCb=null;cb();}fade=0;pressed.a=true;battleTick(0);
    chooseCommand('ATTACK');if(next==='plan'){pressed.right=true;battleTick(0);pressed.a=true;battleTick(0);chooseCommand('MAGIC');pressed.a=true;battleTick(0);for(let i=0;i<3;i++){pressed.right=true;battleTick(0);}pressed.a=true;battleTick(0);chooseCommand('ITEM');pressed.a=true;battleTick(0);pressed.a=true;battleTick(0);chooseCommand('PLAN');}}
  else openMenu();clearEdges();toast('Disposable '+scene+' scene','Canonical recruits/pack/injuries are explicitly seeded; terrain/sprites/audio/focus/storage are diagnostic peers.');cv.focus();safeRender();}
const excluded=new Set(['EQUIP','STATUS','BESTIARY','FISH','OPTIONS']);
function dispatch(){if(gameplayInputBlocked()){clearEdges();toast('Input paused','Diagnostic focus/visibility peer. Focus the canvas to continue.');safeRender();return;}
  if(mode==='name')nameTick(0);else if(mode==='battle'){if(B.phase==='act'){clearEdges();toast('Initiative queue built','Action execution is excluded. Reset a battle scene to choose again.');}else if(B.phase==='cmd'||B.phase==='intro')battleTick(0);}
  else if(mode==='menu'){if(!menu.sub&&pressed.a&&!pressed.b&&!pressed.start){const commands=MENU_CMDS.concat(['JOURNEY']);let index=menu.idx;if(pressed.up)index=(index+commands.length-1)%commands.length;if(pressed.down)index=(index+1)%commands.length;if(excluded.has(commands[index])){menu.idx=index;clearEdges();toast(commands[index]+' excluded','This diagnostic does not execute that scene or its dependencies.');safeRender();return;}}menuTick();}
  else{if(hit('start'))openMenu();else clearEdges();}if(fadeCb&&mode!=='battle'){const cb=fadeCb;fadeCb=null;cb();fade=0;}safeRender();}
function describe(act){const target=act.target==='all'?'ALL FOES':act.target&&typeof act.target==='object'?{name:act.target.name,foeSlot:B.foes.indexOf(act.target)+1,allySlot:party.indexOf(act.target)+1}:act.kind==='run'||act.kind==='item'&&act.target===null?'ESCAPE ATTEMPT':'SELF';return{actor:act.who.name,kind:act.kind,action:act.spell?act.spell.name:act.spirit?act.spirit.name:act.item||act.kind,target};}
function render(){paints=[];if(mode==='name')drawName();else if(mode==='battle')drawBattle();else if(mode==='menu')drawMenu();else{drawField();text('OPEN FIELD MENU OR CHOOSE A SCENE.',12,20);}
  const view={diagnostic:true,scene,width:W,location:document.getElementById('location').value,stage,mode,sub:mode==='battle'?B.sub:menu&&menu.sub,page:menu&&menu.jp,route:menu&&menu.ii,anchor:journeyAnchor(),
    menu:menu&&{index:menu.idx,who:menu.who,item:menu.ii,target:menu.target,page:menu.jp,pick:menu.pick},roster:roster().map(m=>({name:m.name,job:m.job,front:party.includes(m),hp:m.hp,max:m.max,mp:m.mp,mmax:m.mmax,status:m.status||{}})),bag,gold,
    naming:nameEntry&&{name:nameEntry.name,target:nameEntry.target&&nameEntry.target.job,originalName:nameEntry.originalName},battle:B&&{phase:B.phase,chooser:B.who,command:B.cmd,target:B.target,acts:B.acts.map(describe),queueLength:B.queue?B.queue.length:0,stoppedBeforeActions:B.phase==='act',deterministicInitiativeRolls:diagnosticRolls},
    memorySaves:{reads:memoryCalls.reads,writes:memoryCalls.writes,keys:Array.from(memory.keys())},silentAudioPeer:audioEvents};document.getElementById('view').textContent=JSON.stringify(view,null,2);document.getElementById('labels').textContent=paints.join('\n');}
function safeRender(){try{render();document.getElementById('error').textContent='';}catch(error){document.getElementById('error').textContent=error.stack||error.message;}}
for(const id of ['formation','healing','pack','battle','plan'])document.getElementById(id).onclick=()=>resetScene(id,true);
document.getElementById('menu').onclick=()=>{scene='journey';B=null;nameEntry=null;openMenu();cv.focus();safeRender();};
document.querySelectorAll('[data-key]').forEach(button=>button.onclick=()=>{cv.focus();pressed[button.dataset.key]=true;dispatch();});
document.querySelectorAll('[data-stage]').forEach(button=>button.onclick=()=>{stage=Number(button.dataset.stage);if(scene==='battle'||scene==='plan')resetScene(scene);else{applyStage();cv.focus();safeRender();}});
document.getElementById('location').onchange=event=>{setLocation(event.target.value);safeRender();};
document.getElementById('width').onchange=event=>{W=Number(event.target.value);cv.width=W;safeRender();};
window.addEventListener('keydown',event=>{if(event.target.tagName==='SELECT'||event.ctrlKey||event.metaKey||event.altKey||event.repeat)return;const key=KEYMAP[event.code];if(!key)return;event.preventDefault();pressed[key]=true;dispatch();});
window.addEventListener('error',event=>document.getElementById('error').textContent=event.message);
resetScene('journey');
})(window);
</script>"""
    page = page.replace("__DATA__", json.dumps(payload).replace("</", "<\\/")).replace("__HANDLERS__", handlers).replace("__SUMMONS__", summons)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "index.html"
    target.write_text(page, encoding="utf-8")
    print(target.resolve())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: journey_preview.py OUTPUT_DIRECTORY")
    write_preview(sys.argv[1])
