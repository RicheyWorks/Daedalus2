// Shardring + the shared DaedalusPad module, headless: a fake standard gamepad drives the real pad layer,
// its logical events go through Shardring.PAD_ACTIONS / applyVerb, and the game state is checked.
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const ROOT = path.resolve(__dirname, "..", "..");
const html = fs.readFileSync(path.join(__dirname, "web", "shardring", "index.html"), "utf8");
const core = html.match(/<script id="shardring-core">([\s\S]*?)<\/script>/)[1];
const mod = { exports: {} };
new Function("module", core)(mod);
const S = mod.exports;
let fail = 0;
const ok = (c, m) => { if (!c) { console.log("FAIL", m); fail++; } };

// 1. action map + applyVerb without any pad
let g = new S.Game(3, "normal"), sel = 0, r;
r = S.applyVerb(g, sel, "prev"); ok(r.sel === 9, "prev wraps");
r = S.applyVerb(g, 9, "next"); ok(r.sel === 0, "next wraps");
r = S.applyVerb(g, 4, "place"); ok(r.placed && g.ring[4] !== null && g.pouch === 49, "place sets facet");
r = S.applyVerb(g, 4, "place"); ok(!r.placed && g.pouch === 49, "occupied facet ignored");
ok(S.applyVerb(g, 0, "restart").restart, "restart");
ok(S.applyVerb(g, 0, "cancel").sel === 0 && S.PAD_ACTIONS.cancel === undefined, "unmapped verb is a no-op");

// 2. the real shared pad module in a fake window
const handlers = {};
const buttons = Array.from({ length: 17 }, () => ({ pressed: false, value: 0 }));
const gp = { index: 0, id: "Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)", mapping: "standard",
             connected: true, buttons, axes: [0, 0, 0, 0] };
const win = { navigator: { userAgent: "Windows", getGamepads: () => [gp] }, performance: { now: () => Date.now() },
              addEventListener: (t, f) => { handlers[t] = f; }, localStorage: { getItem: () => null, setItem: () => {} },
              console, setInterval: () => 0, clearInterval: () => {} };
win.window = win;
const ctx = vm.createContext(Object.assign(win, { setInterval: win.setInterval, clearInterval: win.clearInterval }));
vm.runInContext(fs.readFileSync(path.join(ROOT, "daedalus-server/src/main/resources/static/controllers/daedalus-pad.js"), "utf8"), ctx);
ok(typeof ctx.DaedalusPad === "object", "DaedalusPad loaded");
g = new S.Game(5, "easy"); sel = 0; let restarts = 0;
const pad = ctx.DaedalusPad.create({ sampleMs: 0, onChange: e => {
  if (e.type === "down" && S.PAD_ACTIONS[e.action]) {
    const res = S.applyVerb(g, sel, S.PAD_ACTIONS[e.action]);
    if (res.restart) { restarts++; g = new S.Game(5, "easy"); sel = 0; } else sel = res.sel;
  }
} });
const tick = () => handlers.gamepadconnected({ gamepad: gp });
const press = i => { buttons[i].pressed = true; buttons[i].value = 1; tick(); buttons[i].pressed = false; buttons[i].value = 0; tick(); };
tick();
press(15); press(15); ok(sel === 2, "D-pad right x2 -> facet 2, got " + sel);
press(14); ok(sel === 1, "D-pad left -> facet 1");
press(0); ok(g.ring[1] !== null && g.pouch === 59, "A places on facet 1");
gp.axes[0] = 0.9; tick(); gp.axes[0] = 0; tick(); ok(sel === 2, "stick right -> facet 2, got " + sel);
press(9); ok(restarts === 1 && g.pouch === 60, "Start restarts");
pad.destroy();
console.log(fail ? "FAIL " + fail : "OK controller");
process.exit(fail ? 1 : 0);
