// SPDX-License-Identifier: MIT
// Hash, recipe, walk, and hotspot helpers. No DOM, no `state`.
"use strict";
(function (global) {
  function readHash(raw) {
    raw = String(raw || "").replace(/^#/, "");
    if (!raw) return {};
    if (raw === "daily") return {daily: true};
    const out = {};
    raw.split("&").forEach(part => {
      if (part === "daily") { out.daily = true; return; }
      const eq = part.indexOf("=");
      if (eq < 0) return;
      out[decodeURIComponent(part.slice(0, eq))] = decodeURIComponent(part.slice(eq + 1));
    });
    return out;
  }

  function campaignToken(h) {
    if (!h || h.campaign == null || h.campaign === "") return null;
    const raw = String(h.campaign);
    const colon = raw.lastIndexOf(":");
    if (colon >= 0) {
      const stage = Number(raw.slice(colon + 1));
      if (Number.isInteger(stage) && stage >= 0) {
        return {seed: raw.slice(0, colon), stage};
      }
    }
    return {seed: raw, stage: 0};
  }

  function mazeRecipe(maze) {
    if (!maze) return [];
    const parts = [
      "g=" + encodeURIComponent(maze.generatorId),
      "seed=" + maze.seed,
      "rows=" + maze.rows,
      "cols=" + maze.cols,
    ];
    if (maze.braid > 0) parts.push("braid=" + maze.braid);
    const hs = maze.hotspots || [];
    if (hs.length) {
      parts.push("hotspots=" + hs.length);
      parts.push("cost=" + hs[0].cost);
    }
    return parts;
  }

  function walkFromMoves(start, moves) {
    const pts = [];
    if (start) pts.push(start);
    for (const m of moves || []) {
      const p = m.to;
      if (!p) continue;
      const last = pts[pts.length - 1];
      if (!last || last.row !== p.row || last.col !== p.col) pts.push(p);
    }
    return pts;
  }

  function startFromTiles(tiles) {
    if (!tiles) return null;
    for (let r = 1; r < tiles.length; r += 2) {
      for (let c = 1; c < tiles[0].length; c += 2) {
        if (tiles[r][c] === "S") return {row: (r - 1) / 2, col: (c - 1) / 2};
      }
    }
    return null;
  }

  function rng32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  function placeSpots(rows, cols, count, seed, cost) {
    const rnd = rng32(seed >>> 0);
    const seen = new Set();
    const out = [];
    const max = Math.min(count, rows * cols);
    while (out.length < max) {
      const r = Math.floor(rnd() * rows), c = Math.floor(rnd() * cols);
      const k = r + "," + c;
      if (!seen.has(k)) {
        seen.add(k);
        out.push({row: r, col: c, cost});
      }
    }
    return out;
  }

  function ghostPrefix(ghost, nowMs) {
    if (!ghost || !ghost.start) return [];
    const e = nowMs - ghost.started;
    const pts = [ghost.start];
    for (const m of ghost.moves || []) {
      if (m.tMs <= e) pts.push(m.to);
      else break;
    }
    return pts;
  }

  global.DaedalusShare = {
    readHash, campaignToken, mazeRecipe,
    walkFromMoves, startFromTiles, rng32, placeSpots, ghostPrefix,
  };
})(window);
