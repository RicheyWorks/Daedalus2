// SPDX-License-Identifier: MIT
// Fog-walk leftover rules. Memory merge lives in fog.js; this file does not read `state`.
"use strict";
(function (global) {
  function applyView(state, view) {
    state.fog = DaedalusFog.mergeView(state.fog, view);
    carveOpenings(state, view);
  }

  /**
   * The agent reports openings at the cell underfoot, not a grid. Write those four
   * gap tiles into memory so a living tick that opens a wall at your feet is
   * visible, without fetching GET /maze (that would paint rooms you have not
   * stood in).
   */
  function carveOpenings(state, view) {
    if (!state.maze) return;
    state.maze.tiles = DaedalusFog.carveTiles(state.maze.tiles, view);
  }

  async function start(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const sessionId = state.session && state.session.id;
    const view = await host.api(`/maze/${mazeId}/agent`, {method: "POST"});
    // Generate / Daily / Back replaced the maze while this mint was
    // out. Applying would walk fog on a grid this agent was not
    // minted for, and carve its openings into those tiles.
    if (!state.maze || state.maze.id !== mazeId) return;
    // Play on the same maze seats a session; maze id still matches
    // (N26), so a late mint would drop the new seat and re-arm
    // fog on the play walk. Same class as N38. Discard when a
    // session is seated that was not the one we started with —
    // Fog still drops a seat that was already there (leave-session
    // path).
    if (state.session && state.session.id !== sessionId) return;
    state.session = null;
    state.seat = null;
    state.joined = null;
    // Leftover trails stay after Fog. Generate / leave-watch /
    // leaveMaze / Play drop leftover crumbs. Fog dropped the
    // seat and leftover ghost (N15) but left leftover trails,
    // so leftover crumbs painted after a living tick ended
    // the fog walk without Play (N109). startFog still must
    // not null tour (N17).
    state.trails = {};
    // Leftover won stays after Fog. Generate / leave-watch /
    // leaveMaze / Play drop leftover won. Fog dropped the
    // seat and leftover trails (N109) but left leftover won,
    // so leftover victory ring painted after a living tick
    // ended the fog walk without Play (N110). startFog still
    // must not null tour (N17).
    state.won = null;
    // Leftover tourGot stays after Fog. Hunt remints collected
    // coins. Fog dropped the seat and leftover won (N110) but
    // left leftover tourGot, so leftover collected coins
    // painted after Play seated a new walk (draw swallows
    // during fog). Drop those coins after the maze-id discard
    // (N117). startFog still must not null tour (N17).
    state.tourGot = [];
    host.$("join").disabled = true;
    // Open session pinned #session= and subscribed /player. N15 dropped the
    // seat and hash; the subscription and ghost ticker stayed, so a joiner
    // frame still logged a session move and the ghost still advanced —
    // draw() returned early, so it did not paint, while the canvas walked
    // fog. resubscribe / ghost clear after the null, same as adoptMaze.
    // Pin after the drop — daily / campaign stay those kinds; a leftover
    // #session= becomes #maze=.
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    host.bumpAnim();
    state.ghost = null;
    state.path = null; state.expansions = [];
    state.analysis = null; state.hardest = null; state.field = null;
    state.lens = null; state.race = null; state.sanctuaries = null;
    state.fingerprint = null;
    state.caption = null;
    // Analyze / Compare / Identify write #compareBox. Fog already drops
    // those overlay objects (and hides ASCII); the sidebar stayed, so a
    // leftover caption still named chokepoints during the walk, and a
    // leftover compare table could hover-arm a solve path draw() swallowed
    // until Play. Empty it after the drop, same as adoptMaze.
    // state.tour stays: draw() returns early, refreshTourStatus needs the
    // seat N16 dropped, and Play / a living fall-through still belong to
    // this maze.
    host.$("compareBox").innerHTML = "";
    state.fog = {seen: new Set()};
    applyView(state, view);
    host.setGodModeEnabled(false);
    host.$("asciiOut").hidden = true;
    // Leftover Solve stats stay after Fog. Play / Hunt /
    // Join rewrite #stats (N92–N94). Fog did not, so leftover
    // solver numbers named the previous walk under the fog
    // walk (N95). startFog still must not null tour (N17).
    host.$("stats").innerHTML =
        `<span>maze</span> ${host.esc(state.maze.id.slice(0, 8))}&hellip;<br>`
        + `<span>by</span> ${host.esc(state.maze.generatorId)} &middot; ${state.maze.rows}&times;${state.maze.cols} `
        + `&middot; <span>seed</span> ${state.maze.seed}`
        + (state.maze.braid > 0 ? ` &middot; braided ${state.maze.braid}` : "")
        + `<br>`;
    host.clearStatusFlash();
    host.$("status").textContent = `fog: ${view.stepsRemaining} steps left — arrows walk the agent`;
    host.log("state", `fog of war — agent ${String(view.agentId).slice(0, 8)}… sees `
        + (view.open && view.open.length ? view.open.join(", ") : "no openings"));
    host.pinHash();
    host.resubscribe();
    host.draw();
  }

  async function step(state, host, dr, dc) {
    if (!state.fog || state.fog.arrived || state.fog.expired) return;
    const dir = DaedalusFog.dirFromDelta(dr, dc);
    if (!dir) return;
    if (!state.fog.open.includes(dir)) {
      host.log("err", `no opening ${dir}`);
      return;
    }
    const agentId = state.fog.agentId;
    const view = await host.api(`/agent/${agentId}/step?direction=${dir}`, {method: "POST"});
    // Generate / Play dropped the walk while this step was out.
    // applyFogView used to recreate state.fog and carve the old
    // openings into the maze now on screen.
    if (!state.fog || state.fog.agentId !== agentId) return;
    applyView(state, view);
    if (view.arrived) {
      host.$("status").textContent = `arrived in ${view.stepsUsed} steps`;
      host.log("state", `fog: arrived in ${view.stepsUsed} steps`);
    } else if (view.expired) {
      host.$("status").textContent = "budget exhausted — open a new fog walk";
      host.log("err", "fog: step budget exhausted");
    } else {
      host.$("status").textContent = `fog: ${view.stepsRemaining} steps left · ${view.open.join(", ")}`;
    }
    host.draw();
  }

  global.DaedalusFogWalk = {applyView, carveOpenings, start, step};
})(window);
