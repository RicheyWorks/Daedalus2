// SPDX-License-Identifier: MIT
// Fog-of-war memory. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  const DELTA = {"-1,0": "NORTH", "1,0": "SOUTH", "0,-1": "WEST", "0,1": "EAST"};

  function key(r, c) {
    return r + "," + c;
  }

  function dirFromDelta(dr, dc) {
    return DELTA[dr + "," + dc] || null;
  }

  function mergeView(fog, view) {
    const next = fog || {seen: new Set()};
    if (!next.seen) next.seen = new Set();
    next.agentId = view.agentId;
    next.position = view.position;
    next.goal = view.goal;
    next.open = view.open || [];
    next.stepsUsed = view.stepsUsed;
    next.stepsRemaining = view.stepsRemaining;
    next.arrived = view.arrived;
    next.expired = view.expired;
    next.seen.add(key(view.position.row, view.position.col));
    if (!next.walk) next.walk = [];
    const last = next.walk[next.walk.length - 1];
    if (!last || last.row !== view.position.row || last.col !== view.position.col) {
      next.walk.push(view.position);
    }
    return next;
  }

  function carveTiles(tiles, view) {
    if (!tiles || !view || !view.position) return tiles;
    const r = view.position.row, c = view.position.col;
    const tr = 2 * r + 1, tc = 2 * c + 1;
    const open = new Set(view.open || []);
    const gaps = [
      ["NORTH", tr - 1, tc], ["SOUTH", tr + 1, tc],
      ["WEST", tr, tc - 1], ["EAST", tr, tc + 1],
    ];
    const next = tiles.slice();
    for (const [dir, gr, gc] of gaps) {
      const row = next[gr];
      if (row == null || gc < 0 || gc >= row.length) continue;
      const ch = open.has(dir) ? " " : "#";
      if (row[gc] === ch) continue;
      next[gr] = row.substring(0, gc) + ch + row.substring(gc + 1);
    }
    return next;
  }

  global.DaedalusFog = {key, dirFromDelta, mergeView, carveTiles};
})(window);
