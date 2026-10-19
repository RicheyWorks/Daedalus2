// SPDX-License-Identifier: MIT
/* PRISM03 Prism Shard summon spirits: pure rules, no DOM.
   Each Warden in data/rpg/prism-bosses.json that drops "<Spirit> summon" becomes a summon spirit once that
   Warden is beaten (the save already keeps beaten Wardens, so spirits persist with it). In battle any standing
   hero may call an unlocked spirit: it costs MP, strikes every foe with the Warden's element (weak spot x2,
   same element x0.5) and answers once per battle. Each spirit arrives with its own soft three-note chord drawn
   from the same low D pentatonic bells as the Labyrinth Echo Bell gate (146.832-349.228 Hz, ear rules:
   sine, low-passed, gain 0.3 or less, notes rolled 110 ms apart). Loaded by index.html; also works under Node. */
(function (root) {
  "use strict";
  const ROOT_HZ = 146.832, MAX_HZ = 360, NOTE_GAIN = 0.3, ROLL_MS = 110;
  /* semitones above D3, one triad per shard, all within the 7 bells 0,3,5,7,10,12,15 */
  const SHARD_CHORD = { Fire: [0, 7, 12], Tide: [3, 7, 10], Gale: [5, 10, 15], Stone: [0, 5, 10], Light: [7, 12, 15], Shade: [0, 3, 7] };
  const hzOf = s => Math.round(ROOT_HZ * Math.pow(2, s / 12) * 1000) / 1000;

  /* bosses: prism-bosses.json entries (or the demo's dungeon boss_data). Returns spirits in data order. */
  function table(bosses) {
    const out = [];
    for (const b of bosses || []) {
      const drop = (b.drops || []).find(d => / summon$/.test(d));
      if (!drop || !SHARD_CHORD[b.shard]) continue;
      out.push({
        name: drop.replace(/ summon$/, ""), warden: b.name, shard: b.shard, element: b.element,
        power: 20 + 2 * b.level, mp: 6 + Math.floor(b.level / 3),
        chord: SHARD_CHORD[b.shard].map((s, i) => ({ semis: s, hz: hzOf(s), gain: NOTE_GAIN, at_ms: i * ROLL_MS }))
      });
    }
    return out;
  }
  /* beaten: a Set or array of beaten Warden names */
  function unlocked(spirits, beaten) {
    const has = beaten instanceof Set ? n => beaten.has(n) : n => (beaten || []).includes(n);
    return spirits.filter(s => has(s.warden));
  }
  function resist(spirit, foe) {
    if (foe.weak && foe.weak === spirit.element) return 2;
    if (foe.el && foe.el === spirit.element) return 0.5;
    return 1;
  }
  /* one foe's damage; caster: { int }, r: a roll in [0.9, 1.1] */
  function damage(spirit, foe, caster, r) {
    return Math.max(1, Math.round((spirit.power * 1.6 + (caster.int || 0) * 3 - (foe.def || 0) * 0.3) * resist(spirit, foe) * r));
  }
  /* why a call is refused, or null if it may go: used is a Set of spirit names already called this battle */
  function refusal(spirit, used, mp) {
    if (used && used.has(spirit.name)) return "ALREADY ANSWERED";
    if (mp < spirit.mp) return "NOT ENOUGH MP";
    return null;
  }
  const api = { ROOT_HZ, MAX_HZ, NOTE_GAIN, ROLL_MS, SHARD_CHORD, hzOf, table, unlocked, resist, damage, refusal };
  if (typeof module === "object" && module.exports) module.exports = api; else root.PrismSummons = api;
})(typeof window !== "undefined" ? window : globalThis);
