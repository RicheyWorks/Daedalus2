// SPDX-License-Identifier: MIT
// The baseline squad director and DTO 1 writer for the browser (ADR-060): a line-for-line port of
// DaedalusTacticsCore.h's Decide()/Write(), the same as Java's SquadDirector. tools/reach_parity.mjs checks it
// against engines/unreal/core-test/tactics_parity.txt (40 seeded squads, byte for byte).
export const MAX_ORDERS = 256;
export const SETTINGS = { retreatBelow: 0.3, flankRadius: 900, retreatDistance: 1500, highGround: 300, engage: 2600 };

/** C's printf("%.1f"): the exact binary value, ties to even, and a negative that rounds to zero keeps its sign. */
export function num(v) {
  const a = Math.abs(v);
  let s = a.toFixed(1);   // exact decimal of the binary value, but an exact tie goes up
  // An exact tie (the hundredths digit is exactly 5 with nothing after) needs a = n/20 exactly, which a binary double
  // can only be when it is a multiple of 1/4: x.25 or x.75. Scaling by 4 and 2 is exact, so this test is too.
  if (Number.isInteger(a * 4) && !Number.isInteger(a * 2)) {
    const down = Math.floor(a * 10);   // a*10 = d + 0.5 exactly
    const even = down % 2 === 0 ? down : down + 1;
    s = (even / 10).toFixed(1);
  }
  const negative = v < 0 || Object.is(v, -0);
  return negative ? "-" + s : s;
}

function unit2(dx, dy) {
  const l = Math.sqrt(dx * dx + dy * dy);
  return l < 1e-6 ? [1, 0] : [dx / l, dy / l];
}

export function flankPoint(player, from, side, radius) {
  const [dx, dy] = unit2(from.x - player.x, from.y - player.y);
  const s = side === "LEFT" ? 1.0 : -1.0;
  return { x: player.x + -dy * s * radius, y: player.y + dx * s * radius, z: player.z };
}

export function awayFrom(player, from, distance) {
  const [dx, dy] = unit2(from.x - player.x, from.y - player.y);
  return { x: from.x + dx * distance, y: from.y + dy * distance, z: from.z };
}

/** units: [{name, at: {x,y,z}, health, maxHealth, seesPlayer}]. Returns {squad, tick, orders: [{unit, verb, side, at, why}]}. */
export function decide(squad, tick, input, player, s = SETTINGS) {
  const out = { squad, tick, orders: [] };
  if (!input.length) return out;
  const d2 = (u) => { const dx = u.at.x - player.x, dy = u.at.y - player.y, dz = u.at.z - player.z; return dx * dx + dy * dy + dz * dz; };
  let units = [...input].sort((a, b) => { const da = d2(a), db = d2(b); return da !== db ? da - db : (a.name < b.name ? -1 : a.name > b.name ? 1 : 0); });
  if (units.length > MAX_ORDERS) units = units.slice(0, MAX_ORDERS);
  let mx = 0, my = 0, mz = 0;
  for (const u of units) { mx += u.at.x; my += u.at.y; mz += u.at.z; }
  const mid = { x: mx / units.length, y: my / units.length, z: mz / units.length };
  const inRange = Math.sqrt(d2(units[0])) <= s.engage;
  const high = player.z - mid.z > s.highGround;
  let healthy = 0;
  for (const u of units) {
    const frac = u.maxHealth > 0 ? u.health / u.maxHealth : 0;
    const dist = Math.trunc(Math.sqrt(d2(u)));
    const o = { unit: u.name, verb: "HOLD", side: "-", at: u.at, why: "" };
    if (!inRange) {
      o.why = `player out of range (${dist} cm)`;
    } else if (frac < s.retreatBelow) {
      o.verb = "RETREAT";
      o.at = awayFrom(player, u.at, s.retreatDistance);
      o.why = `health ${Math.trunc(frac * 100)}%`;
    } else {
      const rank = healthy++;
      if (rank === 0) {
        o.verb = high ? "DEFEND" : "ATTACK";
        o.at = high ? mid : player;
        o.why = high ? "player holds high ground; hold the approach" : `closest (${dist} cm)`;
      } else if (rank <= 2) {
        o.verb = "FLANK";
        o.side = rank === 1 ? "LEFT" : "RIGHT";
        o.at = flankPoint(player, mid, o.side, s.flankRadius);
        o.why = "cut off escape, " + (rank === 1 ? "left" : "right");
      } else {
        o.verb = "DEFEND";
        o.at = mid;
        o.why = "hold the squad's centre";
      }
    }
    out.orders.push(o);
  }
  out.orders.sort((a, b) => (a.unit < b.unit ? -1 : a.unit > b.unit ? 1 : 0));
  return out;
}

/** DTO 1 text, byte for byte as the C++ Write(). */
export function write(spec) {
  let t = `DTO 1\nsquad ${spec.squad} tick ${spec.tick}\n`;
  for (const o of spec.orders) {
    t += `order ${o.unit} ${o.verb} ${o.side} ${num(o.at.x)} ${num(o.at.y)} ${num(o.at.z)}`;
    const why = (o.why || "").replace(/\n/g, " ");
    if (why) t += " | " + why;
    t += "\n";
  }
  return t;
}
