// SPDX-License-Identifier: MIT
// STOMP subscribe, broker-down polls, and mutation apply.
// app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  let stompWarned = false;
  let stompGen = 0;

  function connect(state, host) {
    if (typeof Stomp === "undefined" || typeof SockJS === "undefined") {
      // CDN unreachable (offline / blocked network). Everything REST-driven still works;
      // only the live-frames panel degrades. Say so once, quietly, instead of leaking a
      // ReferenceError into the log.
      if (!stompWarned) {
        stompWarned = true;
        host.log("state", "live frames unavailable (STOMP libraries did not load) — "
            + "generate, solve, and play still work");
      }
      return;
    }
    const gen = ++stompGen;
    if (state.stomp) {
      try { state.stomp.disconnect(); } catch (ignored) {}
      state.stomp = null;
    }
    const client = Stomp.over(new SockJS("/ws"));
    client.debug = null;
    const headers = {};
    if (state.token) headers.Authorization = "Bearer " + state.token;
    client.connect(headers, () => {
      if (gen !== stompGen) {
        try { client.disconnect(); } catch (ignored) {}
        return;
      }
      state.stomp = client;
      host.log("state", state.token ? "STOMP connected (authenticated)" : "STOMP connected");
      // STOMP-less fallbacks were armed because the broker was not
      // up yet. Frames are now the source of truth. A leftover spectate
      // poll rewinds a hop (N43); leftover living / traffic polls
      // write an older GET /maze over a tick that already landed (N44).
      clearInterval(state.spectatePoll); state.spectatePoll = null;
      clearInterval(state.livePoll); state.livePoll = null;
      clearInterval(state.trafficPoll); state.trafficPoll = null;
      resubscribe(state, host);
    }, err => {
      if (gen !== stompGen) return;
      state.stomp = null;
      host.log("err", "STOMP connection lost — retrying in 3s");
      // CONNECT dropped the fallbacks (N43 / N44). The broker is gone
      // again, so a living / traffic / watched maze would freeze until
      // the next CONNECT. Re-arm the same polls; do not POST /live.
      armFallbacks(state, host);
      setTimeout(() => { if (gen === stompGen) connect(state, host); }, 3000);
    });
  }

  /** Poll while the broker is down. CONNECT clears these (N43 / N44). */
  function armFallbacks(state, host) {
    if (state.stomp) return;
    if (state.readOnly && state.session && state.maze) host.startSpectatePolling();
    if (state.maze && host.$("live") && host.$("live").disabled && !state.livePoll) {
      startPolling(state, host, state.maze.id, state.liveTickMs || 2000, Infinity);
    }
    if (state.maze && host.$("traffic") && host.$("traffic").disabled && !state.trafficPoll) {
      host.startTrafficPolling(state.maze.id, state.trafficTickMs || 2000);
    }
  }

  function resubscribe(state, host) {
    if (!state.stomp) return;
    state.subs.forEach(s => { try { s.unsubscribe(); } catch (ignored) {} });
    state.subs = [];
    if (state.maze) {
      state.subs.push(state.stomp.subscribe(`/topic/maze/${state.maze.id}/state`, f => {
        const m = JSON.parse(f.body);
        // Three frame shapes ride /state: MutationFrame (living tick, has `tick`),
        // TrafficFrame (has `congestedCells`), GeneratedFrame (has `generatorId`).
        if (m.tick !== undefined) { applyMutation(state, host, m); return; }
        if (m.congestedCells !== undefined) { host.onTrafficPulse(m); return; }
        host.log("state", `generated ${m.rows}×${m.cols} by ${m.generatorId}`);
      }));
      state.subs.push(state.stomp.subscribe(`/topic/maze/${state.maze.id}/solver`, f => {
        const m = JSON.parse(f.body);
        host.log("solver", `${m.solverId} finished: path ${m.pathLength}, success=${m.success}`);
      }));
    }
    if (state.session) {
      const sessionId = state.session.id;
      state.subs.push(state.stomp.subscribe(`/topic/session/${sessionId}/player`, f => {
        const m = JSON.parse(f.body);
        // Fog / Generate + a new Open session can replace the
        // seat after this subscribe was armed. An in-flight
        // frame must not log or apply a hop onto the new seat.
        if (state.fog) return;
        if (!state.session || state.session.id !== sessionId) return;
        const who = m.player || state.session.primary;
        host.log("player", `${who}: (${m.from.row},${m.from.col}) → (${m.to.row},${m.to.col})`);
        host.applyMove(who, m.to, m.from);
      }));
    }
    state.subs.push(state.stomp.subscribe("/topic/plugins/failures", f => {
      const m = JSON.parse(f.body);
      host.log("err", `plugin ${m.pluginId} failed in ${m.phase}: ${m.errorClass}`);
      // The frame exists so the roster can change. A log line with STARTED
      // still on the Plugins panel is the failure buried in server logs.
      host.refreshPlugins();
    }));
  }

  /**
   * STOMP-less fallback while a maze erodes: re-fetch on the tick cadence until the ticks run
   * out or the maze on screen changes. Shared by the Bring-to-life button and campaign stages
   * that declare the `living` hazard.
   */
  function startPolling(state, host, mazeId, tickMillis = 2000, ticks = 30) {
    state.liveTickMs = tickMillis;
    let polls = 0;
    clearInterval(state.livePoll);
    state.livePoll = setInterval(async () => {
      if (state.stomp || !state.maze || state.maze.id !== mazeId || ++polls > ticks + 1) {
        clearInterval(state.livePoll); state.livePoll = null;
        if (!state.stomp && state.maze && state.maze.id === mazeId) {
          host.$("live").disabled = false;
          if (host.$("harden")) host.$("harden").disabled = false;
        }
        return;
      }
      await host.refreshLivingMaze(true);
    }, tickMillis);
  }

  /** A mutation frame arrived: re-fetch the snapshot, refresh theory overlays, re-solve if a route is shown, redraw. */
  async function applyMutation(state, host, m) {
    // Frame is for a maze. Generate / adopt can replace the canvas
    // before this lands, or while the living refresh is out. Do not
    // log a tick or re-enable #live for a maze that is gone. Fog
    // stays — living under fog is honest (N19 / Q2).
    const mazeId = m.mazeId;
    if (!state.maze || state.maze.id !== mazeId) return;
    const closed = m.wallsClosed || 0;
    host.log("state", `tick ${m.tick}: ${m.wallsOpened} wall${m.wallsOpened === 1 ? "" : "s"} opened`
        + (closed ? `, ${closed} closed` : "")
        + `, ${m.deadEndsRemaining} dead ends left${m.settled ? " — maze has settled" : ""}`);
    await host.refreshLivingMaze();
    if (!state.maze || state.maze.id !== mazeId) return;
    if (m.settled) {
      host.$("live").disabled = false;
      if (host.$("harden")) host.$("harden").disabled = false;
    }
  }

  global.DaedalusLive = {connect, armFallbacks, resubscribe, startPolling, applyMutation};
})(window);
