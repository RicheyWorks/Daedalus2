/* SPDX-License-Identifier: MIT
   Prismheart waystones (PRISM02, contest G10, disk-saver): the pure rules, no DOM, no game state.
   Works in the browser (window.PrismWaystones) and in Node (require) so waystone_core_test.js can check it.

   Waystones are placed by tools/rpg_demo/waystones.py at build time (data.json "waystones": [{id, bit, name, x, y}]).
   Step on one to awaken it; from any awakened waystone you can travel to any other awakened one for a fare in gold
   and time. Which ones are awake is saved at the inn as a WAY1 string:

       WAY1.<mask hex>.<check hex>     e.g. WAY1.13.9c1f05a2  (bits 0, 1 and 4 awake)

   'mask' sets bit N for the waystone whose permanent slot is N; 'check' is FNV-1a 32 of "WAY1." + mask. A string
   that is malformed, from another version or fails its check decodes to "none awake" with a reason; bits for
   waystones this build does not know are ignored, never invented. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PrismWaystones = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const VERSION = "WAY1";
  const MAX_BIT = 30;                                   /* stays inside a positive 32-bit int */
  const DEFAULT_FARE = { base_gold: 5, gold_per_tile: 1, minutes: 30 };

  function fnv1a(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
    return h >>> 0;
  }

  /* Check the build's waystone list; throws on anything the save format could not represent. */
  function validate(list) {
    if (!Array.isArray(list)) throw new Error("waystones: not a list");
    const ids = new Set(), bits = new Set(), spots = new Set();
    for (const w of list) {
      if (!w || typeof w.id !== "string" || !/^[a-z][a-z0-9_]{0,31}$/.test(w.id)) throw new Error("waystones: bad id " + (w && w.id));
      if (!Number.isInteger(w.bit) || w.bit < 0 || w.bit > MAX_BIT) throw new Error("waystones: bad bit for " + w.id);
      if (!Number.isInteger(w.x) || !Number.isInteger(w.y)) throw new Error("waystones: no position for " + w.id);
      if (ids.has(w.id)) throw new Error("waystones: duplicate id " + w.id);
      if (bits.has(w.bit)) throw new Error("waystones: duplicate bit " + w.bit);
      if (spots.has(w.x + "," + w.y)) throw new Error("waystones: two on one tile at " + w.x + "," + w.y);
      ids.add(w.id); bits.add(w.bit); spots.add(w.x + "," + w.y);
    }
    return list;
  }

  const at = (list, x, y) => list.find(w => w.x === x && w.y === y) || null;
  const byId = (list, id) => list.find(w => w.id === id) || null;

  /* Wake a waystone; true only the first time. */
  function activate(awake, w) { if (!w || awake.has(w.id)) return false; awake.add(w.id); return true; }

  function fare(from, to, f) {
    f = f || DEFAULT_FARE;
    const tiles = Math.abs(from.x - to.x) + Math.abs(from.y - to.y);
    return { tiles, gold: f.base_gold + f.gold_per_tile * tiles, minutes: f.minutes };
  }

  /* Where you can go from an awakened waystone: every other awakened one, nearest first, ties by id. */
  function destinations(list, awake, fromId, f) {
    const from = byId(list, fromId);
    if (!from || !awake.has(fromId)) return [];
    return list.filter(w => w.id !== fromId && awake.has(w.id))
      .map(w => Object.assign({ id: w.id, name: w.name, x: w.x, y: w.y }, fare(from, w, f)))
      .sort((a, b) => a.tiles - b.tiles || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }

  /* Try a trip with the gold in hand. Returns {ok, to, gold, minutes} or {ok:false, why}. */
  function travel(list, awake, fromId, toId, gold, f) {
    const d = destinations(list, awake, fromId, f).find(x => x.id === toId);
    if (!d) return { ok: false, why: awake.has(toId) ? "not from here" : "not awake" };
    if (gold < d.gold) return { ok: false, why: "gold", need: d.gold };
    return { ok: true, to: d, gold: gold - d.gold, minutes: d.minutes };
  }

  function encode(list, awake) {
    let mask = 0;
    for (const w of list) if (awake.has(w.id)) mask |= (1 << w.bit);
    const m = (mask >>> 0).toString(16);
    return VERSION + "." + m + "." + fnv1a(VERSION + "." + m).toString(16).padStart(8, "0");
  }

  function decode(list, s) {
    const none = why => ({ ok: false, awake: new Set(), why });
    if (typeof s !== "string" || s.length > 32) return none("not a waystone record");
    const p = s.split(".");
    if (p.length !== 3) return none("not a waystone record");
    if (p[0] !== VERSION) return none("unknown version " + p[0]);
    if (!/^[0-9a-f]{1,8}$/.test(p[1]) || (p[1].length > 1 && p[1][0] === "0")) return none("bad mask");
    if (!/^[0-9a-f]{8}$/.test(p[2]) || parseInt(p[2], 16) !== fnv1a(VERSION + "." + p[1])) return none("check failed");
    const mask = parseInt(p[1], 16), awake = new Set();
    for (const w of list) if (mask & (1 << w.bit)) awake.add(w.id);
    return { ok: true, awake, why: "" };
  }

  return { VERSION, MAX_BIT, DEFAULT_FARE, fnv1a, validate, at, byId, activate, fare, destinations, travel, encode, decode };
});
