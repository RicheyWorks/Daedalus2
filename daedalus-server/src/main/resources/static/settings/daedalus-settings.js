// SPDX-License-Identifier: MIT
/*
 * DaedalusSettings: the settings every Daedalus web client shares, laid out like Halo Infinite
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
 * The panel is Halo Infinite's: a tab ribbon switched with LB / RB (or Q / E), sections of rows, the selected row's
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
    const subs = {};
    const readyCbs = [];
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
      schema = s; rows = s.rows; byId = {};
      for (const r of rows) byId[r.id] = r;
      for (const r of rows) fire(r.id, api.get(r.id));
      readyCbs.splice(0).forEach(f => f(api));
    }
    const api = {
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
        const r = byId[id]; if (!r) return false;
        const v = api.get(id);
        if (r.kind === "toggle") return api.set(id, v ? 0 : 1);
        if (r.kind === "choice") return api.set(id, (v + dir + r.choices.length) % r.choices.length);
        return api.set(id, v + dir * r.step);
      },
      activate: id => { const r = byId[id]; return r && r.kind !== "slider" ? api.nudge(id, 1) : false; },
      format: id => {
        const r = byId[id]; if (!r) return "";
        const v = api.get(id);
        if (r.kind === "toggle") return v ? "ON" : "OFF";
        if (r.kind === "choice") return r.choices[v] || "?";
        const whole = r.step >= 1 && Math.abs(r.step - Math.round(r.step)) < 1e-6;
        return (whole ? String(Math.round(v)) : v.toFixed(1)) + (r.unit || "");
      },
      fraction: id => { const r = byId[id]; return r && r.max > r.min ? (api.get(id) - r.min) / (r.max - r.min) : 0; },
      resetTab: tab => { for (const r of rows) if (r.tab === tab) { delete values[r.id]; fire(r.id, r.default); } save(); },
      on: (id, f) => { (subs[id] = subs[id] || []).push(f); if (schema && id !== "*") f(api.get(id), id); return () => { subs[id] = subs[id].filter(x => x !== f); }; },
      export: () => { const o = {}; for (const r of rows) o[r.id] = api.get(r.id); return o; },
      import: obj => { let n = 0; for (const k in obj || {}) if (byId[k] && api.set(k, obj[k])) n++; return n; },
      layout: () => schema && schema.layouts,
    };
    if (opt.schema && typeof opt.schema === "object") take(opt.schema);
    else if (opt.schema && root.fetch) fetch(opt.schema).then(r => r.ok ? r.json() : null).then(j => j && take(j)).catch(() => {});
    return api;
  }

  /* ------------------------------------------------------------------------------------------- the panel */
  const CSS = `
.dset{position:fixed;inset:0;z-index:2147483000;display:none;font-family:"Segoe UI",system-ui,sans-serif;color:#edf2f7;
  background:radial-gradient(120% 90% at 50% 0%,rgba(8,20,36,.97),rgba(2,6,12,.99));-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);-webkit-font-smoothing:antialiased}
.dset.open{display:flex;flex-direction:column}
.dset *{box-sizing:border-box}
.dset .bar{display:flex;align-items:center;gap:max(10px,1.4vw);padding:18px max(16px,3vw) 10px;overflow-x:auto;scrollbar-width:none}
.dset .bar::-webkit-scrollbar{display:none}
.dset h2{margin:0 max(12px,2vw) 0 0;font-size:13px;letter-spacing:.32em;font-weight:600;color:#93a3b5;white-space:nowrap}
.dset .pill{flex:none;font-size:11px;font-weight:700;letter-spacing:.06em;border:1px solid rgba(255,255,255,.35);border-radius:4px;padding:3px 7px;color:#edf2f7;background:transparent;cursor:pointer;min-height:28px}
.dset .tab{flex:none;background:none;border:0;color:#93a3b5;font:600 14px/1 inherit;letter-spacing:.12em;padding:12px 4px;cursor:pointer;border-bottom:2px solid transparent;min-height:44px;white-space:nowrap}
.dset .tab.on{color:#edf2f7;border-bottom-color:#5bd1f5}
.dset .body{flex:1;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:max(16px,2.4vw);padding:8px max(16px,3vw) 0;min-height:0}
.dset .list{overflow-y:auto;padding-bottom:24px;min-height:0}
.dset .sec{margin:18px 0 6px;font-size:12px;letter-spacing:.2em;color:#5bd1f5;text-transform:uppercase}
.dset .row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:12px;min-height:48px;padding:6px 14px;margin:3px 0;
  background:rgba(255,255,255,.035);border-left:3px solid transparent;cursor:pointer;touch-action:pan-y}
.dset .row.on{background:rgba(255,255,255,.14);border-left-color:#5bd1f5}
.dset .row .lab{font-size:15px;line-height:1.25}
.dset .row .val{display:flex;align-items:center;gap:8px;font-variant-numeric:tabular-nums;font-size:14px;min-width:0}
.dset .row .v{min-width:7.2em;text-align:right;white-space:nowrap}
.dset .track{position:relative;width:min(200px,26vw);height:28px;cursor:ew-resize;touch-action:none}
.dset .track i{position:absolute;left:0;right:0;top:12px;height:4px;background:rgba(255,255,255,.18)}
.dset .track b{position:absolute;left:0;top:12px;height:4px;background:#5bd1f5}
.dset .step{width:36px;height:36px;border-radius:50%;border:1px solid rgba(255,255,255,.25);background:none;color:#edf2f7;font-size:18px;line-height:1;cursor:pointer}
.dset .desc{border-left:1px solid rgba(255,255,255,.12);padding:22px 0 0 max(14px,2vw);color:#c9d3de;font-size:15px;line-height:1.55;overflow-y:auto}
.dset .desc h3{margin:0 0 10px;font-size:19px;font-weight:600;color:#edf2f7}
.dset .desc .tag{display:inline-block;margin-top:14px;font-size:11px;letter-spacing:.12em;color:#93a3b5}
.dset .foot{display:flex;flex-wrap:wrap;gap:8px 22px;justify-content:flex-end;padding:12px max(16px,3vw) max(14px,env(safe-area-inset-bottom));border-top:1px solid rgba(255,255,255,.08)}
.dset .foot button{display:flex;align-items:center;gap:8px;background:none;border:0;color:#c9d3de;font:500 13px inherit;cursor:pointer;min-height:40px}
.dset .foot kbd{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:24px;border-radius:50%;border:1px solid rgba(255,255,255,.4);font:700 11px inherit;padding:0 5px}
.dset.t1 .row .lab,.dset.t1 .desc{font-size:17px}.dset.t2 .row .lab,.dset.t2 .desc{font-size:20px}
.dset.t1 .row{min-height:56px}.dset.t2 .row{min-height:64px}
@media (max-width:720px){.dset .body{grid-template-columns:1fr}.dset .desc{display:none}
  .dset .row{grid-template-columns:1fr;gap:4px;padding:8px 12px}.dset .row .val{justify-content:flex-end}
  .dset .track{flex:1;width:auto}.dset .row .v{min-width:4.5em}}
@media (prefers-reduced-motion:no-preference){.dset .row{transition:background .12s}}
`;
  function mountPanel(opt) {
    const S = opt.settings, pad = opt.pad || null;
    const doc = root.document;
    if (!doc.getElementById(STYLE_ID)) { const st = doc.createElement("style"); st.id = STYLE_ID; st.textContent = CSS; doc.head.appendChild(st); }
    const el = doc.createElement("div");
    el.className = "dset"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); el.setAttribute("aria-label", "Settings");
    el.innerHTML = '<div class="bar"><h2>SETTINGS</h2><button class="pill" data-k="lb" aria-label="Previous tab">LB</button><div class="tabs" style="display:flex;gap:max(14px,2vw)"></div><button class="pill" data-k="rb" aria-label="Next tab">RB</button></div>' +
      '<div class="body"><div class="list" role="listbox"></div><div class="desc" aria-live="polite"></div></div>' +
      '<div class="foot"><button data-k="a"><kbd>A</kbd>Change</button><button data-k="y"><kbd>Y</kbd>Reset tab</button><button data-k="x"><kbd>X</kbd>Copy settings</button><button data-k="b"><kbd>B</kbd>Back</button></div>';
    (opt.host || doc.body).appendChild(el);
    const tabsEl = el.querySelector(".tabs"), listEl = el.querySelector(".list"), descEl = el.querySelector(".desc");
    let tab = 0, row = 0, open = false, raf = 0, lastMove = 0, note = "";
    const tabs = () => S.tabs();
    const rowsHere = () => S.rows(tabs()[tab]);
    function render() {
      if (!S.loaded()) { listEl.textContent = "Loading settings..."; return; }
      el.classList.toggle("t1", S.get("TextSize") === 1); el.classList.toggle("t2", S.get("TextSize") === 2);
      tabsEl.innerHTML = "";
      tabs().forEach((t, i) => {
        const b = doc.createElement("button"); b.className = "tab" + (i === tab ? " on" : ""); b.textContent = t; b.setAttribute("aria-selected", i === tab);
        b.onclick = () => { tab = i; row = 0; render(); };
        tabsEl.appendChild(b);
        if (i === tab && b.scrollIntoView) b.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
      const rs = rowsHere(); row = Math.min(row, rs.length - 1);
      listEl.innerHTML = "";
      let sec = null;
      rs.forEach((r, i) => {
        if (r.section !== sec) { sec = r.section; const h = doc.createElement("div"); h.className = "sec"; h.textContent = sec; listEl.appendChild(h); }
        const d = doc.createElement("div"); d.className = "row" + (i === row ? " on" : ""); d.setAttribute("role", "option"); d.dataset.i = i;
        d.innerHTML = '<div class="lab"></div><div class="val"></div>';
        d.querySelector(".lab").textContent = r.label;
        const val = d.querySelector(".val");
        if (r.kind === "slider") {
          const minus = doc.createElement("button"); minus.className = "step"; minus.textContent = "-"; minus.setAttribute("aria-label", "Less");
          const plus = doc.createElement("button"); plus.className = "step"; plus.textContent = "+"; plus.setAttribute("aria-label", "More");
          const tr = doc.createElement("div"); tr.className = "track"; tr.innerHTML = '<i></i><b style="width:' + (S.fraction(r.id) * 100) + '%"></b>';
          minus.onclick = e => { e.stopPropagation(); row = i; S.nudge(r.id, -1); render(); };
          plus.onclick = e => { e.stopPropagation(); row = i; S.nudge(r.id, 1); render(); };
          const drag = e => { const b = tr.getBoundingClientRect(); const f = Math.min(1, Math.max(0, (e.clientX - b.left) / b.width)); S.set(r.id, r.min + f * (r.max - r.min)); render(); };
          tr.addEventListener("pointerdown", e => { e.stopPropagation(); row = i; tr.setPointerCapture(e.pointerId); drag(e); tr.onpointermove = drag; });
          tr.addEventListener("pointerup", () => { tr.onpointermove = null; });
          val.append(minus, tr, plus);
        }
        const v = doc.createElement("span"); v.className = "v"; v.textContent = S.format(r.id); val.appendChild(v);
        d.onclick = () => { if (row === i && r.kind !== "slider") S.activate(r.id); row = i; render(); };
        listEl.appendChild(d);
      });
      const cur = rs[row];
      if (cur) {
        descEl.innerHTML = "<h3></h3><p></p><span class='tag'></span>";
        descEl.querySelector("h3").textContent = cur.label;
        descEl.querySelector("p").textContent = cur.help;
        descEl.querySelector(".tag").textContent = note || (cur.section + (cur.native ? "" : " \u00b7 web"));
        const on = listEl.querySelector(".row.on"); if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
      }
    }
    function act(k) {
      const rs = rowsHere(), cur = rs[row];
      note = "";
      if (k === "lb" || k === "rb") { tab = (tab + (k === "rb" ? 1 : -1) + tabs().length) % tabs().length; row = 0; }
      else if (k === "up") row = (row + rs.length - 1) % rs.length;
      else if (k === "down") row = (row + 1) % rs.length;
      else if ((k === "left" || k === "right") && cur) S.nudge(cur.id, k === "right" ? 1 : -1);
      else if (k === "a" && cur) S.activate(cur.id);
      else if (k === "y") S.resetTab(tabs()[tab]);
      else if (k === "x") {
        const text = JSON.stringify(S.export());
        try { root.navigator.clipboard.writeText(text); note = "COPIED: paste into Saved/Config/DaedalusSettings.json"; } catch (e) { note = text; }
      }
      else if (k === "b") return close();
      render();
    }
    el.querySelectorAll("[data-k]").forEach(b => b.addEventListener("click", () => act(b.dataset.k)));
    const KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Enter: "a", Space: "a", Escape: "b", Backspace: "b",
      KeyQ: "lb", KeyE: "rb", PageUp: "lb", PageDown: "rb", KeyR: "y", KeyC: "x" };
    function onKey(e) {
      if (!open) return;
      const k = KEYS[e.code]; if (!k) return;
      e.preventDefault(); e.stopPropagation();
      act(k);
    }
    root.addEventListener("keydown", onKey, true);
    function loop(now) {                                  /* pad: edges for buttons, held + repeat for directions */
      if (!open) return;
      raf = root.requestAnimationFrame(loop);
      if (!pad) return;
      pad.poll();
      for (const [a, k] of [["confirm", "a"], ["cancel", "b"], ["menu", "b"], ["y", "y"], ["x", "x"], ["l", "lb"], ["r", "rb"]]) if (pad.pressed(a)) return act(k);
      const dirs = ["up", "down", "left", "right"].filter(d => pad.held(d));
      for (const d of ["up", "down", "left", "right"]) if (pad.pressed(d)) { lastMove = now + 260; return act(d); }
      if (dirs.length && now > lastMove) { lastMove = now + 90; act(dirs[0]); }
    }
    function openP() {
      if (open) return; open = true; el.classList.add("open"); render();
      if (pad) { pad.poll(); pad.clearEdges(); }
      raf = root.requestAnimationFrame(loop);
      if (opt.onOpen) opt.onOpen();
    }
    function close() {
      if (!open) return; open = false; el.classList.remove("open"); root.cancelAnimationFrame(raf);
      if (pad) pad.clearEdges();
      if (opt.onClose) opt.onClose();
    }
    S.ready(() => { if (open) render(); });
    return { open: openP, close, toggle: () => (open ? close() : openP()), isOpen: () => open, element: el, act, state: () => ({ tab: tabs()[tab], row: (rowsHere()[row] || {}).id }) };
  }

  root.DaedalusSettings = { create, mountPanel, version: "daedalus-settings/1" };
})(typeof window !== "undefined" ? window : globalThis);
