// SPDX-License-Identifier: MIT
/*
 * DaedalusSettings: the settings every Daedalus web client shares, laid out like a modern console game
 * (Controller, Keyboard/Mouse, Video, Audio, Gameplay, Accessibility), from one schema.
 *
 *   <script src="/settings/daedalus-settings.js"></script>          (or: import "/settings/daedalus-settings.js")
 *   const settings = DaedalusSettings.create({ schema: "/settings/settings-schema.json" });
 *   settings.get("MusicVolume"); settings.on("MusicVolume", v => ...); settings.on("*", (id, v) => ...);
 *   const panel = DaedalusSettings.mountPanel({ settings, pad });   panel.open(); panel.close();
 *
 * The schema (data/settings/settings-schema.json) is built from the Unreal client's own settings code by
 * tools/settings/build_schema.py, so ids, ranges, defaults and choices are the native ones. Values are saved in the
 * native format, a flat {"Id": number} object (localStorage "daedalus.settings"); export() / import() move a
 * Saved/Config/DaedalusSettings.json between Unreal and the browser unchanged.
 *
 * The panel is a modern console game's: a tab ribbon switched with LB / RB (or Q / E), sections of rows, the selected row's
 * description on the side, and button hints. Up / down picks a row, left / right adjusts it, A changes a toggle or
 * choice, Y resets the tab, B closes. It works with any pad DaedalusPad knows, a keyboard, a mouse, or touch (rows
 * and slider handles are at least 44 px tall; drag a slider or tap its - / + buttons).
 */
(function (root) {
  "use strict";
  const STYLE_ID = "daedalus-settings-style";

  function create(opt) {
    opt = Object.assign({ storageKey: "daedalus.settings", schema: null }, opt || {});
    let schema = null, rows = [], byId = {};
    let values = {};
    try { values = JSON.parse(root.localStorage.getItem(opt.storageKey) || "{}") || {}; } catch (e) { values = {}; }
    const subs = {}, actions = {};
    const readyCbs = [], pending = [];                   /* app-local rows waiting for the schema */
    const clamp = (r, v) => {
      v = Number(v); if (!isFinite(v)) v = r.default;
      if (r.kind === "slider") { v = Math.min(r.max, Math.max(r.min, v)); return Math.round(v / r.step) * r.step; }
      if (r.kind === "toggle") return v > 0.5 ? 1 : 0;
      return Math.min(r.choices.length - 1, Math.max(0, Math.round(v)));
    };
    const save = () => { try { root.localStorage.setItem(opt.storageKey, JSON.stringify(values)); } catch (e) {} };
    const fire = (id, v) => {
      for (const f of subs[id] || []) try { f(v, id); } catch (e) { if (root.console) console.error(e); }
      for (const f of subs["*"] || []) try { f(id, v); } catch (e) { if (root.console) console.error(e); }
    };
    function take(s) {
      schema = JSON.parse(JSON.stringify(s)); rows = schema.rows; byId = {};
      for (const r of rows) byId[r.id] = r;
      pending.splice(0).forEach(addLocal);
      for (const r of rows) fire(r.id, api.get(r.id));
      readyCbs.splice(0).forEach(f => f(api));
    }
    /* App-local rows: an app adds its own rows (actions, live info, its own toggles) into a tab and section of the shared
       layout. They are marked local, kept out of export() (Unreal never sees them) and need no schema change. */
    function addLocal(spec) {
      const t = schema.tabs.find(x => x.id === spec.tab);
      if (!t) return;
      if (!t.sections.includes(spec.section)) { if (spec.first) t.sections.unshift(spec.section); else t.sections.push(spec.section); }
      const made = spec.rows.map(r => Object.assign({ min: 0, max: 1, step: 1, unit: "", choices: [], default: 0, help: "" }, r,
        { tab: spec.tab, section: spec.section, local: true, native: false, consumers: ["app"] }));
      made.forEach(r => { byId[r.id] = r; });
      const order = id => { const r = byId[id]; return t.sections.indexOf(r.section); };
      const rest = rows.filter(r => !made.includes(r));
      rows = rest.concat(made);
      const tabOrder = schema.tabs.map(x => x.id);
      rows.sort((a, b) => (tabOrder.indexOf(a.tab) - tabOrder.indexOf(b.tab)) || (a.tab === b.tab ? order(a.id) - order(b.id) : 0));
      schema.rows = rows;
      made.forEach(r => { if (r.kind !== "action" && r.kind !== "info") fire(r.id, api.get(r.id)); });
    }
    const api = {
      extend: spec => { if (schema) addLocal(spec); else pending.push(spec); return api; },
      onAction: (id, f) => { actions[id] = f; return api; },
      ready: f => { if (schema) f(api); else readyCbs.push(f); },
      loaded: () => !!schema,
      schema: () => schema,
      row: id => byId[id] || null,
      tabs: () => schema ? schema.tabs.map(t => t.id) : [],
      sections: tab => { const t = schema && schema.tabs.find(x => x.id === tab); return t ? t.sections.slice() : []; },
      rows: (tab, section) => rows.filter(r => (!tab || r.tab === tab) && (!section || r.section === section)),
      get: id => { const r = byId[id]; if (!r) return values[id]; return id in values ? clamp(r, values[id]) : r.default; },
      choice: id => { const r = byId[id]; return r && r.kind === "choice" ? r.choices[api.get(id)] : null; },
      set: (id, v) => {
        const r = byId[id]; if (!r) return false;
        const nv = clamp(r, v);
        if (api.get(id) === nv && id in values) return false;
        values[id] = nv; save(); fire(id, nv); return true;
      },
      nudge: (id, dir) => {
        const r = byId[id]; if (!r || r.kind === "action" || r.kind === "info") return false;
        const v = api.get(id);
        if (r.kind === "toggle") return api.set(id, v ? 0 : 1);
        if (r.kind === "choice") return api.set(id, (v + dir + r.choices.length) % r.choices.length);
        return api.set(id, v + dir * r.step);
      },
      activate: id => {
        const r = byId[id]; if (!r) return false;
        if (r.kind === "action") { if (actions[id]) actions[id](); return true; }
        if (r.kind === "info") return false;
        return r.kind !== "slider" ? api.nudge(id, 1) : false;
      },
      format: id => {
        const r = byId[id]; if (!r) return "";
        if (r.kind === "info") return typeof r.value === "function" ? String(r.value()) : (r.value || "");
        if (r.kind === "action") return r.button || "START";
        const v = api.get(id);
        if (r.kind === "toggle") return v ? "ON" : "OFF";
        if (r.kind === "choice") return r.choices[v] || "?";
        const whole = r.step >= 1 && Math.abs(r.step - Math.round(r.step)) < 1e-6;
        return (whole ? String(Math.round(v)) : v.toFixed(1)) + (r.unit || "");
      },
      fraction: id => { const r = byId[id]; return r && r.max > r.min ? (api.get(id) - r.min) / (r.max - r.min) : 0; },
      resetTab: tab => { for (const r of rows) if (r.tab === tab && r.kind !== "action" && r.kind !== "info") { delete values[r.id]; fire(r.id, r.default); } save(); },
      on: (id, f) => { (subs[id] = subs[id] || []).push(f); if (schema && id !== "*") f(api.get(id), id); return () => { subs[id] = subs[id].filter(x => x !== f); }; },
      export: () => { const o = {}; for (const r of rows) if (!r.local) o[r.id] = api.get(r.id); return o; },
      import: obj => { let n = 0; for (const k in obj || {}) if (byId[k] && api.set(k, obj[k])) n++; return n; },
      layout: () => schema && schema.layouts,
    };
    if (opt.schema && typeof opt.schema === "object") take(opt.schema);
    else if (opt.schema && root.fetch) fetch(opt.schema).then(r => r.ok ? r.json() : null).then(j => j && take(j)).catch(() => {});
    return api;
  }

  /* ------------------------------------------------------------------------------------------- the panel
     a modern console game's settings screen: SETTINGS title, a tab ribbon between LB and RB glyphs with a sliding
     indicator, sections of rows (\u2039 VALUE \u203a selectors and sliders), a description pane on the right with the
     current and default value and, for the layout rows, a live controller diagram, and button hints along the
     bottom that use the connected pad's own button names (A / Cross / B ...). The DOM is built once per tab and
     updated in place, so a slider keeps its grip while it is dragged. */
  const CSS = `
.dset{position:fixed;inset:0;z-index:2147483000;display:none;font-family:"Segoe UI",system-ui,-apple-system,sans-serif;color:#eef3f8;
  background:linear-gradient(180deg,rgba(4,10,18,.96) 0%,rgba(6,14,26,.97) 40%,rgba(2,5,10,.99) 100%);
  -webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);-webkit-font-smoothing:antialiased}
.dset.open{display:flex;flex-direction:column}
.dset *{box-sizing:border-box}
.dset button{font-family:inherit;color:inherit}
.dset .top{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;padding:22px max(16px,3.2vw) 6px}
.dset h2{margin:0;font-size:26px;font-weight:300;letter-spacing:.28em;line-height:1}
.dset .dev{font-size:12px;letter-spacing:.08em;color:#8fa1b4;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:50%}
.dset .dev b{color:#5bd1f5;font-weight:600}
.dset .ribbon{position:relative;display:flex;align-items:center;gap:6px;padding:10px max(16px,3.2vw) 0;border-bottom:1px solid rgba(255,255,255,.1)}
.dset .glyph{flex:none;display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:24px;padding:0 6px;border-radius:5px;
  border:1px solid rgba(255,255,255,.5);background:rgba(255,255,255,.06);font:700 11px/1 inherit;letter-spacing:.04em;cursor:pointer;margin-bottom:10px}
.dset .glyph:hover{background:rgba(255,255,255,.16)}
.dset .tabs{position:relative;flex:1;display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;scroll-snap-type:x proximity;min-width:0}
.dset .tabs::-webkit-scrollbar{display:none}
.dset .tab{flex:none;scroll-snap-align:center;background:none;border:0;color:#8fa1b4;font:600 13px/1 inherit;letter-spacing:.16em;
  padding:13px clamp(10px,1.6vw,22px) 17px;cursor:pointer;min-height:46px;white-space:nowrap;border-radius:4px 4px 0 0}
.dset .tab:hover{color:#dfe7ef;background:rgba(255,255,255,.05)}
.dset .tab.on{color:#fff;background:linear-gradient(180deg,rgba(255,255,255,.12),rgba(255,255,255,.03))}
.dset .ink{position:absolute;bottom:0;height:3px;background:#5bd1f5;box-shadow:0 0 12px rgba(91,209,245,.6);border-radius:2px;pointer-events:none}
.dset .count{flex:none;font-size:11px;letter-spacing:.12em;color:#6f8296;margin:0 4px 10px}
.dset .body{flex:1;display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,1fr);gap:max(18px,2.6vw);padding:4px max(16px,3.2vw) 0;min-height:0}
.dset .list{overflow-y:auto;padding:0 6px 28px 0;min-height:0;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.2) transparent}
.dset .sec{position:sticky;top:0;z-index:1;margin:0;padding:16px 0 8px;font-size:11.5px;font-weight:600;letter-spacing:.22em;color:#5bd1f5;
  text-transform:uppercase;background:linear-gradient(180deg,rgba(5,12,22,1) 70%,rgba(5,12,22,0))}
.dset .row{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:14px;min-height:50px;padding:5px 10px 5px 18px;
  margin:2px 0;background:rgba(255,255,255,.035);border-radius:2px;cursor:pointer;touch-action:pan-y;outline:none}
.dset .row:hover{background:rgba(255,255,255,.07)}
.dset .row.on{background:rgba(255,255,255,.15);box-shadow:inset 0 0 0 1px rgba(255,255,255,.18)}
.dset .row.on::before{content:"";position:absolute;left:0;top:6px;bottom:6px;width:3px;background:#5bd1f5;border-radius:2px}
.dset .row .lab{font-size:15px;line-height:1.25;display:flex;align-items:center;gap:8px}
.dset .row .dot{width:6px;height:6px;border-radius:50%;background:#f5c14a;flex:none;opacity:0}
.dset .row.changed .dot{opacity:1}
.dset .ctl{display:flex;align-items:center;gap:6px;font-variant-numeric:tabular-nums;min-width:0}
.dset .arrow{width:36px;height:36px;border:0;background:none;border-radius:50%;font-size:20px;line-height:1;cursor:pointer;color:#c3cfdb;flex:none}
.dset .arrow:hover{background:rgba(255,255,255,.12);color:#fff}
.dset .pick{min-width:11em;text-align:center;font-size:14px;letter-spacing:.06em;white-space:nowrap}
.dset .pips{display:flex;gap:4px;justify-content:center;margin-top:5px}
.dset .pips i{width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,.25)}
.dset .pips i.on{background:#5bd1f5}
.dset .track{position:relative;width:min(210px,24vw);height:34px;cursor:ew-resize;touch-action:none;flex:none}
.dset .track .rail{position:absolute;left:0;right:0;top:15px;height:4px;background:rgba(255,255,255,.18);border-radius:2px}
.dset .track .fill{position:absolute;left:0;top:15px;height:4px;background:#5bd1f5;border-radius:2px}
.dset .track .knob{position:absolute;top:8px;width:18px;height:18px;margin-left:-9px;border-radius:50%;background:#eef3f8;box-shadow:0 0 0 3px rgba(91,209,245,.35)}
.dset .num{min-width:4.2em;text-align:right;font-size:14px}
.dset .act{display:inline-flex;align-items:center;gap:9px;min-height:38px;padding:0 16px 0 6px;border-radius:19px;border:1px solid rgba(255,255,255,.3);
  background:rgba(255,255,255,.06);font-size:13px;letter-spacing:.12em;cursor:pointer}
.dset .act:hover,.dset .row.on .act{background:rgba(91,209,245,.18);border-color:#5bd1f5}
.dset .act kbd,.dset .bindbox kbd{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;border-radius:13px;border:1.5px solid rgba(255,255,255,.55);font:700 11px/1 inherit;padding:0 7px}
.dset .info{max-width:min(380px,40vw);text-align:right;font-size:13px;color:#a9b8c7;line-height:1.35;white-space:pre-line}
.dset .bindbox{position:absolute;inset:0;z-index:5;display:none;align-items:center;justify-content:center;background:rgba(2,6,12,.88)}
.dset .bindbox.on{display:flex}
.dset .bindbox>div{width:min(520px,92vw);padding:28px 30px;border:1px solid rgba(91,209,245,.5);background:rgba(8,20,36,.96);text-align:center}
.dset .bindbox .k{font-size:11px;letter-spacing:.22em;color:#5bd1f5}
.dset .bindbox .q{margin:14px 0 6px;font-size:26px;font-weight:300;letter-spacing:.06em;color:#fff}
.dset .bindbox .who{font-size:13px;color:#8fa1b4}
.dset .bindbox .steps{display:flex;gap:6px;justify-content:center;margin:18px 0 10px}
.dset .bindbox .steps i{width:30px;height:4px;background:rgba(255,255,255,.2)}.dset .bindbox .steps i.done{background:#5bd1f5}.dset .bindbox .steps i.now{background:#fff}
.dset .bindbox button{margin-top:12px;background:none;border:0;color:#d7e0e9;font-size:13px;cursor:pointer;min-height:40px}
.dset .desc{border-left:1px solid rgba(255,255,255,.1);padding:18px 0 24px max(16px,2.2vw);color:#c6d1dc;font-size:15px;line-height:1.55;overflow-y:auto}
.dset .desc .kicker{font-size:11px;letter-spacing:.22em;color:#5bd1f5;text-transform:uppercase}
.dset .desc h3{margin:6px 0 10px;font-size:22px;font-weight:400;color:#fff}
.dset .desc .now{display:flex;gap:18px;margin:14px 0 4px;font-size:12px;letter-spacing:.1em;color:#8fa1b4}
.dset .desc .now b{display:block;font-size:20px;letter-spacing:.02em;color:#fff;font-weight:500;margin-top:2px}
.dset .desc svg{display:block;width:100%;max-width:460px;height:auto;margin-top:16px}
.dset .desc .note{margin-top:12px;font-size:12px;color:#f5c14a;word-break:break-all}
.dset .foot{display:flex;flex-wrap:wrap;align-items:center;gap:6px 26px;justify-content:flex-end;padding:12px max(16px,3.2vw) max(14px,env(safe-area-inset-bottom));
  border-top:1px solid rgba(255,255,255,.1);background:rgba(0,0,0,.25)}
.dset .foot button{display:flex;align-items:center;gap:9px;background:none;border:0;color:#d7e0e9;font-size:13px;letter-spacing:.06em;cursor:pointer;min-height:42px;padding:0 2px}
.dset .foot button:hover{color:#fff}
.dset .foot kbd{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;border-radius:13px;border:1.5px solid rgba(255,255,255,.55);
  font:700 11px/1 inherit;padding:0 7px;color:#fff}
.dset.t1 .row .lab,.dset.t1 .desc,.dset.t1 .pick,.dset.t1 .num{font-size:17px}.dset.t1 .row{min-height:58px}
.dset.t2 .row .lab,.dset.t2 .desc,.dset.t2 .pick,.dset.t2 .num{font-size:20px}.dset.t2 .row{min-height:66px}.dset.t2 .tab{font-size:15px}
.dset .list.swap{animation:dsetIn .18s ease-out}
@keyframes dsetIn{from{opacity:0;transform:translateX(var(--dx,12px))}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.dset .list.swap{animation:none}.dset .ink{transition:none!important}}
@media (prefers-reduced-motion:no-preference){.dset .ink{transition:left .2s ease,width .2s ease}.dset .row{transition:background .12s}.dset .track .fill,.dset .track .knob{transition:none}}
@media (max-width:760px){
  .dset .info{max-width:none;text-align:left}
  .dset .top{padding-top:16px}.dset h2{font-size:20px}.dset .dev{display:none}
  .dset .body{grid-template-columns:1fr}.dset .desc{display:none}
  .dset .row{grid-template-columns:1fr;gap:2px;padding:8px 8px 8px 16px}.dset .ctl{justify-content:flex-end}
  .dset .track{flex:1;width:auto}.dset .pick{min-width:8em}.dset .count{display:none}
  .dset .foot{justify-content:space-between;gap:4px 12px}}
`;
  const ACTION_NAMES = { Jump: "Jump", Dash: "Dash", Interact: "Interact", Switch: "Switch Weapon", Aim: "Aim / Shield", Attack: "Attack",
    Melee: "Melee", Shoulder: "Swap Shoulder", Sprint: "Sprint", ViewCycle: "Camera View", CallVehicle: "Call Ghost", NextCube: "Next Cube",
    Menu: "Game Menu", View: "Field Menu" };
  const STICK_NAMES = { MoveX: "Strafe", MoveY: "Forward / Back", LookX: "Turn", LookY: "Look Up / Down" };
  const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  /* A generic pad (an original outline, not any maker's shape) with callouts: which action sits on each input. */
  function padDiagram(labels, at) {
    const L = (pos, fb) => esc((labels && labels[pos]) || fb);
    const left = [["zl", "LT", 30], ["l", "LB", 58], ["l3", "L STICK", 92], ["up", "D-PAD UP", 124], ["left", "D-PAD LEFT", 150], ["right", "D-PAD RIGHT", 176], ["down", "D-PAD DOWN", 202]];
    const right = [["zr", "RT", 30], ["r", "RB", 58], ["y", "", 92], ["x", "", 118], ["b", "", 144], ["a", "", 170], ["r3", "R STICK", 204]];
    const name = { y: L("north", "Y"), x: L("west", "X"), b: L("east", "B"), a: L("south", "A"), zl: L("zl", "LT"), zr: L("zr", "RT"), l: L("l", "LB"), r: L("r", "RB"),
      back: L("back", "VIEW"), start: L("start", "MENU") };
    const anchor = { zl: [193, 70], l: [195, 86], l3: [200, 124], up: [228, 156], left: [218, 166], right: [238, 166], down: [228, 176], back: [246, 116],
      zr: [327, 70], r: [325, 86], y: [318, 110], x: [304, 124], b: [332, 124], a: [318, 138], r3: [292, 166], start: [274, 116] };
    let s = '<svg viewBox="0 0 520 260" role="img" aria-label="Controller layout" font-family="Segoe UI,system-ui,sans-serif"><g fill="none" stroke="rgba(255,255,255,.55)" stroke-width="2">' +
      '<path d="M190 92 Q260 80 330 92 Q378 100 392 150 Q404 200 384 222 Q366 238 344 214 L318 186 Q260 196 202 186 L176 214 Q154 238 136 222 Q116 200 128 150 Q142 100 190 92 Z"/>' +
      '<rect x="182" y="64" width="22" height="12" rx="4"/><rect x="316" y="64" width="22" height="12" rx="4"/>' +
      '<circle cx="200" cy="124" r="14"/><circle cx="292" cy="166" r="14"/>' +
      '<path d="M216 160 h6 v-6 h12 v6 h6 v12 h-6 v6 h-12 v-6 h-6 z"/>' +
      '<circle cx="318" cy="110" r="7"/><circle cx="304" cy="124" r="7"/><circle cx="332" cy="124" r="7"/><circle cx="318" cy="138" r="7"/>' +
      '<rect x="240" y="111" width="12" height="9" rx="3"/><rect x="268" y="111" width="12" height="9" rx="3"/></g>';
    const call = (list, side) => list.forEach(([k, fb, y]) => {
      const [ax, ay] = anchor[k]; const what = at[k] || "";
      const x = side < 0 ? 4 : 516, tx = side < 0 ? 112 : 408;
      const on = what ? "#eef3f8" : "rgba(255,255,255,.35)";
      s += '<path d="M' + ax + ' ' + ay + ' L' + tx + ' ' + y + '" stroke="' + (what ? "rgba(91,209,245,.7)" : "rgba(255,255,255,.18)") + '" stroke-width="1" fill="none"/>';
      s += '<text x="' + x + '" y="' + (y - 3) + '" text-anchor="' + (side < 0 ? "start" : "end") + '" font-size="9" letter-spacing="1" fill="#8fa1b4">' + (name[k] || fb) + '</text>';
      s += '<text x="' + x + '" y="' + (y + 9) + '" text-anchor="' + (side < 0 ? "start" : "end") + '" font-size="11" fill="' + on + '">' + esc(what || "-") + '</text>';
    });
    call(left, -1); call(right, 1);
    for (const [k, fb, x, side] of [["back", "VIEW", 236, -1], ["start", "MENU", 284, 1]]) {   /* the centre buttons label upward */
      const [ax, ay] = anchor[k], what = at[k] || "";
      s += '<path d="M' + ax + ' ' + (ay - 6) + ' L' + ax + ' 44" stroke="' + (what ? "rgba(91,209,245,.7)" : "rgba(255,255,255,.18)") + '" stroke-width="1" fill="none"/>';
      s += '<text x="' + x + '" y="20" text-anchor="' + (side < 0 ? "end" : "start") + '" font-size="9" letter-spacing="1" fill="#8fa1b4">' + (name[k] || fb) + '</text>';
      s += '<text x="' + x + '" y="34" text-anchor="' + (side < 0 ? "end" : "start") + '" font-size="11" fill="' + (what ? "#eef3f8" : "rgba(255,255,255,.35)") + '">' + esc(what || "-") + '</text>';
    }
    return s + "</svg>";
  }

  function mountPanel(opt) {
    const S = opt.settings, pad = opt.pad || null;
    const doc = root.document;
    if (!doc.getElementById(STYLE_ID)) { const st = doc.createElement("style"); st.id = STYLE_ID; st.textContent = CSS; doc.head.appendChild(st); }
    const el = doc.createElement("div");
    el.className = "dset"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); el.setAttribute("aria-label", "Settings");
    el.innerHTML =
      '<div class="top"><h2>SETTINGS</h2><div class="dev" aria-live="polite"></div></div>' +
      '<div class="ribbon"><button class="glyph" data-k="lb" aria-label="Previous tab">LB</button>' +
      '<div class="tabs" role="tablist" aria-label="Settings tabs"></div><span class="count"></span>' +
      '<button class="glyph" data-k="rb" aria-label="Next tab">RB</button><span class="ink"></span></div>' +
      '<div class="body"><div class="list" role="tabpanel"></div><div class="desc" aria-live="polite"></div></div>' +
      '<div class="foot"></div>' +
      '<div class="bindbox" role="alertdialog" aria-live="assertive"><div><div class="k">TEACH BUTTONS</div><div class="q"></div><div class="who"></div>' +
      '<div class="steps"></div><button data-k="cancelbind"><kbd>Esc</kbd> Cancel</button></div></div>';
    (opt.host || doc.body).appendChild(el);
    const $ = q => el.querySelector(q);
    const tabsEl = $(".tabs"), listEl = $(".list"), descEl = $(".desc"), footEl = $(".foot"), inkEl = $(".ink"), devEl = $(".dev"), countEl = $(".count");
    let openedAt = 0;                                       /* touch: the tap that opened the panel must not also click it */
    el.addEventListener("click", e => { if (performance.now() - openedAt < 400) { e.stopPropagation(); e.preventDefault(); } }, true);
    let tab = 0, row = 0, open = false, raf = 0, lastMove = 0, note = "", builtTab = -1, rowEls = [], usingPad = false, scrolledTo = "", lastInfo = 0;
    const tabs = () => S.tabs();
    const rowsHere = () => S.rows(tabs()[tab]);
    const device = () => (pad ? pad.devices()[0] : null);
    const SYMBOL = { Cross: "\u2715", Circle: "\u25cb", Square: "\u25a1", Triangle: "\u25b3" };   /* PlayStation face buttons as printed */
    function glyph(action, fallback) {                       /* the connected pad's name for a button, else a keyboard key */
      const d = device();
      if (d && usingPad) { const g = pad.label(action, d.index); return SYMBOL[g] || g; }
      return fallback;
    }
    function buildTabs() {
      tabsEl.innerHTML = "";
      tabs().forEach((t, i) => {
        const b = doc.createElement("button"); b.className = "tab"; b.textContent = t; b.setAttribute("role", "tab"); b.id = "dset-tab-" + i;
        b.onclick = () => go(i);
        tabsEl.appendChild(b);
      });
    }
    function buildRows() {                                   /* once per tab; values update in place afterwards */
      listEl.innerHTML = ""; rowEls = [];
      let sec = null;
      rowsHere().forEach((r, i) => {
        if (r.section !== sec) { sec = r.section; const h = doc.createElement("h4"); h.className = "sec"; h.textContent = sec; listEl.appendChild(h); }
        const d = doc.createElement("div"); d.className = "row"; d.setAttribute("role", "option"); d.tabIndex = -1;
        d.innerHTML = '<div class="lab"><span class="dot" title="Changed from default"></span><span></span></div><div class="ctl"></div>';
        d.querySelector(".lab span:last-child").textContent = r.label;
        const ctl = d.querySelector(".ctl");
        const parts = { d };
        if (r.kind === "slider") {
          const minus = doc.createElement("button"); minus.className = "arrow"; minus.textContent = "\u2212"; minus.setAttribute("aria-label", "Less " + r.label);
          const plus = doc.createElement("button"); plus.className = "arrow"; plus.textContent = "+"; plus.setAttribute("aria-label", "More " + r.label);
          const tr = doc.createElement("div"); tr.className = "track"; tr.innerHTML = '<span class="rail"></span><span class="fill"></span><span class="knob"></span>';
          tr.setAttribute("role", "slider"); tr.setAttribute("aria-label", r.label); tr.setAttribute("aria-valuemin", r.min); tr.setAttribute("aria-valuemax", r.max);
          const num = doc.createElement("span"); num.className = "num";
          minus.onclick = e => { e.stopPropagation(); select(i); S.nudge(r.id, -1); refresh(); };
          plus.onclick = e => { e.stopPropagation(); select(i); S.nudge(r.id, 1); refresh(); };
          const drag = e => { const b = tr.getBoundingClientRect(); const f = Math.min(1, Math.max(0, (e.clientX - b.left) / b.width)); S.set(r.id, r.min + f * (r.max - r.min)); refresh(); };
          tr.addEventListener("pointerdown", e => { e.stopPropagation(); select(i); try { tr.setPointerCapture(e.pointerId); } catch (x) {} tr.dragging = true; drag(e); });
          tr.addEventListener("pointermove", e => { if (tr.dragging) drag(e); });
          const stop = () => { tr.dragging = false; };
          tr.addEventListener("pointerup", stop); tr.addEventListener("pointercancel", stop); tr.addEventListener("lostpointercapture", stop);
          ctl.append(minus, tr, plus, num);
          Object.assign(parts, { fill: tr.querySelector(".fill"), knob: tr.querySelector(".knob"), num, tr });
        } else if (r.kind === "action") {
          const go = doc.createElement("button"); go.className = "act"; go.setAttribute("aria-label", r.label);
          go.onclick = e => { e.stopPropagation(); select(i); S.activate(r.id); refresh(); };
          ctl.append(go);
          Object.assign(parts, { act: go });
        } else if (r.kind === "info") {
          const info = doc.createElement("span"); info.className = "info";
          ctl.append(info);
          Object.assign(parts, { info });
        } else {
          const prev = doc.createElement("button"); prev.className = "arrow"; prev.textContent = "\u2039"; prev.setAttribute("aria-label", "Previous " + r.label);
          const next = doc.createElement("button"); next.className = "arrow"; next.textContent = "\u203a"; next.setAttribute("aria-label", "Next " + r.label);
          const pick = doc.createElement("div"); pick.className = "pick"; pick.innerHTML = "<div></div><div class='pips'></div>";
          const n = r.kind === "toggle" ? 2 : r.choices.length;
          pick.querySelector(".pips").innerHTML = "<i></i>".repeat(n);
          prev.onclick = e => { e.stopPropagation(); select(i); S.nudge(r.id, -1); refresh(); };
          next.onclick = e => { e.stopPropagation(); select(i); S.nudge(r.id, 1); refresh(); };
          ctl.append(prev, pick, next);
          Object.assign(parts, { text: pick.firstChild, pips: Array.from(pick.querySelectorAll(".pips i")) });
        }
        d.onclick = () => { if (row === i && r.kind !== "slider") { S.activate(r.id); } select(i); refresh(); };
        d.onpointerenter = e => { if (e.pointerType === "mouse") usingPad = false; };
        listEl.appendChild(d); rowEls.push(parts);
      });
      builtTab = tab;
    }
    function select(i) { row = i; }
    function go(i, dir) {
      if (i === tab) return;
      const n = tabs().length;
      dir = dir || (i > tab ? 1 : -1);
      tab = (i + n) % n; row = 0; note = "";
      listEl.classList.remove("swap"); void listEl.offsetWidth; listEl.style.setProperty("--dx", (dir * 14) + "px"); listEl.classList.add("swap");
      refresh();
    }
    function refreshTabs() {
      const btns = Array.from(tabsEl.children);
      btns.forEach((b, i) => { b.classList.toggle("on", i === tab); b.setAttribute("aria-selected", i === tab); b.tabIndex = i === tab ? 0 : -1; });
      const cur = btns[tab];
      if (cur) {
        if (cur.scrollIntoView) cur.scrollIntoView({ block: "nearest", inline: "center" });
        const rb = el.querySelector(".ribbon").getBoundingClientRect(), cb = cur.getBoundingClientRect();
        inkEl.style.left = (cb.left - rb.left + 8) + "px"; inkEl.style.width = Math.max(0, cb.width - 16) + "px";
      }
      countEl.textContent = (tab + 1) + " / " + btns.length;
      listEl.setAttribute("aria-labelledby", "dset-tab-" + tab);
      const lb = el.querySelector('[data-k="lb"]'), rbb = el.querySelector('[data-k="rb"]');
      lb.textContent = glyph("l", "Q"); rbb.textContent = glyph("r", "E");
    }
    function describe(r) {
      const fmtDefault = () => {
        if (r.kind === "toggle") return r.default ? "ON" : "OFF";
        if (r.kind === "choice") return r.choices[r.default];
        return (r.step >= 1 ? Math.round(r.default) : r.default.toFixed(1)) + (r.unit || "");
      };
      const help = typeof r.help === "function" ? r.help() : r.help;
      let html = '<div class="kicker">' + esc(r.section) + "</div><h3>" + esc(r.label) + "</h3><p>" + esc(help).replace(/\n/g, "<br>") + "</p>";
      if (r.kind !== "action" && r.kind !== "info") html += '<div class="now"><span>CURRENT<b>' + esc(S.format(r.id)) + "</b></span><span>DEFAULT<b>" + esc(fmtDefault()) + "</b></span></div>";
      const L = S.layout(), d = device();
      const labels = d ? { south: pad.label("a", d.index), east: pad.label("b", d.index), west: pad.label("x", d.index), north: pad.label("y", d.index),
        l: pad.label("l", d.index), r: pad.label("r", d.index), zl: pad.label("zl", d.index), zr: pad.label("zr", d.index),
        back: pad.label("back", d.index), start: pad.label("start", d.index) } : null;
      if (L && r.id === "ButtonLayout") {
        const lay = L.buttons[S.choice("ButtonLayout")] || L.buttons.DEFAULT, at = {};
        const add = (k, a) => { at[k] = at[k] ? at[k] + " / " + a : a; };
        for (const a in lay) for (const k of lay[a]) add(k, ACTION_NAMES[a] || a);
        for (const a in L.fixed) add(L.fixed[a], ACTION_NAMES[a] || a);
        html += padDiagram(labels, at);
      } else if (L && r.id === "ThumbstickLayout") {
        const st = L.sticks[S.choice("ThumbstickLayout")] || L.sticks.DEFAULT, at = {};
        for (const k in st) { const stick = st[k][0] === "l" ? "l3" : "r3"; at[stick] = at[stick] ? at[stick] + " + " + STICK_NAMES[k] : STICK_NAMES[k]; }
        html += padDiagram(labels, at);
      }
      if (note) html += '<div class="note">' + esc(note) + "</div>";
      descEl.innerHTML = html;
    }
    function refreshFoot() {
      const hints = [["a", glyph("confirm", "Enter"), "Select"], ["y", glyph("y", "R"), "Reset Tab"], ["x", glyph("x", "C"), "Copy Settings"], ["b", glyph("cancel", "Esc"), "Back"]];
      const key = hints.map(h => h[1]).join("|");
      if (footEl.dataset.key === key) return;
      footEl.dataset.key = key;
      footEl.innerHTML = hints.map(([k, g, t]) => '<button data-k="' + k + '"><kbd>' + esc(g) + "</kbd>" + t + "</button>").join("");
      footEl.querySelectorAll("button").forEach(b => b.addEventListener("click", () => act(b.dataset.k)));
    }
    function refresh() {
      if (!S.loaded()) { listEl.textContent = "Loading settings..."; return; }
      el.classList.toggle("t1", S.get("TextSize") === 1); el.classList.toggle("t2", S.get("TextSize") === 2);
      if (!tabsEl.children.length) buildTabs();
      if (builtTab !== tab) buildRows();
      const rs = rowsHere(); row = Math.max(0, Math.min(row, rs.length - 1));
      rs.forEach((r, i) => {
        const p = rowEls[i]; if (!p) return;
        p.d.classList.toggle("on", i === row); p.d.setAttribute("aria-selected", i === row);
        p.d.classList.toggle("changed", r.kind !== "action" && r.kind !== "info" && S.get(r.id) !== r.default);
        if (p.act) { p.act.innerHTML = "<kbd>" + esc(glyph("confirm", "Enter")) + "</kbd>" + esc(r.button || "START"); }
        else if (p.info) { p.info.textContent = S.format(r.id); }
        else if (p.fill) {
          const f = S.fraction(r.id) * 100;
          p.fill.style.width = f + "%"; p.knob.style.left = f + "%"; p.num.textContent = S.format(r.id); p.tr.setAttribute("aria-valuenow", S.get(r.id));
        } else {
          p.text.textContent = S.format(r.id);
          const v = S.get(r.id); p.pips.forEach((pp, k) => pp.classList.toggle("on", k === v));
        }
      });
      const cur = rowEls[row];
      if (cur && cur.d.scrollIntoView && (scrolledTo !== tab + ":" + row)) { scrolledTo = tab + ":" + row; cur.d.scrollIntoView({ block: "nearest" }); }
      if (rs[row]) describe(rs[row]);
      const d = device();
      devEl.innerHTML = d ? "<b>\u25cf</b> " + esc(d.name) : "Keyboard &amp; mouse";
      refreshTabs(); refreshFoot();
    }
    function act(k) {
      const rs = rowsHere(), cur = rs[row];
      if (k !== "x") note = "";
      if (k === "lb" || k === "rb") return go(tab + (k === "rb" ? 1 : -1), k === "rb" ? 1 : -1);
      if (k === "up") row = (row + rs.length - 1) % rs.length;
      else if (k === "down") row = (row + 1) % rs.length;
      else if ((k === "left" || k === "right") && cur) S.nudge(cur.id, k === "right" ? 1 : -1);
      else if (k === "a" && cur) S.activate(cur.id);
      else if (k === "y") S.resetTab(tabs()[tab]);
      else if (k === "x") {
        const text = JSON.stringify(S.export());
        try { root.navigator.clipboard.writeText(text); note = "Copied. Paste it into Saved/Config/DaedalusSettings.json to use these settings in Unreal."; } catch (e) { note = text; }
      }
      else if (k === "b") return close();
      refresh();
    }
    const KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Enter: "a", Space: "a", Escape: "b", Backspace: "b",
      KeyQ: "lb", KeyE: "rb", PageUp: "lb", PageDown: "rb", KeyR: "y", KeyC: "x" };
    function onKey(e) {
      if (!open) return;
      if (pad && pad.binding()) { if (e.code === "Escape") { e.preventDefault(); e.stopPropagation(); pad.cancelBind(); } return; }
      const k = KEYS[e.code]; if (!k) return;
      e.preventDefault(); e.stopPropagation();
      if (usingPad) { usingPad = false; }
      act(k);
    }
    root.addEventListener("keydown", onKey, true);
    root.addEventListener("resize", () => { if (open) refreshTabs(); });
    el.querySelectorAll(".glyph").forEach(b => b.addEventListener("click", () => act(b.dataset.k)));
    const bindEl = $(".bindbox");
    bindEl.querySelector("button").onclick = () => { if (pad) pad.cancelBind(); };
    function bindView() {                                   /* the pad module's BIND, shown console-style prompt */
      const step = pad && pad.binding();
      bindEl.classList.toggle("on", !!step);
      if (!step) return false;
      const all = ["up", "down", "left", "right", "confirm", "cancel", "menu"], i = all.indexOf(step);
      const NAMES = { up: "UP", down: "DOWN", left: "LEFT", right: "RIGHT", confirm: "CONFIRM", cancel: "BACK", menu: "MENU" };
      bindEl.querySelector(".q").textContent = "Press the button for " + NAMES[step];
      const d = device(); bindEl.querySelector(".who").textContent = d ? d.name : "Any controller";
      bindEl.querySelector(".steps").innerHTML = all.map((x, k) => '<i class="' + (k < i ? "done" : k === i ? "now" : "") + '"></i>').join("");
      return true;
    }
    function loop(now) {                                     /* pad: edges for buttons, held + repeat for directions */
      if (!open) return;
      raf = root.requestAnimationFrame(loop);
      if (!pad) return;
      pad.poll();
      if (bindView()) { bindEl.dataset.was = "1"; pad.clearEdges(); return; }
      if (bindEl.dataset.was === "1") { bindEl.dataset.was = ""; pad.clearEdges(); refresh(); return; }
      if (now - lastInfo > 500) { lastInfo = now; refresh(); }      /* live rows (connected pads) and pad glyphs stay current */
      const pressed = a => { const v = pad.pressed(a); if (v && !usingPad) { usingPad = true; footEl.dataset.key = ""; } return v; };
      for (const [a, k] of [["confirm", "a"], ["cancel", "b"], ["menu", "b"], ["y", "y"], ["x", "x"], ["l", "lb"], ["r", "rb"]]) if (pressed(a)) return act(k);
      for (const d of ["up", "down", "left", "right"]) if (pressed(d)) { lastMove = now + 260; return act(d); }
      const dirs = ["up", "down", "left", "right"].filter(d => pad.held(d));
      if (dirs.length && now > lastMove) { lastMove = now + 90; act(dirs[0]); }
    }
    function openP() {
      if (open) return; open = true; el.classList.add("open"); openedAt = performance.now();
      usingPad = !!(pad && pad.devices().length);
      footEl.dataset.key = ""; refresh();
      if (pad) { pad.poll(); pad.clearEdges(); }
      raf = root.requestAnimationFrame(loop);
      if (opt.onOpen) opt.onOpen();
    }
    function close() {
      if (!open) return; open = false; el.classList.remove("open"); root.cancelAnimationFrame(raf);
      if (pad) pad.clearEdges();
      if (opt.onClose) opt.onClose();
    }
    S.ready(() => { if (open) refresh(); });
    return { open: openP, close, toggle: () => (open ? close() : openP()), isOpen: () => open, element: el, act,
      state: () => ({ tab: tabs()[tab], row: (rowsHere()[row] || {}).id }) };
  }

  /* The controller rows every app shares: what is plugged in, Teach Buttons (BIND) and Reset, on the Controller tab. */
  function addPadRows(settings, pad) {
    if (!pad) return;
    const list = () => { const d = pad.devices(); return d.length ? d.map(x => x.name).join("\n") : "None. Plug one in or pair it, then press any button."; };
    const how = () => {
      const d = pad.devices();
      if (!d.length) return "Any controller works when it is plugged in: Xbox, PlayStation, Switch, Razer, GameSir, 8BitDo, retro pads and adapters, arcade sticks and encoders. Press a button on it to wake it.";
      const S = { standard: "the standard layout", bundle: "the community controller map", custom: "your taught buttons", guess: "a best guess (use Teach Buttons)" };
      return d.map(x => x.name + ": " + x.family + " family, read through " + S[x.source] + "." + (x.oneButton ? " One button: tap to confirm, hold to go back, hold longer for the menu." : "") + (x.note ? " " + x.note : "")).join("\n");
    };
    settings.extend({ tab: "CONTROLLER", section: "Devices", first: true, rows: [
      { id: "PadDevices", kind: "info", label: "Connected", value: list, help: how },
      { id: "PadTeach", kind: "action", label: "Teach Buttons", button: "TEACH", help: "Press each button you want for up, down, left, right, confirm, back and menu. Use it for any controller that doesn't feel right; it remembers that controller." },
      { id: "PadForget", kind: "action", label: "Forget Taught Buttons", button: "RESET", help: "Go back to the controller's own layout." },
    ] });
    settings.onAction("PadTeach", () => pad.startBind());
    settings.onAction("PadForget", () => pad.resetBinds());
  }

  root.DaedalusSettings = { create, mountPanel, addPadRows, version: "daedalus-settings/1" };
})(typeof window !== "undefined" ? window : globalThis);
