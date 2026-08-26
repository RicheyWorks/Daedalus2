// SPDX-License-Identifier: MIT
// Hunt leftover rules. app.js owns leftover-state wiring; this file does not
// read leftover globals — it takes `state` plus a host bag.
"use strict";
(function (global) {
  function same(a, b) { return a && b && a.row === b.row && a.col === b.col; }

  function mazeStatsHtml(state, host) {
    return `<span>maze</span> ${host.esc(state.maze.id.slice(0, 8))}&hellip;<br>`
        + `<span>by</span> ${host.esc(state.maze.generatorId)} &middot; ${state.maze.rows}&times;${state.maze.cols} `
        + `&middot; <span>seed</span> ${state.maze.seed}`
        + (state.maze.braid > 0 ? ` &middot; braided ${state.maze.braid}` : "")
        + `<br>`;
  }

  /**
   * Collect every waypoint, then reach the goal. The optimal collection order is computed
   * server-side by exact Held-Karp, so the score at the end compares your walk against a proven
   * best — not an estimate. Collection is also counted server-side; what we track here is only
   * for drawing.
   */
  async function start(state, host) {
    if (host.refuseSpectatorWrite("hunt waypoints")) return;
    const mazeId = state.maze.id;
    const t = await host.api(`/maze/${mazeId}/tour`);
    // Hunt then play() used to leave fog after the session POST. A Fog
    // that started while /tour was out still called play() and lost the
    // walk. Discard — Hunt is locked during fog, so this is only late.
    // Generate mid-flight: a late /tour would state.tour = t and play()
    // on the maze now on screen. Discard — same as N18 / N30.
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    state.tour = t;
    state.tourGot = [];
    // Compare / Analyze / Hardest / Lens stay armed after Hunt.
    // A leftover compare hover paints a solver path over the
    // corridor you are scored against; leftover hardest is a
    // second walk that is not the Held-Karp route (N50). Fog
    // already drops these; Hunt did not. state.tour stays.
    state.path = null; state.expansions = [];
    state.searchProgress = 1; state.pathProgress = 1;
    host.bumpAnim();
    state.race = null; state.analysis = null; state.hardest = null;
    state.field = null; state.sanctuaries = null; state.lens = null;
    state.fingerprint = null; state.caption = null;
    host.$("compareBox").innerHTML = "";
    // Leftover ASCII stays armed after Hunt. Generate / Fog /
    // Play / Solve / Hardest / Race hide #asciiOut (N68–N71).
    // Hunt did not, and play() is skipped when a seat already
    // exists, so leftover dump reminted the text/plain maze
    // under the Held-Karp walk (N72). Must not null tour (N50).
    // startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Ghost stays armed after Hunt. Fog already drops the
    // ticker. Theory / Solve / Hardest / Race already drop
    // it (N80–N83). Hunt did not, and play() is skipped when
    // a seat already exists, so leftover recording painted
    // under the Held-Karp walk (N84). Must not null tour
    // (N50). startFog still must not null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Leftover Solve stats stay after Hunt. play() rewrites
    // #stats (N92) only when it seats; a hunt on an existing
    // seat skipped that rewrite, so leftover solver numbers
    // named the previous walk under the Held-Karp coins (N93).
    // Must not null tour (N50). startFog still must not null
    // tour (N17).
    host.$("stats").innerHTML = mazeStatsHtml(state, host);
    // Leftover Hunt / win status stays after Hunt. play()
    // rewrites #status (N48) only when it seats;
    // refreshTourStatus remints hunt status only when the
    // tour is feasible. An infeasible hunt skipped both, so
    // leftover "waypoint hunt" or leftover "reached the goal"
    // named the previous walk under the new coins (N106).
    // Must not null tour (N50). startFog still must not null
    // tour (N17).
    host.clearStatusFlash();
    host.$("status").textContent = state.session
        ? `session ${state.session.id.slice(0, 8)}… — arrow keys to move`
        : "arrow keys move once a session is open";
    if (!t.feasible) {
      host.log("err", "this maze has unreachable waypoints — tour not possible");
      return;
    }
    host.log("state", `waypoint hunt: collect ${t.waypoints.length} waypoints then reach the goal — `
        + `the optimal route is ${t.optimalCost} steps`
        + (t.path && t.path.length ? ` (${t.path.length} cells)` : ""));
    if (!state.session) await host.play();
    host.draw();
    refresh(state, host);
  }

  /** Ask the server how we are doing; it counts pickups from real moves, not our word for it. */
  async function refresh(state, host) {
    if (!state.tour || !state.session) return;
    const sessionId = state.session.id;
    const mazeId = state.maze && state.maze.id;
    try {
      const p = await host.api(`/session/${sessionId}/tour`);
      // Fog dropped the seat while this snapshot was out. Do not paint
      // hunt status onto the walk (N24). Generate + a new Play: the
      // GET would name the old hunt on the maze now on screen (N35).
      // state.tour stays on Fog — same maze.
      if (state.fog) return;
      if (!state.session) return;
      if (state.session.id !== sessionId) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      state.tourGot = state.tour.waypoints.filter(w => !p.remaining.some(r => same(r, w)));
      const left = p.total - p.collected;
      host.$("status").textContent = p.complete
          ? `all ${p.total} waypoints collected — reach the goal (${p.walked} steps so far, `
            + `optimal tour ${p.optimal})`
          : `waypoint hunt — ${p.collected}/${p.total} collected, ${left} to go `
            + `(${p.walked} steps, optimal tour ${p.optimal})`;
      host.draw();
      return p;
    } catch (e) {
      host.log("err", `tour status failed: ${e.message}`);
    }
  }

  /** Final verdict, once the goal is reached. */
  async function verdict(state, host) {
    const sessionId = state.session && state.session.id;
    const mazeId = state.maze && state.maze.id;
    const p = await refresh(state, host);
    if (!p) return "";
    if (state.fog) return "";
    if (!state.session) return "";
    if (state.session.id !== sessionId) return "";
    if (!state.maze || state.maze.id !== mazeId) return "";
    if (!p.complete) {
      const missed = p.total - p.collected;
      return ` — but ${missed} waypoint${missed === 1 ? "" : "s"} left uncollected, so that is `
          + `not a completed tour`;
    }
    const over = p.walked - p.optimal;
    return over <= 0
        ? ` — PERFECT TOUR: ${p.walked} steps, matching the optimal route exactly`
        : ` — tour complete in ${p.walked} steps; the optimal route is ${p.optimal} `
          + `(${over} step${over === 1 ? "" : "s"} over, `
          + `${(100 * p.walked / p.optimal).toFixed(0)}% of optimal)`;
  }

  global.DaedalusHunt = { start, refresh, verdict };
})(window);
