// SPDX-License-Identifier: MIT
// Ghost leftover rules (ADR-006 idea #8). app.js owns leftover-state wiring;
// this file does not read leftover globals — it takes `state` plus a host bag.
"use strict";
(function (global) {
  /** If this maze has a recorded best run, race it: same pacing, hesitations and all. */
  async function summon(state, host) {
    const mazeStart = host.mazeStart;
    const thisTabSeat = host.thisTabSeat;
    if (!state.session) return;
    const mazeId = state.maze && state.maze.id;
    if (!mazeId) return;
    let run;
    try { run = await host.api(`/maze/${mazeId}/ghost`); }
    catch (ignored) { return; } // 404 — nobody has finished this maze yet
    // Fog dropped the seat and cleared the ghost while this GET was
    // out. Do not re-arm the ticker onto a walk that just emptied it.
    // Generate + Play: a late /ghost would seat the old recording
    // on the maze now on screen (N37). Maze-bound, not seat-bound —
    // a new Play on the same maze still races this recording.
    if (state.fog) return;
    if (!state.session) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Recording is a walk from the maze start. A late #session= hydrate used
    // the opener's current cell, so the ghost trail teleported from mid-run.
    const start = mazeStart(state.maze) || state.session.positions[thisTabSeat()];
    state.ghost = {
      moves: run.moves, name: run.playerName, score: run.score, elapsedMs: run.elapsedMs,
      started: performance.now(), pos: start, start, done: false,
    };
    host.log("player", `ghost summoned: ${run.playerName}'s best run `
        + `(${(run.elapsedMs / 1000).toFixed(1)}s, score ${run.score}) — beat it`);
    clearInterval(state.ghostTimer);
    state.ghostTimer = setInterval(() => {
      const g = state.ghost;
      if (!g || !state.session) { clearInterval(state.ghostTimer); return; }
      const e = performance.now() - g.started;
      let pos = g.pos, done = true;
      for (const m of g.moves) {
        if (m.tMs <= e) pos = m.to;
        else { done = false; break; }
      }
      g.pos = pos;
      if (done && !g.done) {
        g.done = true;
        host.log("player", `the ghost finished its run (${(g.elapsedMs / 1000).toFixed(1)}s)`);
        clearInterval(state.ghostTimer);
      }
      host.draw();
    }, 100);
  }

  global.DaedalusGhost = {summon};
})(window);
