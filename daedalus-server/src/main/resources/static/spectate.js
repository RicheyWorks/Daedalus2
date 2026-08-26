// SPDX-License-Identifier: MIT
// Spectate / hash leftover rules. app.js owns leftover-state wiring; this
// file does not read leftover globals — it takes `state` plus a host bag.
"use strict";
(function (global) {
  function same(a, b) { return a && b && a.row === b.row && a.col === b.col; }

  function applyRecipe(state, host, h) {
    if (h.g && host.$("generator") && [...host.$("generator").options].some(o => o.value === h.g)) {
      host.$("generator").value = h.g;
      host.updateInfo();
    }
    if (h.rows) host.$("rows").value = h.rows;
    if (h.cols) host.$("cols").value = h.cols;
    if (h.seed != null && h.seed !== "") host.$("seed").value = h.seed;
    if (host.$("braid")) {
      const v = h.braid && +h.braid > 0 ? String(h.braid) : "0";
      if (![...host.$("braid").options].some(o => o.value === v)) {
        const o = document.createElement("option");
        o.value = v;
        o.textContent = v + " — from permalink";
        host.$("braid").appendChild(o);
      }
      host.$("braid").value = v;
      host.syncBraid("braid");
    }
    if (host.$("hotspots")) host.$("hotspots").value = h.hotspots || "0";
    // Permalink without cost= left leftover #hotspotCost from
    // the previous recipe (N123). Catalog default matches leaveMaze.
    if (host.$("hotspotCost")) host.$("hotspotCost").value = h.cost || 25;
  }

  async function rebuild(state, host, h) {
    applyRecipe(state, host, h);
    await host.generate();
  }

  function permalink(state, host) {
    // Campaign and daily keep the ladder / shared board. Everything else with a
    // session — generate+play, spectate, join-from-spectate — is #session=.
    // readOnly used to be the only way to get that hash, so Open session left
    // #maze= in the bar and joining a spectate dropped the permalink you arrived on.
    if (state.campaign && state.stageIndex != null) {
      // Stage 0 stays `#campaign=SEED` so old links still hydrate. Later rungs
      // extend the same token (`#campaign=SEED:N`) — not a second kind.
      return {campaign: state.stageIndex > 0
          ? state.campaign.seed + ":" + state.stageIndex
          : String(state.campaign.seed)};
    }
    if (state.dailyId && state.maze && state.maze.id === state.dailyId) return {daily: true};
    if (state.session) return {session: state.session.id};
    if (state.maze) return {maze: state.maze.id};
    const g = host.$("lbGen") && host.$("lbGen").value;
    if (g) return {generator: g};
    return {};
  }

  function pin(state, host) {
    const p = permalink(state, host);
    // playStage restores stageIndex before pinning, so that write stays
    // #campaign= and the ladder lives. Generate / Daily / Breed (and any
    // sibling that pins maze / daily / session) must drop it — adoptMaze
    // only nulls stageIndex, and a matching hash makes loadFromHash no-op.
    if (p.campaign == null) host.leaveCampaign();
    let next = "";
    if (p.session) next = "session=" + p.session;
    else if (p.campaign != null) next = "campaign=" + p.campaign;
    else if (p.daily) next = "daily";
    else if (p.maze) next = ["maze=" + p.maze].concat(DaedalusShare.mazeRecipe(state.maze)).join("&");
    else if (p.generator) next = "generator=" + encodeURIComponent(p.generator);
    const want = next ? "#" + next : "";
    if (location.hash !== want) location.hash = next;
  }

  /**
   * True when the bar already names what the canvas is showing. pinHash's
   * write fires hashchange; that must not re-fetch / re-adopt / remint.
   */
  function showsCurrent(state, host) {
    const h = DaedalusShare.readHash(location.hash);
    const p = permalink(state, host);
    if (h.session) return p.session === h.session;
    if (h.campaign != null && h.campaign !== "") return p.campaign === String(h.campaign);
    if (h.daily) return !!p.daily;
    if (h.maze) return p.maze === h.maze;
    if (h.generator) return p.generator === h.generator;
    return !p.session && p.campaign == null && !p.daily && !p.maze && !p.generator;
  }

  function armWrites(state, host, on) {
    ["live", "traffic", "tour"].forEach(id => {
      const el = host.$(id);
      if (el) el.disabled = !on;
    });
    if (host.$("harden")) host.$("harden").disabled = !on;
  }

  function refuseWrite(state, host, what) {
    if (!state.readOnly) return false;
    host.log("err", "spectating is read-only — join this session to " + what);
    return true;
  }

  /**
   * Open session, Generate, Fog, Daily, Campaign, Breed, Solve overlays, and
   * join-from-spectate leave watch mode before they write. play() used to mint
   * a session and leave readOnly set, so the status line said "arrow keys to
   * move" and both inputs no-op'd. Generate replaced the maze and Fog POSTed
   * an agent walk while still watching. Daily / Campaign / Breed fetched, then
   * adoptMaze cleared readOnly as a side effect. Solve painted a god-mode
   * overlay on the watched maze. Live / traffic / tour mutate the maze
   * underfoot and must not stay armed on a #session= hydrate.
   */
  function leaveWatch(state, host) {
    const wasWatching = state.readOnly;
    state.readOnly = false;
    clearInterval(state.spectatePoll);
    state.spectatePoll = null;
    armWrites(state, host, true);
    // Join-from-spectate sets the seat before this call and
    // keeps the session. Solve / Analyze after watch used to
    // keep the opener's session writable — arrows POSTed
    // /move on a walk this tab only watched (N51).
    if (!wasWatching || state.seat) return;
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    state.session = null;
    // Spectated hunt stayed after the seat drop. Solve / Fog
    // then Play scored a new walk against leftover waypoints,
    // and a living tick asked tourFor with no seat (N56).
    // startFog still must not null tour (N17).
    state.tour = null;
    state.tourGot = [];
    state.joined = null;
    state.trails = {};
    state.won = null;
    // Leftover spectate status stays after the seat drop.
    // Generate / Fog / Play rewrite #status (N48). Solve /
    // Hardest / Race / Compare rewrite after leaving a
    // watch (N101–N104). Analyze / Identify / heat /
    // sanctuaries / lens call leaveSpectate and left
    // leftover "spectating session… — read-only" naming a
    // watch that is gone under the cuts (N105). Join-from-
    // spectate sets the seat first and keeps the session —
    // do not rewrite. startFog still must not null tour
    // (N17) except this leave-watch path (N56).
    host.clearStatusFlash();
    host.$("status").textContent = "arrow keys move once a session is open";
    host.$("join").disabled = true;
    host.$("join").textContent = "Join as second player";
    host.$("join").title = "Requires daedalus.session.multiplayer=true";
    host.resubscribe();
    // The bar still said #session= after the seat drop. Refresh
    // reminted a watch this tab already left (N52). Pin the maze
    // that stayed. leaveMaze nulls maze first so this does not
    // fight History.
    if (state.maze) pin(state, host);
  }

  /**
   * Drop the canvas maze so a hash that names no maze cannot keep showing one.
   * Back onto "" or #generator= used to leave the previous maze (and its daily
   * / session seat) on screen after N10 re-hydrated maze-to-maze. Does not pin
   * — rewriting the bar would fight History.
   */
  function leave(state, host) {
    clearInterval(state.livePoll); state.livePoll = null;
    clearInterval(state.trafficPoll); state.trafficPoll = null;
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    host.bumpAnim();
    // Null the maze before leaveSpectate. N52 pins #maze= when
    // a watch leave keeps the canvas; writing that here would
    // fight History (Back onto "" / #generator=).
    state.maze = null;
    leaveWatch(state, host);
    state.path = null;
    state.session = null;
    state.seat = null;
    state.joined = null;
    state.trails = {};
    state.won = null;
    state.expansions = [];
    state.searchProgress = 1;
    state.pathProgress = 1;
    state.fog = null;
    state.race = null;
    state.dailyId = null;
    state.analysis = null;
    state.ghost = null;
    state.hardest = null;
    state.field = null;
    state.sanctuaries = null;
    state.lens = null;
    state.fingerprint = null;
    state.tour = null;
    state.tourGot = [];
    state.caption = null;
    state.prevMazeId = null;
    state.stageIndex = null;
    host.$("breed").disabled = true;
    host.$("play").disabled = true;
    host.$("join").disabled = true;
    host.$("join").textContent = "Join as second player";
    host.$("join").title = "Requires daedalus.session.multiplayer=true";
    host.$("live").disabled = true;
    host.$("traffic").disabled = true;
    if (host.$("harden")) host.$("harden").disabled = true;
    host.$("fog").disabled = true;
    host.setGodModeEnabled(false);
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    host.$("compareBox").innerHTML = "";
    host.clearStatusFlash();
    host.$("status").textContent = "no maze yet";
    host.$("stats").innerHTML = "";
    host.$("pngExport").style.display = "none";
    // adoptMaze wrote the snapshot into the form. Back onto "" /
    // #generator= dropped the canvas and left that recipe, so
    // Generate rebuilt the maze the bar no longer names (N54).
    // Catalog defaults match the inputs. #generator= overwrites
    // the select after this. Do not pin.
    if (host.$("rows")) host.$("rows").value = 21;
    if (host.$("cols")) host.$("cols").value = 31;
    if (host.$("seed")) host.$("seed").value = "";
    if (host.$("hotspots")) host.$("hotspots").value = 0;
    if (host.$("hotspotCost")) host.$("hotspotCost").value = 25;
    if (host.$("braid")) {
      host.$("braid").value = "0";
      host.syncBraid("braid");
    }
    if (host.$("generator")
        && [...host.$("generator").options].some(o => o.value === "recursive-backtracker")) {
      host.$("generator").value = "recursive-backtracker";
      host.updateInfo();
    }
    host.resubscribe();
    host.refreshLeaderboard();
    host.drawEmpty();
  }

  /**
   * Install a session snapshot: positions, opening player, and the recorded walk.
   * Frames only carry the next hop; without the trail a late spectator paints a
   * marker and no corridor.
   */
  function adoptView(state, host, view) {
    const primary = view.player || Object.keys(view.players)[0];
    state.session = {id: view.sessionId, positions: view.players, primary};
    if (view.completed) state.won = primary;
    const start = DaedalusShare.startFromTiles(state.maze && state.maze.tiles);
    const walks = Object.assign({}, view.walks || {});
    if (view.trail && !walks[primary]) walks[primary] = view.trail;
    Object.keys(view.players || {}).forEach(name => {
      state.trails[name] = DaedalusShare.walkFromMoves(start, walks[name] || []);
    });
  }

  /**
   * Overlays the player already turned on — a hunt, a ghost — without minting them.
   * GET /session/{id}/tour is a read (404 if nobody asked /maze/{id}/tour). Ghost 404
   * is "no finished run yet".
   */
  async function hydrate(state, host, view) {
    const sessionId = view.sessionId;
    const mazeId = view.mazeId;
    try {
      const p = await host.api(`/session/${sessionId}/tour`);
      // Progress carries the coins and the Held-Karp path. GET /maze/{id}/tour
      // is auth-required in prod and would 401 here; it is also what freezes
      // coins, which a spectator GET must not do.
      // Generate / Fog / a new #session= while this GET was out would
      // paint the old hunt onto the maze now on screen. Discard — same
      // class as N31. startFog still must not null tour (N17).
      if (state.fog) return;
      if (!state.session || state.session.id !== sessionId) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      if (p.waypoints && p.waypoints.length) {
        state.tour = {
          waypoints: p.waypoints,
          path: p.path || [],
          optimalCost: p.optimal,
          feasible: true,
        };
        state.tourGot = p.waypoints.filter(w => !(p.remaining || []).some(r => same(r, w)));
        host.log("state", `spectating a waypoint hunt — ${p.collected}/${p.total} collected`);
      }
    } catch (ignored) { /* no tour minted; do not create one */ }
    if (state.fog) return;
    if (!state.session || state.session.id !== sessionId) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    await host.summonGhost();
  }

  /**
   * STOMP-less spectator fallback. CONNECT drops this (N43); a later
   * disconnect must re-arm it or a watched walk freezes (N45).
   */
  function startPolling(state, host) {
    if (state.stomp || !state.readOnly || !state.session) return;
    clearInterval(state.spectatePoll);
    state.spectatePoll = setInterval(async () => {
      if (!state.readOnly || !state.session) {
        clearInterval(state.spectatePoll); state.spectatePoll = null;
        return;
      }
      // Broker arrived after this fallback was armed. Frames own
      // the walk; keep polling and a late snapshot rewinds a hop
      // STOMP already applied (N43).
      if (state.stomp) {
        clearInterval(state.spectatePoll); state.spectatePoll = null;
        return;
      }
      const sessionId = state.session.id;
      const mazeId = state.maze && state.maze.id;
      try {
        const view = await host.api(`/session/${sessionId}`);
        // Generate / Fog / a new #session= while this GET was out
        // would re-seat the old walk onto the maze now on screen.
        // Discard — same class as N33. startFog still must not
        // null tour (N17).
        if (state.fog) return;
        if (state.stomp) {
          clearInterval(state.spectatePoll); state.spectatePoll = null;
          return;
        }
        if (!state.session || state.session.id !== sessionId) return;
        if (!state.maze || state.maze.id !== mazeId) return;
        adoptView(state, host, view);
        host.draw();
      } catch (gone) {
        if (state.fog) return;
        if (state.stomp) {
          clearInterval(state.spectatePoll); state.spectatePoll = null;
          return;
        }
        if (!state.session || state.session.id !== sessionId) return;
        if (!state.maze || state.maze.id !== mazeId) return;
        clearInterval(state.spectatePoll); state.spectatePoll = null;
        host.log("err", "spectated session ended (evicted)");
      }
    }, 1000);
  }

  /**
   * Watch someone else's session, read-only: load the snapshot, then follow the same
   * /topic/session/{id}/player frames the players produce (or poll when STOMP is absent).
   * Owned sessions keep their per-destination STOMP authorization — a spectator can only
   * follow what the broker lets them subscribe to. "Join this session" POSTs /join and
   * drops read-only so a second client can play; an authenticated join also grants the
   * player topic (ADR-012).
   */
  async function watch(state, host, sessionId) {
    // #session= hydrate is a leave-fog path — the bar already named the
    // session. Leave before the fetch; a Fog that starts mid-flight still
    // hits adoptMaze's discard, and must not adoptSessionView after that.
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    // Generate mid-flight: a late #session= would adopt over the maze
    // now on screen (N41). Capture maze id (or none); skip adoptMaze /
    // adoptSessionView when fog is on or the canvas id no longer
    // matches. Fog discard stays (N22). Stay until join lands.
    const mazeId = state.maze && state.maze.id;
    let view;
    try { view = await host.api(`/session/${sessionId}`); }
    catch (e) { host.log("err", host.nameGone(e.message) || e.message); return; }
    if (state.fog) return;
    if (state.maze && state.maze.id !== mazeId) return;
    if (!state.maze && mazeId) return;
    try {
      const maze = await host.api(`/maze/${view.mazeId}`);
      if (state.fog) return;
      if (state.maze && state.maze.id !== mazeId) return;
      if (!state.maze && mazeId) return;
      host.adoptMaze(maze, null, "spectated session");
    } catch (e) {
      // Session still open, maze idle-TTL evicted — do not dump the status line.
      host.log("err", host.nameGone(e.message) || e.message);
      return;
    }
    if (state.fog) return;
    adoptView(state, host, view);
    state.readOnly = true;
    armWrites(state, host, false);
    pin(state, host);
    host.$("status").textContent = `spectating session ${view.sessionId.slice(0, 8)}… — read-only`;
    host.$("join").disabled = false;
    host.$("join").textContent = "Join this session";
    host.$("join").title = "Join as the name in the player field (needs daedalus.session.multiplayer)";
    host.log("state", `spectating ${Object.keys(view.players).join(", ")} — moves arrive live`);
    await hydrate(state, host, view);
    host.resubscribe();
    if (!state.stomp) startPolling(state, host);
    host.draw();
  }

  /**
   * #session=, #campaign=, #daily, #maze= or #generator=: restore the view that hash names.
   * Boot and hashchange share this path. The same-hash guard stops pinHash's write
   * from looping — Back/Forward (and a pasted hash after boot) still hydrate.
   * A matching campaign hash keeps the ladder; any other permalink (or a
   * different campaign id) drops it so a leftover stage cannot play.
   * `#campaign=SEED:N` hydrates that rung; a missing stage token is stage 0.
   * A hash with no maze kind drops the leftover maze (N14).
   * A different maze / session / daily / campaign is a leave-fog path:
   * Back / paste / Forward already wrote the bar, and adoptMaze used to
   * no-op during fog without saying why, so the bar named a maze the
   * canvas still walked. Leave before the fetch (same as N20 / N21).
   * Same-hash still no-ops above and does not remint.
   */
  async function load(state, host) {
    if (showsCurrent(state, host)) return;
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    const h = DaedalusShare.readHash(location.hash);
    const named = DaedalusShare.campaignToken(h);
    if (!named || !state.campaign || String(state.campaign.seed) !== String(named.seed)) {
      host.leaveCampaign();
    }
    if (h.session) { await watch(state, host, h.session); return; }
    if (named) {
      try {
        if (state.campaign && String(state.campaign.seed) === String(named.seed)) {
          const index = named.stage < state.campaign.stages.length ? named.stage : 0;
          await host.playStage(index);
        } else {
          await host.loadCampaign(Number(named.seed), named.stage);
        }
      } catch (e) { host.log("err", `campaign permalink failed (${e.message})`); }
      return;
    }
    if (h.daily) {
      try { await host.loadDaily(); }
      catch (e) { host.log("err", `daily permalink failed (${e.message})`); }
      return;
    }
    if (h.maze) {
      // Generate mid-flight: a late #maze= would adopt over the maze
      // now on screen (N40). Capture maze id (or none); discard after
      // the GET (and a recipe rebuild) when the canvas id changed.
      // Fog discard stays (N22).
      const mazeId = state.maze && state.maze.id;
      try {
        const maze = await host.api(`/maze/${h.maze}`);
        if (state.fog) return;
        if (state.maze && state.maze.id !== mazeId) return;
        if (!state.maze && mazeId) return;
        host.adoptMaze(maze, null);
        pin(state, host);
        host.log("state", "loaded maze from permalink");
      } catch (e) {
        if (h.g && h.seed != null && h.seed !== "" && h.rows && h.cols) {
          try {
            if (state.fog) return;
            if (state.maze && state.maze.id !== mazeId) return;
            if (!state.maze && mazeId) return;
            await rebuild(state, host, h);
            host.log("state", "permalink maze aged out — rebuilt from the recipe");
            return;
          } catch (rebuildErr) {
            // maze-capacity is a full cache, not a missing maze. Swallowing it
            // as 404 made a refused remint look like the recipe was gone.
            host.log("err", host.permalinkLoadFailed(e, rebuildErr));
            return;
          }
        }
        host.log("err", host.permalinkLoadFailed(e, null));
      }
      return;
    }
    // "" and #generator= name no maze. N10 re-hydrated maze-to-maze and left
    // the previous maze here — daily / session / canvas leftovers the bar
    // no longer names. Drop them before the generator select so the board
    // cannot stay maze-scoped.
    leave(state, host);
    if (h.generator) {
      if (host.$("lbGen") && [...host.$("lbGen").options].some(o => o.value === h.generator)) {
        host.$("lbGen").value = h.generator;
        await host.refreshLeaderboard();
      }
      // The hash named an algorithm, not just a leaderboard partition.
      if (host.$("generator") && [...host.$("generator").options].some(o => o.value === h.generator)) {
        host.$("generator").value = h.generator;
        host.updateInfo();
      }
    }
  }

  global.DaedalusSpectate = {
    applyRecipe, rebuild, permalink, pin, showsCurrent,
    leaveWatch, armWrites, refuseWrite, leave, load,
    watch, startPolling, adoptView, hydrate,
  };
})(window);
