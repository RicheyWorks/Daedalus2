// SPDX-License-Identifier: MIT
/*
 * DaedalusPad: one controller layer for every Daedalus web client (realm, Prismheart demo, future pages).
 *
 *   <script src="/controllers/daedalus-pad.js"></script>            (or: import "/controllers/daedalus-pad.js")
 *   const pad = DaedalusPad.create({ bundle: "/controllers/controller-bundle.json", onChange: e => ... });
 *   pad.held("confirm"); pad.pressed("menu"); pad.axes().lx; pad.label("confirm"); pad.devices();
 *
 * Where a button's meaning comes from, highest first:
 *   1. BIND: the player taught this exact pad (stored per pad id in localStorage).
 *   2. The browser's "standard" mapping (Xbox, Elite Series 2, Razer Wolverine V2/V3 incl. 8K, GameSir in X-input
 *      mode, DualShock/DualSense, Switch Pro, most 8BitDo modes, GP2040-CE boards in X-input mode ...).
 *   3. The controller bundle: SDL_GameControllerDB's community mapping for this USB vendor:product on this platform
 *      (retro pads, adapters for N64 / GameCube / Saturn / Dreamcast / NES / SNES / Genesis, arcade sticks and
 *      encoders, Atari joysticks ...), plus Daedalus' curated lineup for names, families and button labels.
 *   4. A family guess using DaedalusControllers.json numbering (Button2 = south/A, Button1 = east/B, Button10 = Start)
 *      with POV-hat d-pads detected from their resting value.
 *
 * Logical actions: up down left right confirm cancel menu select, and the positional names a b x y l r zl zr
 * l3 r3 start back guide (a = south face button, b = east, x = west, y = north). Axes: lx ly rx ry lt rt.
 * confirm follows the pad family's custom (Nintendo-style pads confirm with the A label, which sits east) unless
 * setConfirm("position") makes south confirm everywhere. Pads without a second button use the one-button rule:
 * tap = confirm, hold = cancel, long hold = menu. Pads without Start open the menu with Select or A+B together.
 * The left stick also drives up/down/left/right as one cardinal with press 0.55 / release 0.40 / switch bias 0.10
 * (the same numbers as the native portal-controls translator). Inputs are sampled every 4 ms so taps shorter
 * than a frame on high-polling pads still land. Arcade keyboard encoders (I-PAC, X-Arcade mode 1) can be read
 * through the MAME default keys with arcadeKeys: true.
 */
(function (root) {
  "use strict";
  const POS = ["a", "b", "x", "y", "l", "r", "zl", "zr", "back", "start", "l3", "r3", "up", "down", "left", "right", "guide"];
  const STANDARD = { a: 0, b: 1, x: 2, y: 3, l: 4, r: 5, zl: 6, zr: 7, back: 8, start: 9, l3: 10, r3: 11, up: 12, down: 13, left: 14, right: 15, guide: 16 };
  const SDL_NAME = { a: "a", b: "b", x: "x", y: "y", leftshoulder: "l", rightshoulder: "r", lefttrigger: "zl", righttrigger: "zr",
    back: "back", start: "start", leftstick: "l3", rightstick: "r3", dpup: "up", dpdown: "down", dpleft: "left", dpright: "right", guide: "guide",
    leftx: "lx", lefty: "ly", rightx: "rx", righty: "ry" };
  const GENERIC = { a: [1], b: [0], x: [2], y: [3], l: [4], r: [5], zl: [6], zr: [7], back: [8], start: [9] };
  const LOGICAL = ["up", "down", "left", "right", "confirm", "cancel", "menu", "select"].concat(POS);
  const BIND_STEPS = ["up", "down", "left", "right", "confirm", "cancel", "menu"];
  const MAME_P1 = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", ControlLeft: "a", AltLeft: "b",
    Space: "x", ShiftLeft: "y", KeyZ: "l", KeyX: "r", Digit1: "start", Digit5: "back" };

  function platform() {
    const ua = (root.navigator && (navigator.userAgent || "")) || "";
    if (/android/i.test(ua)) return "A";
    if (/iphone|ipad|ipod/i.test(ua)) return "I";
    if (/mac os x|macintosh/i.test(ua)) return "M";
    if (/linux|cros/i.test(ua)) return "L";
    return "W";
  }
  function parseId(id) {                                   /* Chrome "... (Vendor: 045e Product: 0b00)"; Firefox "045e-0b00-Name" */
    let m = /vendor:\s*([0-9a-f]{1,4})\s*product:\s*([0-9a-f]{1,4})/i.exec(id);
    if (!m) m = /^([0-9a-f]{1,4})-([0-9a-f]{1,4})-/i.exec(id);
    const name = id.replace(/\s*\((standard gamepad|xinput[^)]*)?[^)]*vendor[^)]*\)\s*/i, " ").replace(/^[0-9a-f]{1,4}-[0-9a-f]{1,4}-/i, "").trim();
    return { vid: m ? m[1].toLowerCase().padStart(4, "0") : null, pid: m ? m[2].toLowerCase().padStart(4, "0") : null, name: name || id };
  }
  function parseSdl(map) {                                 /* "a:b0,leftx:a0,dpup:h0.1,+lefty:-a1,righttrigger:a5~" */
    const out = {};
    for (const part of map.split(",")) {
      const i = part.indexOf(":"); if (i < 0) continue;
      let tgt = part.slice(0, i), src = part.slice(i + 1);
      let half = 0;
      if (tgt[0] === "+" || tgt[0] === "-") { half = tgt[0] === "+" ? 1 : -1; tgt = tgt.slice(1); }
      const name = SDL_NAME[tgt]; if (!name) continue;
      let s = null, m;
      if ((m = /^b(\d+)$/.exec(src))) s = { b: +m[1] };
      else if ((m = /^h(\d+)\.(\d+)$/.exec(src))) s = { hat: +m[1], mask: +m[2] };
      else if ((m = /^([+-]?)a(\d+)(~?)$/.exec(src))) s = { ax: +m[2], half: m[1] === "+" ? 1 : m[1] === "-" ? -1 : 0, inv: !!m[3] };
      if (!s) continue;
      s.out = half;
      (out[name] = out[name] || []).push(s);
    }
    return out;
  }
  function hatDirs(v) {                                    /* POV hat on one axis: -1 up, then clockwise in 1/7 steps; ~1.29 centred */
    if (v === undefined || v > 1.05 || v < -1.05) return 0;
    const i = Math.round((v + 1) / (2 / 7)) % 8;
    return [1, 3, 2, 6, 4, 12, 8, 9][i];                  /* SDL masks: 1 up 2 right 4 down 8 left */
  }

  function create(opt) {
    opt = Object.assign({ storageKey: "daedalus.pad.v1", digitalStick: true, sampleMs: 4, oneButton: true, arcadeKeys: false,
      deadzone: 0.15, onChange: null }, opt || {});
    const plat = platform();
    let bundle = null;
    let store = {};
    try { store = JSON.parse(root.localStorage.getItem(opt.storageKey) || "{}") || {}; } catch (e) { store = {}; }
    store.confirm = store.confirm || opt.confirm || "label";
    store.binds = store.binds || {};
    const save = () => { try { root.localStorage.setItem(opt.storageKey, JSON.stringify(store)); } catch (e) {} };
    const pads = {};                                       /* gamepad index -> pad record */
    const held = {}, edges = {}, ups = {};
    let keyHeld = {};
    let bind = null;
    const emit = e => { if (opt.onChange) try { opt.onChange(e); } catch (err) { if (root.console) console.error(err); } };

    function familyOf(rec) {
      if (rec.dev && rec.dev.f) return rec.dev.f;
      const id = rec.id.toLowerCase();
      if (/xinput|xbox/.test(id)) return "xbox";
      if (rec.vid === "057e") return /2019|n64/.test(rec.pid + id) ? "n64" : "nintendo";
      if (rec.vid === "054c") return "playstation";
      return "generic";
    }
    function resolve(rec) {
      const key = rec.vid && rec.pid ? rec.vid + ":" + rec.pid : null;
      rec.dev = bundle && key ? bundle.devices[key] || null : null;
      rec.model = rec.dev && rec.dev.k >= 0 ? bundle.models[rec.dev.k] : null;
      if (!rec.model && bundle) {                          /* no USB ids (e.g. XInput on Windows): match the curated names */
        const k = bundle.models.findIndex(m => { try { return new RegExp(m.match, "i").test(rec.id); } catch (e) { return false; } });
        if (k >= 0) rec.model = bundle.models[k];
      }
      rec.family = rec.model ? rec.model.family : familyOf(rec);
      if (rec.dev && rec.dev.f && rec.dev.f !== "generic") rec.family = rec.dev.f;
      rec.custom = store.binds[rec.id] || null;
      rec.sdl = null;
      if (rec.custom) rec.source = "custom";
      else if (rec.mapping === "standard") rec.source = "standard";
      else if (rec.dev && (rec.dev.m[plat] || rec.dev.m.W)) { rec.sdl = parseSdl(rec.dev.m[plat] || rec.dev.m.W); rec.source = "bundle"; }
      else rec.source = "guess";
      const has = n => rec.custom ? !!rec.custom[n] : rec.sdl ? !!rec.sdl[n] : true;
      rec.oneButton = opt.oneButton && !rec.custom && (rec.sdl ? !rec.sdl.b : false);
      rec.noStart = !rec.custom && rec.sdl ? !rec.sdl.start : false;
      rec.labels = (bundle && bundle.families[rec.family]) || FALLBACK_LABELS[rec.family] || FALLBACK_LABELS.generic;
      rec.name = rec.model ? rec.model.maker + " " + rec.model.model : rec.dev ? rec.dev.n : parseId(rec.id).name;
      return has;
    }
    function connect(gp) {
      const ids = parseId(gp.id);
      const rec = { index: gp.index, id: gp.id, vid: ids.vid, pid: ids.pid, mapping: gp.mapping, rest: Array.from(gp.axes),
        state: {}, ax: { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0 }, stick: null, src: "pad" + gp.index, hold: null, hats: [] };
      rec.hats = rec.rest.map((v, i) => Math.abs(v) > 1.05 ? i : -1).filter(i => i >= 0);
      resolve(rec);
      pads[gp.index] = rec;
      emit({ type: "connect", pad: describe(rec) });
    }
    const btn = (gp, i) => { const b = gp.buttons[i]; return !!b && (b.pressed || b.value > 0.5); };
    const val = (gp, i) => { const b = gp.buttons[i]; return b ? (typeof b.value === "number" ? b.value : b.pressed ? 1 : 0) : 0; };
    function hatMask(gp, rec, n) {
      const ax = rec.hats[n];
      if (ax !== undefined) return hatDirs(gp.axes[ax]);
      if (n === 0 && gp.buttons.length > 15) return (btn(gp, 12) ? 1 : 0) | (btn(gp, 15) ? 2 : 0) | (btn(gp, 13) ? 4 : 0) | (btn(gp, 14) ? 8 : 0);
      return 0;
    }
    function srcValue(gp, rec, s) {                       /* one SDL / bind source -> 0..1 (buttons) or -1..1 (axes) */
      if (s.b !== undefined) return val(gp, s.b);
      if (s.hat !== undefined) return hatMask(gp, rec, s.hat) & s.mask ? 1 : 0;
      if (s.hatv !== undefined) { const v = gp.axes[s.ax]; return v !== undefined && Math.abs(v - s.hatv) < 0.07 ? 1 : 0; }
      if (s.ax !== undefined) {
        let v = gp.axes[s.ax] || 0;
        if (s.inv) v = -v;
        if (s.half) v = s.half > 0 ? Math.max(0, v) : Math.max(0, -v);
        if (s.s) v = v * s.s;
        return v;
      }
      return 0;
    }
    function read(gp, rec) {
      const st = {}, ax = { lx: gp.axes[0] || 0, ly: gp.axes[1] || 0, rx: gp.axes[2] || 0, ry: gp.axes[3] || 0, lt: 0, rt: 0 };
      if (rec.custom) {
        for (const k in rec.custom) for (const s of rec.custom[k]) if (srcValue(gp, rec, s) > 0.5) st[k] = true;
      } else if (rec.source === "standard") {
        for (const k in STANDARD) st[k] = btn(gp, STANDARD[k]);
        ax.lt = val(gp, 6); ax.rt = val(gp, 7);
      } else if (rec.sdl) {
        for (const k in rec.sdl) {
          let v = 0;
          for (const s of rec.sdl[k]) {
            const x = srcValue(gp, rec, s);
            v = Math.abs(x) > Math.abs(v) ? (s.out ? s.out * Math.abs(x) : x) : v;
          }
          if (k in ax) ax[k] = v;
          else if (k === "zl" || k === "zr") {                /* analog triggers: 0 at their resting value, 1 fully pulled */
            const s0 = rec.sdl[k][0];
            let t = v;
            if (s0.ax !== undefined && !s0.half) { const r = rec.rest[s0.ax] || 0, raw = (gp.axes[s0.ax] || 0) * (s0.inv ? -1 : 1), rr = r * (s0.inv ? -1 : 1); t = Math.max(0, Math.min(1, (raw - rr) / (1 - rr || 1))); }
            ax[k === "zl" ? "lt" : "rt"] = t; st[k] = t > 0.5;
          } else st[k] = v > 0.5;
        }
        if (!rec.sdl.lx) ax.lx = 0;
        if (!rec.sdl.ly) ax.ly = 0;
        if (!rec.sdl.rx) ax.rx = 0;
        if (!rec.sdl.ry) ax.ry = 0;
      } else {
        for (const k in GENERIC) st[k] = GENERIC[k].some(i => btn(gp, i));
        const m = rec.hats.length ? hatMask(gp, rec, 0) : 0;
        st.up = !!(m & 1) || btn(gp, 12); st.right = !!(m & 2) || btn(gp, 15); st.down = !!(m & 4) || btn(gp, 13); st.left = !!(m & 8) || btn(gp, 14);
        rec.hats.forEach(i => { if (i < 4) ax[["lx", "ly", "rx", "ry"][i]] = 0; });
      }
      rec.pre = { lx: ax.lx, ly: ax.ly };                  /* the digital stick reads raw values, like the native translator */
      shapeStick(ax, "lx", "ly", "Left"); shapeStick(ax, "rx", "ry", "Right");
      ax.lt = shapeTrigger(ax.lt); ax.rt = shapeTrigger(ax.rt);
      if (rec.source === "standard") { st.zl = ax.lt > 0.5; st.zr = ax.rt > 0.5; }
      rec.ax = ax;
      return st;
    }
    /* Sticks: radial center dead zone with rescale (no cross-shaped dead zone, diagonals stay diagonal), a max input
       threshold, and an optional axial dead zone, per stick, from the Controller tab (Halo Infinite's three). */
    const setting = (id, d) => (opt.settings && opt.settings.loaded() ? opt.settings.get(id) : d);
    function shapeStick(ax, kx, ky, side) {
      const dz = setting(side + "Deadzone", opt.deadzone * 100) / 100, mx = Math.max(dz + 0.01, setting(side + "MaxInput", 100) / 100);
      const axial = setting(side + "AxialDeadzone", 0) / 100;
      let x = ax[kx], y = ax[ky];
      const m = Math.hypot(x, y);
      if (m <= dz) { ax[kx] = ax[ky] = 0; return; }
      const k = Math.min(1, (m - dz) / (mx - dz)) / m;
      x *= k; y *= k;
      if (axial > 0) { if (Math.abs(x) < axial) x = 0; if (Math.abs(y) < axial) y = 0; }
      ax[kx] = x; ax[ky] = y;
    }
    function shapeTrigger(t) {
      const lo = setting("TriggerInnerDeadzone", 5) / 100, hi = Math.max(lo + 0.01, setting("TriggerOuterDeadzone", 95) / 100);
      return Math.min(1, Math.max(0, (t - lo) / (hi - lo)));
    }
    const confirmMode = () => (opt.settings && opt.settings.loaded() ? (opt.settings.get("ConfirmButton") === 1 ? "position" : "label") : store.confirm);
    function stickDir(rec) {                               /* one cardinal: press 0.55 / release 0.40 / switch bias 0.10 */
      const src = rec.pre || rec.ax, x = src.lx, y = src.ly, axv = Math.abs(x), ayv = Math.abs(y), cur = rec.stick;
      const want = Math.max(axv, ayv) < 0.55 ? null : axv > ayv ? (x > 0 ? "right" : "left") : (y > 0 ? "down" : "up");
      if (cur) {
        const v = cur === "left" || cur === "right" ? axv : ayv;
        if (v < 0.40) return (rec.stick = want);
        if (want && want !== cur && Math.max(axv, ayv) - v > 0.10) return (rec.stick = want);
        return cur;
      }
      return (rec.stick = want);
    }
    function logical(rec, st, now) {                        /* positional -> logical, with the one-button and no-Start rules */
      const out = {};
      for (const k of POS) out[k] = !!st[k];
      if (opt.digitalStick && !(rec.custom && ["up", "down", "left", "right"].some(k => rec.custom[k] && rec.custom[k].some(s => s.ax === 0 || s.ax === 1)))) {
        const d = stickDir(rec); if (d) out[d] = true;
      }
      const east = confirmMode() === "label" && rec.labels.confirm === "east";
      if (rec.custom) { out.confirm = !!st.confirm; out.cancel = !!st.cancel; out.menu = !!st.menu; }
      else { out.confirm = east ? out.b : out.a; out.cancel = east ? out.a : out.b; out.menu = out.start; }
      out.select = out.back;
      if (rec.noStart && !out.menu) out.menu = out.back || (out.a && out.b);
      if (rec.oneButton) {      /* released before 0.35 s = confirm, released after = cancel, still held at 1.2 s = menu */
        const down = out.a;
        out.confirm = out.cancel = false; out.menu = rec.noStart ? out.back : out.start;
        if (down && !rec.hold) rec.hold = { t: now, menu: false };
        if (rec.hold) {
          const dt = now - rec.hold.t;
          if (down) { if (dt >= 1200) rec.hold.menu = true; if (rec.hold.menu) out.menu = true; }
          else { if (!rec.hold.menu) rec.pulse = { t: now, what: dt < 350 ? "confirm" : "cancel" }; rec.hold = null; }
        }
        if (rec.pulse && now - rec.pulse.t < 60) out[rec.pulse.what] = true; else rec.pulse = null;
      }
      return out;
    }
    function merge() {
      const all = {};
      for (const i in pads) { const s = pads[i].logical || {}; for (const k in s) if (s[k]) all[k] = true; }
      for (const k in keyHeld) if (keyHeld[k]) { all[k] = true; if (k === "a") all.confirm = true; if (k === "b") all.cancel = true; if (k === "start") all.menu = true; if (k === "back") all.select = true; }
      for (const k of LOGICAL) {
        const v = !!all[k];
        if (v && !held[k]) { edges[k] = true; emit({ type: "down", action: k }); }
        if (!v && held[k]) { ups[k] = true; emit({ type: "up", action: k }); }
        held[k] = v;
      }
    }
    function sample() {
      const list = root.navigator && navigator.getGamepads ? navigator.getGamepads() : [];
      const now = (root.performance || Date).now();
      for (const gp of list) {
        if (!gp || gp.connected === false) continue;
        if (!pads[gp.index] || pads[gp.index].id !== gp.id) connect(gp);
        const rec = pads[gp.index];
        if (bind) { bindStep(gp, rec); rec.logical = {}; continue; }
        rec.logical = logical(rec, read(gp, rec), now);
      }
      for (const i in pads) if (!list[i] || list[i].connected === false || list[i].id !== pads[i].id) drop(i);
      merge();
    }
    function drop(i) {
      const rec = pads[i]; if (!rec) return;
      delete pads[i];
      emit({ type: "disconnect", pad: describe(rec) });
    }
    /* BIND: teach any pad. Each step waits for a new button, axis direction or hat position away from rest. */
    function bindStep(gp, rec) {
      if (bind.index !== undefined && bind.index !== gp.index) return;
      const busy = gp.buttons.some((b, i) => btn(gp, i)) || gp.axes.some((v, i) => Math.abs(v - (rec.rest[i] || 0)) > 0.5);
      if (bind.wait) { if (!busy) bind.wait = false; return; }
      let c = null;
      const bi = gp.buttons.findIndex((b, i) => btn(gp, i));
      if (bi >= 0) c = { b: bi, name: "Button " + (bi + 1) };
      else for (let i = 0; i < gp.axes.length && !c; i++) {
        const v = gp.axes[i], r = rec.rest[i] || 0;
        if (Math.abs(r) > 1.05) { if (hatDirs(v)) c = { ax: i, hatv: Math.round(v * 1000) / 1000, name: "Hat " + (i + 1) }; }
        else if (Math.abs(v - r) > 0.6) c = { ax: i, s: Math.sign(v - r), name: "Axis " + (i + 1) + (v > r ? "+" : "-") };
      }
      if (!c) return;
      bind.index = gp.index;
      const step = bind.steps[bind.i];
      bind.map[step] = [c]; bind.names.push(step + "=" + c.name); bind.i++; bind.wait = true;
      emit({ type: "bind", step, input: c.name, next: bind.steps[bind.i] || null });
      if (bind.i >= bind.steps.length) {
        const m = bind.map;
        if (m.confirm) m.a = m.confirm; if (m.cancel) m.b = m.cancel; if (m.menu) m.start = m.menu;
        store.binds[gp.id] = m; save(); resolve(rec);
        const names = bind.names; bind = null;
        emit({ type: "bound", pad: describe(rec), names });
      }
    }
    const FALLBACK_LABELS = {
      xbox: { south: "A", east: "B", west: "X", north: "Y", l: "LB", r: "RB", zl: "LT", zr: "RT", start: "Menu", back: "View", confirm: "south" },
      nintendo: { south: "B", east: "A", west: "Y", north: "X", l: "L", r: "R", zl: "ZL", zr: "ZR", start: "+", back: "-", confirm: "east" },
      n64: { south: "A", east: "B", west: "C-Left", north: "C-Up", start: "Start", back: "C-Down", confirm: "south" },
      playstation: { south: "Cross", east: "Circle", west: "Square", north: "Triangle", l: "L1", r: "R1", zl: "L2", zr: "R2", start: "Options", back: "Create", confirm: "south" },
      generic: { south: "1", east: "2", west: "3", north: "4", l: "L1", r: "R1", zl: "L2", zr: "R2", start: "Start", back: "Select", confirm: "south" },
    };
    function describe(rec) {
      return { index: rec.index, id: rec.id, name: rec.name, vid: rec.vid, pid: rec.pid, family: rec.family, source: rec.source,
        mapping: rec.mapping, kind: rec.model ? rec.model.kind : null, maker: rec.model ? rec.model.maker : null,
        oneButton: !!rec.oneButton, noStart: !!rec.noStart, custom: !!rec.custom, note: rec.model && rec.model.note || "" };
    }
    function label(action, index) {
      const rec = index !== undefined ? pads[index] : Object.values(pads)[0];
      const L = rec ? rec.labels : FALLBACK_LABELS.xbox;
      if (rec && rec.custom && rec.custom[action]) return rec.custom[action][0].name;
      if (rec && rec.oneButton && (action === "confirm" || action === "cancel" || action === "menu"))
        return { confirm: "tap " + L.south, cancel: "hold " + L.south, menu: "long-hold " + L.south }[action];   /* hold = released after 0.35 s */
      const east = confirmMode() === "label" && L.confirm === "east";
      const pos = { confirm: east ? "east" : "south", cancel: east ? "south" : "east", a: "south", b: "east", x: "west", y: "north",
        menu: "start", start: "start", select: "back", back: "back", l: "l", r: "r", zl: "zl", zr: "zr" }[action];
      return (pos && L[pos]) || action;
    }
    function layouts() { return opt.settings && opt.settings.loaded() ? opt.settings.layout() : null; }
    function heroInputs(name) {
      const L = layouts(); if (!L) return [];
      const lay = L.buttons[opt.settings.choice("ButtonLayout")] || L.buttons.DEFAULT;
      return (lay[name] || []).concat(L.fixed[name] ? [L.fixed[name]] : []);
    }
    function stickPair(kind, index) {
      const a = api_axes(index), L = layouts();
      const st = L ? (L.sticks[opt.settings.choice("ThumbstickLayout")] || L.sticks.DEFAULT) : { MoveX: "lx", MoveY: "ly", LookX: "rx", LookY: "ry" };
      return { x: a[st[kind + "X"]] || 0, y: -(a[st[kind + "Y"]] || 0) };   /* y up = positive, like Unreal's stick Y */
    }
    function api_axes(index) {
      const r = index !== undefined ? pads[index] : Object.values(pads).find(p => p.ax && (p.ax.lx || p.ax.ly || p.ax.rx || p.ax.ry)) || Object.values(pads)[0];
      return r ? r.ax : { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0 };
    }
    if (root.addEventListener) {
      root.addEventListener("gamepadconnected", e => { if (e.gamepad) connect(e.gamepad); sample(); });
      root.addEventListener("gamepaddisconnected", e => { if (e.gamepad) drop(e.gamepad.index); merge(); });
      root.addEventListener("blur", () => { keyHeld = {}; for (const i in pads) pads[i].logical = {}; merge(); });
      if (opt.arcadeKeys) {
        root.addEventListener("keydown", e => { const k = MAME_P1[e.code]; if (k && !e.repeat) { keyHeld[k] = true; merge(); } });
        root.addEventListener("keyup", e => { const k = MAME_P1[e.code]; if (k) { keyHeld[k] = false; merge(); } });
      }
    }
    const timer = opt.sampleMs > 0 ? setInterval(sample, opt.sampleMs) : null;
    function loadBundle(b) {
      if (!b) return;
      const take = j => { bundle = j; for (const i in pads) resolve(pads[i]); emit({ type: "bundle", devices: Object.keys(j.devices).length, models: j.models.length }); };
      if (typeof b === "string") { if (root.fetch) fetch(b).then(r => r.ok ? r.json() : null).then(j => j && take(j)).catch(() => {}); }
      else take(b);
    }
    loadBundle(opt.bundle);

    return {
      poll: sample,
      held: a => !!held[a],
      pressed: a => { const v = !!edges[a]; edges[a] = false; return v; },
      released: a => { const v = !!ups[a]; ups[a] = false; return v; },
      clearEdges: () => { for (const k in edges) edges[k] = false; for (const k in ups) ups[k] = false; },
      axes: index => { const r = index !== undefined ? pads[index] : Object.values(pads).find(p => p.ax && (p.ax.lx || p.ax.ly || p.ax.rx || p.ax.ry)) || Object.values(pads)[0];
        return r ? Object.assign({}, r.ax) : { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0 }; },
      devices: () => Object.values(pads).map(describe),
      label,
      confirmMode,
      setConfirm: m => {
        if (opt.settings && opt.settings.loaded()) opt.settings.set("ConfirmButton", m === "position" ? 1 : 0);
        store.confirm = m === "position" ? "position" : "label"; save(); emit({ type: "confirm", mode: confirmMode() });
      },
      startBind: (index, steps) => { bind = { index, steps: steps || BIND_STEPS.slice(), i: 0, map: {}, names: [], wait: true }; for (const i in pads) pads[i].logical = {}; merge(); emit({ type: "bind", step: null, next: bind.steps[0] }); },
      cancelBind: () => { if (bind) { bind = null; emit({ type: "bindcancel" }); } },
      binding: () => bind ? bind.steps[bind.i] : null,
      resetBinds: index => { for (const i in pads) if (index === undefined || +i === index) { delete store.binds[pads[i].id]; resolve(pads[i]); } save(); emit({ type: "reset" }); },
      rumble: (strong, ms) => {
        if (!setting("Vibration", 1)) return;
        strong *= setting("VibrationStrength", 100) / 100;
        if (strong <= 0) return;
        for (const gp of (root.navigator && navigator.getGamepads ? navigator.getGamepads() : [])) {
          const v = gp && gp.vibrationActuator;
          if (v && v.playEffect) v.playEffect("dual-rumble", { duration: ms || 120, strongMagnitude: strong, weakMagnitude: Math.min(1, strong + 0.2) }).catch(() => {});
        }
      },
      /* The hero's controls, from the same layout tables the Unreal hero uses (settings-schema.json layouts):
         heroHeld("Jump") follows the Button Layout row, move() / look() follow the Thumbstick Layout row. */
      heroHeld: name => heroInputs(name).some(k => held[k]),
      heroPressed: name => heroInputs(name).some(k => { const v = !!edges[k]; if (v) edges[k] = false; return v; }),
      heroInputs: name => heroInputs(name),
      move: index => stickPair("Move", index),
      look: index => stickPair("Look", index),
      bundleInfo: () => bundle ? { devices: Object.keys(bundle.devices).length, models: bundle.models.length } : null,
      store: () => JSON.parse(JSON.stringify(store)),
      destroy: () => { if (timer) clearInterval(timer); },
    };
  }

  root.DaedalusPad = { create, parseId, parseSdl, hatDirs, platform, MAME_P1, version: "daedalus-pad/1" };
})(typeof window !== "undefined" ? window : globalThis);
