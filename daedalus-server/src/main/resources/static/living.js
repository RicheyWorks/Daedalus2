// SPDX-License-Identifier: MIT
// Living-maze leftover rules (ADR-006): bring to life, traffic, snapshot refresh.
// app.js owns leftover-state wiring; this file does not read leftover globals —
// it takes `state` plus a host bag.
"use strict";
(function (global) {
  /**
   * Ask the server to erode this maze in place. Progress arrives as MutationFrames on the
   * /state topic; without STOMP (CDN blocked / offline) we fall back to polling at the
   * server-reported tick interval, so the maze still visibly lives.
   */
  async function awaken(state, host) {
    if (host.refuseSpectatorWrite("bring the maze to life")) return;
    if (host.$("live").disabled) {
      host.log("err", "already alive — Harden only applies on the first Bring to life");
      return;
    }
    const harden = host.$("harden") && host.$("harden").checked;
    const mazeId = state.maze.id;
    const q = `/maze/${mazeId}/live?ticks=30` + (harden ? "&seal=0.08" : "");
    let r;
    try {
      r = await host.api(q, {method: "POST"});
    } catch (e) {
      const why = host.nameCapacity(e.message);
      if (why) {
        host.log("err", why);
        return;
      }
      throw e;
    }
    // Generate / Daily / Campaign / Breed replaced the maze while
    // this POST was out. Disabling #live and arming a poller would
    // bind the maze now on screen — the one that is gone. Fog stays:
    // living under fog is honest (N19 / Q2).
    if (!state.maze || state.maze.id !== mazeId) return;
    host.$("live").disabled = true;
    if (host.$("harden")) host.$("harden").disabled = true;
    host.log("state", `maze is alive — ${r.ticksRequested} ticks`
        + (harden ? " (eroding and hardening)" : " (erosion only)")
        + `, one every ${(r.tickMillis / 1000).toFixed(1)}s`);
    if (!state.stomp) host.startLivePolling(mazeId, r.tickMillis, r.ticksRequested);
  }

  /** Track congestion: everywhere you (or agents) walk gets expensive, then cools off. */
  async function simulate(state, host) {
    if (host.refuseSpectatorWrite("track traffic")) return;
    const mazeId = state.maze.id;
    let r;
    try {
      r = await host.api(`/maze/${mazeId}/traffic`, {method: "POST"});
    } catch (e) {
      const why = host.nameCapacity(e.message);
      if (why) {
        host.log("err", why);
        return;
      }
      throw e;
    }
    // Same steal as awaken: a late /traffic after Generate
    // must not disable #traffic or arm a poller for the maze now
    // on screen. Fog stays — traffic under fog is honest (Q2).
    if (!state.maze || state.maze.id !== mazeId) return;
    host.$("traffic").disabled = true;
    host.log("state", `traffic tracking on — walk around and watch the costs bloom `
        + `(pulse every ${(r.tickMillis / 1000).toFixed(1)}s)`);
    if (!state.stomp) pollTraffic(state, host, mazeId, r.tickMillis);
  }

  /** STOMP-less traffic fallback. CONNECT drops this (N44); disconnect re-arms (N45). */
  function pollTraffic(state, host, mazeId, tickMillis = 2000) {
    state.trafficTickMs = tickMillis;
    clearInterval(state.trafficPoll);
    state.trafficPoll = setInterval(async () => {
      if (state.stomp || !state.maze || state.maze.id !== mazeId) {
        clearInterval(state.trafficPoll); state.trafficPoll = null;
        return;
      }
      await refresh(state, host, true);
    }, tickMillis);
  }

  /** A traffic pulse arrived: costs moved — re-fetch, re-solve, redraw (same as mutation). */
  async function onPulse(state, host, m) {
    const mazeId = m.mazeId;
    if (!state.maze || state.maze.id !== mazeId) return;
    host.log("state", m.settled
        ? "traffic fully decayed — tracking retired"
        : `traffic: ${m.congestedCells} congested cell${m.congestedCells === 1 ? "" : "s"}, `
            + `peak cost ${m.peakCost.toFixed(1)}`);
    await refresh(state, host);
    if (!state.maze || state.maze.id !== mazeId) return;
    if (m.settled) host.$("traffic").disabled = false;
  }

  /** Swap in the latest snapshot without resetting session/solver state (unlike adoptMaze). */
  async function refresh(state, host, fromPoll) {
    try {
      const before = state.maze;
      // Which maze this refresh is FOR. Every await below is a window in which the player can
      // switch mazes (Daily, a campaign stage, Generate), and a response that lands after that
      // must be dropped rather than applied. Without this the poll's in-flight response
      // reinstates the maze the player just left: reproduced deterministically by delaying the
      // old maze's fetch and loading the daily challenge during it, which left state.maze on
      // the old maze under a "Daily leaderboard" heading — a session opened then would play a
      // different maze than the one being scored.
      const forMaze = state.maze.id;
      const stale = () => !state.maze || state.maze.id !== forMaze;

      // Fog is the agent contract: position, openings, goal. GET /maze is the
      // god-mode grid. Pulling it here would let a living tick paint rooms the
      // walk has never stood in (and openings behind you that you have not
      // re-seen). Re-poll the agent only; carveFogOpenings writes the cell
      // underfoot.
      if (state.fog) {
        const agentId = state.fog.agentId;
        try {
          const v = await host.api(`/agent/${agentId}`);
          // Play / Open session dropped the walk while this GET was
          // out. Maze id still matches (same maze), so stale() is
          // not enough — applyFogView would recreate state.fog on
          // the session walk. Same class as N26.
          if (stale()) return;
          if (!state.fog || state.fog.agentId !== agentId) return;
          if (fromPoll && state.stomp) return;
          host.applyFogView(v);
          host.draw();
          return;
        } catch (gone) {
          if (stale()) return;
          if (!state.fog || state.fog.agentId !== agentId) return;
          // Agent is gone. carveFogOpenings mutated tiles and living ticks
          // skipped GET /maze on purpose — fall through and refetch the live grid.
          state.fog = null;
          host.setGodModeEnabled(true);
          host.log("err", `fog walk ended: ${gone.message}`);
        }
      }

      const maze = await host.api(`/maze/${forMaze}`);
      // startFog can land while this snapshot is out. The fog path
      // skipped GET /maze on purpose; a late assign would write the
      // god-mode grid — unseen rooms and openings you have not
      // re-seen — into that walk. Discard, matching N18.
      if (stale() || state.fog) return;
      if (fromPoll && state.stomp) return;
      state.maze = maze;
      // Narrate on the polling path too. Tick/pulse messages normally come from STOMP frames,
      // so with the broker unreachable a living or congested maze changed under the player in
      // total silence — worst exactly where hazards matter most, the late campaign stages.
      if (!state.stomp && before && before.id === maze.id) {
        const walls = t => t.reduce((n, row) => n + (row.match(/#/g) || []).length, 0);
        const openedNow = walls(before.tiles) - walls(maze.tiles);
        const congestedNow = (maze.hotspots || []).length;
        const congestedBefore = (before.hotspots || []).length;
        if (openedNow > 0) {
          host.log("state", `erosion: ${openedNow} wall${openedNow === 1 ? "" : "s"} opened`);
        }
        if (congestedNow !== congestedBefore) {
          host.log("state", `traffic: ${congestedNow} congested cell${congestedNow === 1 ? "" : "s"}`);
        }
      }
      if (!(await host.refreshTheoryOverlays(forMaze, stale))) return;
      if (state.tour) {
        // Placement is frozen; the optimum is not (ADR-014). A seated
        // session — player or spectator — must rescore via
        // GET /session/{id}/tour. That read already reruns Held-Karp on
        // the live grid, and it is the public paint source. The old
        // body always asked GET /maze/{id}/tour (tourFor): auth-required
        // in prod, and it can mint. Spectator hydrate already used the
        // session read; a living tick then 401'd and kept a stale
        // optimum on the watched hunt (N42). Maze tour is only the
        // Hunt-before-Play fallback, when no seat exists to progress.
        try {
          if (state.session) {
            const sessionId = state.session.id;
            const p = await host.api(`/session/${sessionId}/tour`);
            if (stale() || state.fog) return;
            if (!state.session || state.session.id !== sessionId) return;
            if (p.optimal !== state.tour.optimalCost) {
              host.log("state", `tour optimum is now ${p.optimal} steps (was ${state.tour.optimalCost})`);
            }
            state.tour = {
              waypoints: p.waypoints,
              path: p.path || [],
              optimalCost: p.optimal,
              feasible: true,
            };
          } else {
            const t = await host.api(`/maze/${forMaze}/tour?count=${state.tour.waypoints.length}`);
            if (stale() || state.fog) return;
            if (t.optimalCost !== state.tour.optimalCost) {
              host.log("state", `tour optimum is now ${t.optimalCost} steps (was ${state.tour.optimalCost})`);
            }
            state.tour = t;
          }
          await host.refreshTourStatus();
          if (stale() || state.fog) return;
        } catch (ignored) { /* tour overlay; losing one refresh is harmless */ }
      }
      if (state.path) {
        // The drawn route may now cross freshly-opened walls or stale costs — re-solve
        // quietly (no replay animation; the mutation itself is the show).
        const r = await host.api(`/maze/${forMaze}/solve/${host.$("solver").value}`, {method: "POST"});
        if (stale() || state.fog) return;
        state.path = r.path;
        state.expansions = [];
        state.searchProgress = 1;
        state.pathProgress = 1;
      }
      host.draw();
    } catch (e) {
      host.log("err", `living refresh failed: ${e.message}`);
    }
  }

  global.DaedalusLiving = {awaken, simulate, pollTraffic, onPulse, refresh};
})(window);
