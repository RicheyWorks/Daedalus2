/* SPDX-License-Identifier: MIT
   The existing v1 journey snapshot, checked before the title screen touches live party state.
   Reading never writes, erases or repairs localStorage. Missing optional fields keep the older
   save defaults; the original record remains available to the build that wrote it. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PrismJourneySave = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const MAX_TEXT = 262144;
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const object = o => !!o && typeof o === "object" && !Array.isArray(o);
  const integer = (n, min = 0, max = Number.MAX_SAFE_INTEGER) => Number.isSafeInteger(n) && n >= min && n <= max;
  const string = (s, max = 128) => typeof s === "string" && s.length > 0 && s.length <= max;
  const list = (a, max, item) => Array.isArray(a) && a.length <= max && a.every(item);
  const record = (o, max, item) => object(o) && Object.keys(o).length <= max
    && Object.keys(o).every(k => string(k) && item(o[k]));

  // Bound the entire JSON tree, including fields a newer/older build may have added.
  function safeTree(value) {
    let count = 0;
    function visit(v, depth) {
      if (++count > 12000 || depth > 12) return false;
      if (v === null || typeof v === "boolean") return true;
      if (typeof v === "number") return Number.isFinite(v);
      if (typeof v === "string") return v.length <= 4096;
      if (!object(v) && !Array.isArray(v)) return false;
      return Object.keys(v).every(k => k !== "__proto__" && k !== "constructor" && k !== "prototype" && visit(v[k], depth + 1));
    }
    return visit(value, 0);
  }

  function member(m, jobs) {
    if (!object(m) || !string(m.name, 64) || !string(m.job, 64) || !jobs.has(m.job)
      || !integer(m.lv, 1) || !integer(m.exp) || !integer(m.next, 1)
      || !integer(m.max, 1) || !integer(m.hp, 0, m.max) || !integer(m.mmax) || !integer(m.mp, 0, m.mmax)
      || !record(m.st, 32, n => integer(n)) || !["str", "agi", "vit", "int", "spr"].every(k => integer(m.st[k]))
      || !record(m.equip, 32, s => s === null || string(s)) || !["weapon", "armor", "helm", "shield"].every(k => m.equip[k] === null || string(m.equip[k]))
      || !list(m.kinds, 16, k => string(k, 64)) || !string(m.armor, 64)
      || !list(m.spells, 256, s => string(s)) || !string(m.sprite)
      || (own(m, "defend") && typeof m.defend !== "boolean")) return false;
    return !own(m, "status") || record(m.status, 32, n => typeof n === "boolean" || integer(n));
  }

  function read(text, realm, members) {
    const no = (kind, reason) => ({ ok: false, kind, reason, value: null });
    if (text === null || text === undefined || text === "") return no("missing", "No saved journey was found.");
    if (typeof text !== "string" || text.length > MAX_TEXT) return no("invalid", "The saved record is too large to read safely.");
    let v;
    try { v = JSON.parse(text); } catch (_) { return no("invalid", "The saved record is not complete JSON."); }
    if (!object(v) || !safeTree(v)) return no("invalid", "The saved record has an unsupported structure.");
    if (v.v !== 1) return no("invalid", "This saved journey needs a different game version.");
    if ((v.realm_key === undefined ? "prism" : v.realm_key) !== realm) return no("invalid", "This saved journey belongs to a different realm.");
    const jobs = new Set((members || []).map(m => m.job));
    if (!Array.isArray(v.party) || !v.party.length || v.party.length > 4
      || !v.party.every(m => member(m, jobs))) return no("invalid", "The saved party is incomplete or unsupported.");
    const reserve = v.reserve == null ? [] : v.reserve;
    if (!list(reserve, jobs.size, m => member(m, jobs)) || v.party.length + reserve.length > jobs.size
      || new Set(v.party.concat(reserve).map(m => m.job)).size !== v.party.length + reserve.length)
      return no("invalid", "The saved reserve is incomplete or contains duplicate companions.");
    if (!record(v.bag, 2048, n => integer(n)) || !integer(v.gold)) return no("invalid", "The saved items or gold could not be read.");
    if (!list(v.opened, 4096, k => string(k))) return no("invalid", "The saved chest record could not be read.");
    if ((v.beaten != null && !list(v.beaten, 256, k => string(k)))
      || (own(v, "bossBeaten") && typeof v.bossBeaten !== "boolean")) return no("invalid", "The saved Warden record could not be read.");
    if (v.seen != null && !record(v.seen, 2048, e => object(e) && integer(e.seen) && integer(e.felled)))
      return no("invalid", "The saved bestiary could not be read.");
    if ((v.fish != null && !record(v.fish, 1024, n => integer(n)))
      || (v.quests != null && !record(v.quests, 1024, n => typeof n === "boolean")))
      return no("invalid", "The saved fish log or requests could not be read.");
    if ((own(v, "day") && !integer(v.day, 1)) || (own(v, "minute") && !integer(v.minute, 0, 1439)))
      return no("invalid", "The saved journey clock could not be read.");
    if (own(v, "at") && !integer(v.at, 0, 8640000000000000)) return no("invalid", "The saved journey date could not be read.");
    // Optional skiff/WAY1 data already has forgiving recovery: bad coordinates recall the skiff;
    // malformed/unknown masks mean none awake. Continue prepares both before applying live state.
    // Do not turn those documented policies into rejection of the whole older journey.
    v.reserve = reserve;
    v.beaten = v.beaten == null ? (v.bossBeaten ? ["PyreWarden"] : []) : v.beaten;
    v.seen = v.seen == null ? {} : v.seen;
    v.fish = v.fish == null ? {} : v.fish;
    v.quests = v.quests == null ? {} : v.quests;
    v.day = own(v, "day") ? v.day : 1;
    v.minute = own(v, "minute") ? v.minute : 7 * 60;
    return { ok: true, kind: "ready", reason: "", value: v };
  }
  return { MAX_TEXT, read };
});
