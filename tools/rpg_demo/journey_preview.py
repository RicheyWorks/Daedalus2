# SPDX-License-Identifier: MIT
"""Write a focused JOURNEY browser diagnostic without running the asset packer.

python tools/rpg_demo/journey_preview.py OUTPUT_DIRECTORY
Then serve that directory on loopback with the existing Python http.server.
Production handlers/painters are copied verbatim; font/window/terrain substitutes,
an empty roster and scenario controls are explicit diagnostic peers, not game art,
full game boot, persistence, controller lifecycle or ordinary gameplay acceptance.
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
        routes.append(dict(name=original["name"], landmark=landmark,
                           final=name == pins["FINAL"], optional=(landmark, name) in pins["OPTIONAL_QUEST"],
                           boss_data=next(b for b in bosses if b["dungeon"] == name)))
    village = load("prism-village")
    payload = dict(realm_key="prism", dungeons=routes, menus=load("menus")["layouts"]["prism"],
                   world=load("worldmap-tiles")["demo_maps"]["prism"],
                   interiors={k: {"opened_by": v.get("opened_by", {})} for k, v in load("interiors")["interiors"]["prism"].items()},
                   village={k: village[k] for k in ("name", "landmark")}, waystones=[], rects={"sprites": {}, "tiles": {}})
    handlers = "\n".join([
        line("const CHARS ="), between("const KEYMAP =", "const keyboardCodes ="),
        line("const hit ="), line("function clearActionButtons()"), line("const find ="),
        line("function airUnlocked()"), between("const carriesShard =", "const chestKey ="),
        between("let menu = null;", "function drawStatus()"),
        between("function titlePrompt(", "function drawTitle(")
    ])
    page = r"""<!doctype html><meta charset="utf-8"><title>Prismheart JOURNEY diagnostic</title>
<style>body{background:#080c20;color:#dae6f2;font:14px monospace;margin:24px}h1{font-size:22px}button,select{font:inherit;margin:4px;padding:6px;background:#16233c;color:#fff;border:1px solid #6884a5}canvas{image-rendering:pixelated;width:960px;max-width:95vw;display:block;margin:16px 0;border:1px solid #6884a5}pre{white-space:pre-wrap;color:#bcd5e9}p{max-width:920px}</style>
<h1>Prismheart JOURNEY diagnostic</h1><p>Actual production notebook/menu handlers and painters, canonical route metadata. Diagnostic font, windows and blank terrain replace missing art. Only JOURNEY is under test; this is not a complete game build or runtime acceptance.</p>
<button id="menu">Open field menu</button><button data-stage="0">No shards</button><button data-stage="1">One shard</button><button data-stage="3">Three shards</button><button data-stage="4">Heart restored</button><button data-stage="5">All routes complete</button>
<label>Location <select id="location"><option>World</option><option>Town</option><option>Castle</option><option>Inn</option><option>Windmere</option><option>Cinder Forge</option><option>Gearwright's Folly</option></select></label>
<label>Canvas width <select id="width"><option>320</option><option>256</option></select></label>
<canvas id="screen" width="320" height="224" tabindex="0" aria-label="JOURNEY diagnostic canvas"></canvas>
<p>Keyboard: Up from ITEM selects JOURNEY; Z confirms. Left/Right switches notes/map. Up/Down selects a route. X/Esc returns. Click a scenario to change only this disposable diagnostic state.</p>
<p id="notice" role="status" aria-live="polite"></p><pre id="view" aria-live="polite"></pre><pre id="labels" aria-label="Canvas text output"></pre><pre id="error" role="alert"></pre>
<script>
const D = __DATA__, cv = document.getElementById('screen'), g = cv.getContext('2d');
let W=320,H=224,mode='field',map={kind:'world'},P={x:22,y:9},B=null,PAD=null,bag={},gold=0;
const GEAR={},ACTIVE=4,roster=()=>[],IM={},opened=new Set(),pressed={},state={beaten:new Set(),ways:new Set(),air:null};
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n)),tw=s=>String(s).length*6;
let paints=[];
function text(value,x,y,color='#ffffff'){const s=String(value).toUpperCase();paints.push(s);g.fillStyle=color;g.font='8px monospace';for(let i=0;i<s.length;i++)g.fillText(s[i],x+i*6,y+7);}
function win(x,y,w,h){g.fillStyle='#101a32';g.fillRect(x,y,w,h);g.strokeStyle='#6884a5';g.strokeRect(x+1,y+1,w-2,h-2);}
function cursor(x,y){text('>',x,y,'#ffdf83');}function spr(){}function gauge(){}function tags(){return [];}
function sfx(){}function clockText(){return'D1 08:00';}function isNight(){return false;}
function toast(title,detail){document.getElementById('notice').textContent=title+': '+detail;}
function drawField(){g.fillStyle='#080c20';g.fillRect(0,0,W,H);}function openSettings(){throw Error('Settings is outside this diagnostic');}
function saveGame(){throw Error('Saving is outside this diagnostic');}
__HANDLERS__
function render(){paints=[];if(mode==='menu')drawMenu();else{drawField();text('PRESS OPEN FIELD MENU TO RETURN.',12,20);}const anchor=journeyAnchor();document.getElementById('view').textContent=JSON.stringify({mode,sub:menu&&menu.sub,page:menu&&menu.jp,route:menu&&menu.ii,anchor},null,2);document.getElementById('labels').textContent=paints.join('\n');}
document.getElementById('menu').onclick=()=>{openMenu();render();};
document.querySelectorAll('[data-stage]').forEach(button=>button.onclick=()=>{const stage=Number(button.dataset.stage);state.beaten=new Set(D.dungeons.slice(0,Math.min(stage,3)).map(d=>d.boss_data.name));if(stage>=4)state.beaten.add(D.dungeons.find(d=>d.final).boss_data.name);if(stage>=5)state.beaten.add(D.dungeons.find(d=>d.optional).boss_data.name);render();});
document.getElementById('location').onchange=event=>{const name=event.target.value;P={x:1,y:2};map=name==='World'?{kind:'world'}:name==='Town'?{kind:'town'}:name==='Windmere'?{kind:'village'}:['Castle','Inn'].includes(name)?{kind:'interior',name}:{kind:'dungeon',dungeon:D.dungeons.findIndex(d=>d.name===name)};if(name==='World')P={x:22,y:9};render();};
document.getElementById('width').onchange=event=>{W=Number(event.target.value);cv.width=W;render();};
window.addEventListener('keydown',event=>{if(event.target.tagName==='SELECT'||event.repeat)return;const key=KEYMAP[event.code];if(!key)return;event.preventDefault();pressed[key]=true;if(mode==='menu')menuTick();render();});
window.addEventListener('error',event=>document.getElementById('error').textContent=event.message);
openMenu();render();
</script>"""
    page = page.replace("__DATA__", json.dumps(payload).replace("</", "<\\/")).replace("__HANDLERS__", handlers)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "index.html"
    target.write_text(page, encoding="utf-8")
    print(target.resolve())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: journey_preview.py OUTPUT_DIRECTORY")
    write_preview(sys.argv[1])
