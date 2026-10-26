// SPDX-License-Identifier: MIT
// Prismheart waystones core (G10, disk-saver), no browser:  node tools/rpg_demo/waystone_core_test.js
"use strict";
const W = require("./waystones.js");
let pass = 0, total = 0;
function check(name, ok) { total++; if (ok) pass++; console.log((ok ? "ok   " : "FAIL ") + name); }
function throws(fn, re) { try { fn(); return false; } catch (e) { return re.test(e.message); } }

const L = W.validate([
  { id: "hearthgate", bit: 0, name: "Hearthgate Stone", x: 10, y: 10 },
  { id: "windmere", bit: 1, name: "Windmere Lodestone", x: 20, y: 13 },
  { id: "cinderstep", bit: 2, name: "Cinderstep Stone", x: 10, y: 4 },
  { id: "sunwell", bit: 4, name: "Sunwell Lodestone", x: 4, y: 7 },
]);
const awake = new Set();
check("a fresh journey has no waystones awake", W.encode(L, awake) === "WAY1.0." + W.fnv1a("WAY1.0").toString(16).padStart(8, "0"));
check("stepping on one wakes it the first time only", W.activate(awake, W.at(L, 10, 10)) === true && W.activate(awake, W.at(L, 10, 10)) === false);
check("no waystone on an empty tile", W.at(L, 0, 0) === null && W.activate(awake, null) === false);
check("one awake waystone goes nowhere", W.destinations(L, awake, "hearthgate").length === 0);
W.activate(awake, W.byId(L, "windmere")); W.activate(awake, W.byId(L, "sunwell"));
const d = W.destinations(L, awake, "hearthgate");
check("destinations: only awake ones, nearest first", d.map(x => x.id).join() === "sunwell,windmere");
check("fare: 5 gold + 1 per tile, 30 minutes", d[0].tiles === 9 && d[0].gold === 14 && d[0].minutes === 30 && d[1].gold === 18);
check("a sleeping start goes nowhere", W.destinations(L, awake, "cinderstep").length === 0);
check("custom fares are honoured", W.destinations(L, awake, "hearthgate", { base_gold: 0, gold_per_tile: 2, minutes: 5 })[0].gold === 18);
check("ties go by id", W.destinations(W.validate([{ id: "a", bit: 0, name: "A", x: 0, y: 0 }, { id: "c", bit: 1, name: "C", x: 1, y: 0 }, { id: "b", bit: 2, name: "B", x: -1, y: 0 }]), new Set(["a", "b", "c"]), "a").map(x => x.id).join() === "b,c");
let t = W.travel(L, awake, "hearthgate", "windmere", 100);
check("travel pays the fare", t.ok && t.gold === 82 && t.to.x === 20 && t.to.y === 13 && t.minutes === 30);
t = W.travel(L, awake, "hearthgate", "windmere", 17);
check("travel refuses when the purse is short", !t.ok && t.why === "gold" && t.need === 18);
check("travel refuses a sleeping waystone", W.travel(L, awake, "hearthgate", "cinderstep", 999).why === "not awake");
check("travel refuses itself", W.travel(L, awake, "hearthgate", "hearthgate", 999).why === "not from here");
const s = W.encode(L, awake);
check("WAY1 string: bits 0, 1, 4 -> mask 13", s.startsWith("WAY1.13.") && s.length === 16);
const back = W.decode(L, s);
check("decode gives the same waystones back", back.ok && [...back.awake].sort().join() === "hearthgate,sunwell,windmere");
check("a build without a waystone ignores its bit", [...W.decode(L.filter(w => w.id !== "sunwell"), s).awake].sort().join() === "hearthgate,windmere");
const bads = [[null, "not a waystone record"], ["", "not a waystone record"], ["WAY1.13", "not a waystone record"], ["WAY2.13." + s.split(".")[2], "unknown version WAY2"],
  ["WAY1.013." + s.split(".")[2], "bad mask"], ["WAY1.13.00000000", "check failed"], ["WAY1.17." + s.split(".")[2], "check failed"], ["WAY1.1g.00000000", "bad mask"], ["x".repeat(40), "not a waystone record"]];
for (const [str, why] of bads) { const r = W.decode(L, str); check("refuses " + JSON.stringify(str) + ": " + why, !r.ok && r.why === why && r.awake.size === 0); }
const big = W.validate([{ id: "top", bit: 30, name: "Top", x: 1, y: 1 }]);
check("bit 30 round-trips", [...W.decode(big, W.encode(big, new Set(["top"]))).awake].join() === "top");
check("validate refuses duplicate ids", throws(() => W.validate([{ id: "a", bit: 0, name: "A", x: 0, y: 0 }, { id: "a", bit: 1, name: "A", x: 1, y: 0 }]), /duplicate id/));
check("validate refuses duplicate bits", throws(() => W.validate([{ id: "a", bit: 0, name: "A", x: 0, y: 0 }, { id: "b", bit: 0, name: "B", x: 1, y: 0 }]), /duplicate bit/));
check("validate refuses bit 31", throws(() => W.validate([{ id: "a", bit: 31, name: "A", x: 0, y: 0 }]), /bad bit/));
check("validate refuses two on one tile", throws(() => W.validate([{ id: "a", bit: 0, name: "A", x: 0, y: 0 }, { id: "b", bit: 1, name: "B", x: 0, y: 0 }]), /two on one tile/));
check("validate refuses a bad id", throws(() => W.validate([{ id: "Bad Id", bit: 0, name: "A", x: 0, y: 0 }]), /bad id/));
console.log(pass + "/" + total + " passed");
process.exit(pass === total ? 0 : 1);
