// SPDX-License-Identifier: MIT
// Session seat and trail helpers. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  function whoMoves(session, seat) {
    return session && (seat || session.primary);
  }

  function extendTrail(trail, from, to) {
    const next = trail ? trail.slice() : [];
    if (next.length === 0 && from) next.push(from);
    const last = next[next.length - 1];
    if (!last || last.row !== to.row || last.col !== to.col) next.push(to);
    return next;
  }

  function tileAt(tiles, p) {
    if (!tiles || !p) return null;
    const row = tiles[2 * p.row + 1];
    return row ? row[2 * p.col + 1] : null;
  }

  global.DaedalusSeat = {whoMoves, extendTrail, tileAt};
})(window);
