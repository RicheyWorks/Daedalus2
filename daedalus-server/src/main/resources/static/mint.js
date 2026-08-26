// SPDX-License-Identifier: MIT
// Maze mint leftover rules. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  function applySpots(state, host, maze) {
    const hs = (maze && maze.hotspots) || [];
    if (host.$("hotspots")) host.$("hotspots").value = hs.length;
    // Daily / Generate / #maze= reminted count and left leftover
    // spot cost from the previous recipe, so Generate of a
    // no-spot maze still billed leftover cost when spots were
    // later asked for (N123). Catalog default matches leaveMaze.
    if (host.$("hotspotCost")) host.$("hotspotCost").value = hs.length ? hs[0].cost : 25;
  }

  /** The maze's echoed factor owns the selects. A leftover 0.8 on Generate
   *  used to label Daily and a #maze= permalink as braided. */
  function applyBraid(state, host, maze) {
    const v = maze && maze.braid > 0 ? String(maze.braid) : "0";
    const el = host.$("braid");
    if (!el) return;
    if (![...el.options].some(o => o.value === v)) {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v + " — from maze";
      el.appendChild(o);
    }
    el.value = v;
    host.syncBraid("braid");
  }

  /**
   * Install a maze into the UI — from a fresh generate, a #maze=<id> permalink, or the daily.
   */
  function adopt(state, host, maze, roundTripMs, sourceLabel) {
    // A Fog that started while Generate / Daily / Campaign / Breed was
    // already out must keep the walk. Callers leave fog before they
    // fetch; this discard is the late-arrival gate.
    if (state.fog) return;
    if (state.maze && state.maze.id !== maze.id) {
      state.prevMazeId = state.maze.id; // remember the other parent for crossbreeding
    }
    host.$("breed").disabled = !state.prevMazeId;
    // Mirror the adopted maze into the inputs. Size/braid/hotspots already
    // followed the snapshot; generator and seed did not. A #maze= (or Daily /
    // campaign / #session=) success path wrote g= and seed= into the hash from
    // the maze, then Generate / Measure / tournament still read the leftover
    // selects — half-hydrated: the bar named one recipe, the form another.
    host.$("rows").value = maze.rows; host.$("cols").value = maze.cols;
    if (host.$("seed") && maze.seed != null) host.$("seed").value = maze.seed;
    if (host.$("generator") && maze.generatorId
        && [...host.$("generator").options].some(o => o.value === maze.generatorId)) {
      host.$("generator").value = maze.generatorId;
      host.updateInfo();
    }
    applyBraid(state, host, maze);
    applySpots(state, host, maze);
    state.readOnly = false;
    clearInterval(state.spectatePoll); state.spectatePoll = null;
    state.maze = maze; state.path = null; state.session = null;
    state.seat = null; state.joined = null; state.trails = {}; state.won = null;
    state.expansions = []; state.searchProgress = 1; state.pathProgress = 1;
    host.$("play").disabled = false;
    host.$("join").disabled = true;
    host.$("join").textContent = "Join as second player";
    host.$("join").title = "Requires daedalus.session.multiplayer=true";
    host.$("live").disabled = false; host.$("traffic").disabled = false;
    if (host.$("harden")) host.$("harden").disabled = false;
    host.$("fog").disabled = false;
    host.setGodModeEnabled(true);
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    state.fog = null;
    clearInterval(state.livePoll); state.livePoll = null;
    clearInterval(state.trafficPoll); state.trafficPoll = null;
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    // Solve / race rAF captured the previous reveal. Generate would
    // zero path / race, then a leftover frame write progress or
    // raceSummary onto the maze now on screen (N49).
    host.bumpAnim();
    state.race = null; state.dailyId = null; state.analysis = null; state.ghost = null;
    state.hardest = null; state.field = null; state.sanctuaries = null;
    state.lens = null;
    state.fingerprint = null;
    state.tour = null; state.tourGot = [];
    state.caption = null;
    state.stageIndex = null; // playStage re-sets this after adopting the stage's maze
    host.$("compareBox").innerHTML = "";
    // Wall-block flash captured the previous status. Generate /
    // Daily / permalink writes a new line; 900ms later the leftover
    // restore put the old session / hunt text on a maze that no
    // longer has that seat (N48).
    host.clearStatusFlash();
    host.$("status").textContent = DaedalusCaption.sessionStatus(null);
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(maze, host.esc)
        + (roundTripMs != null
            ? `<span>round-trip</span> ${roundTripMs.toFixed(0)} ms<br>`
            : `<span>loaded from</span> ${sourceLabel || "permalink"}<br>`);
    host.resubscribe();
    host.refreshLeaderboard(); // re-scope: global board unless loadDaily re-marks this maze as daily
    host.draw();
    host.$("pngExport").style.display = "inline";
  }

  async function mint(state, host, opts) {
    host.leaveSpectate();
    // Generate stays armed during fog — it is a leave-fog path. Drop the
    // walk before the fetch (leaveSpectate-before-write). adoptMaze used
    // to always replace the maze, so a generate that was already out
    // still stole the canvas after Fog started mid-flight.
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    const braid = opts && opts.braid != null ? +opts.braid : +((host.$("braid") && host.$("braid").value) || 0);
    let seed = host.$("seed").value === "" ? null : +host.$("seed").value;
    if (seed == null || Number.isNaN(seed)) {
      // An empty seed used to be server nanoTime plus Math.random spots — same
      // count could not be rebuilt. Pick a seed here so the request is a recipe.
      seed = Math.floor(Math.random() * 0x7fffffff);
      host.$("seed").value = seed;
    }
    const body = {
      generatorId: host.$("generator").value,
      rows: +host.$("rows").value, cols: +host.$("cols").value,
      seed,
    };
    if (braid > 0) body.braid = braid;
    const spotCount = Math.min(64, Math.max(0, +host.$("hotspots").value || 0));
    if (spotCount > 0) {
      const cost = Math.min(1000, Math.max(1, +host.$("hotspotCost").value || 25));
      body.hotspots = DaedalusShare.placeSpots(body.rows, body.cols, spotCount, seed, cost);
    }
    const t0 = performance.now();
    const maze = await host.api("/maze/generate", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
    });
    if (state.fog) return;
    adopt(state, host, maze, performance.now() - t0);
    host.pinHash();
  }

  /** The shared daily challenge — same maze for everyone until midnight UTC (ADR-006). */
  async function daily(state, host) {
    host.leaveSpectate();
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    // Generate mid-flight: a late Daily would adopt over the maze
    // now on screen (N40). Capture maze id (or none); discard after
    // the GET when fog is on or the canvas id no longer matches.
    // Fog discard stays (N21).
    const mazeId = state.maze && state.maze.id;
    const d = await host.api("/maze/daily");
    if (state.fog) return;
    if (state.maze && state.maze.id !== mazeId) return;
    if (!state.maze && mazeId) return;
    adopt(state, host, d.maze, null, `daily challenge ${d.date}`);
    state.dailyId = d.maze.id; // after adoptMaze (which clears it) — scopes the leaderboard
    host.pinHash();
    host.refreshLeaderboard();
    host.log("state", `daily challenge ${d.date} — the whole world plays this maze today`);
  }

  /** Cross the current maze with the previous one — the child replaces the current maze. */
  async function breed(state, host) {
    host.leaveSpectate();
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    // Generate mid-flight: a late Breed would adopt over the maze
    // now on screen (N40). Capture maze id (or none); discard after
    // the POST when fog is on or the canvas id no longer matches.
    // Fog discard stays (N21).
    const mazeId = state.maze && state.maze.id;
    const child = await host.api(`/maze/breed?a=${state.prevMazeId}&b=${state.maze.id}`,
        {method: "POST"});
    if (state.fog) return;
    if (state.maze && state.maze.id !== mazeId) return;
    if (!state.maze && mazeId) return;
    adopt(state, host, child, null, "crossbreeding");
    host.pinHash();
    host.log("state", "bred a child of the last two mazes — patches of both, repaired to one "
        + "connected maze (breed again to keep the lineage going)");
  }

  global.DaedalusMint = {applySpots, applyBraid, adopt, mint, daily, breed};
})(window);
