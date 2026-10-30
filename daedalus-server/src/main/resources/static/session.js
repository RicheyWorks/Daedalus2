// SPDX-License-Identifier: MIT
// Seat leftover rules. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  async function open(state, host) {
    host.leaveSpectate();
    const name = host.$("player").value || "web";
    const mazeId = state.maze.id;
    // play stays armed during fog — it is a leave-fog path. Drop the
    // walk before the fetch (leaveSpectate-before-write). A before-click
    // snapshot that always nulled fog after the POST treated a Fog that
    // started mid-flight as "no fog" and still pinned #session=.
    // Generate mid-flight: a late /session would pin #session= and
    // seat the old session on the maze now on screen. Capture maze
    // id; discard after the POST (and the leave-fog GET /maze).
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
      // Fog wrote openings into tiles and skipped GET /maze on living ticks.
      // Leaving it without a refetch paints a fog-edited or generate-time grid.
      try {
        const maze = await host.api(`/maze/${mazeId}`);
        if (state.fog) return;
        if (!state.maze || state.maze.id !== mazeId) return;
        Object.assign(state.maze, maze);
      } catch (ignored) { /* play still works; walls may lag until the next refresh */ }
      if (state.fog) return;
      if (!state.maze || state.maze.id !== mazeId) return;
    }
    const s = await host.api(`/maze/${mazeId}/session?player=${encodeURIComponent(name)}`,
        {method: "POST"});
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Race lanes stay armed after Open session. Leftover
    // arena paints over the walk (N55). Hunt calls play()
    // after installing tour — do not null tour (N50).
    state.race = null;
    host.bumpAnim();
    // Sibling theory stays armed after Open session. Leftover
    // cuts remint GET /analysis under the seat (N66). Theory
    // writes already drop siblings (N63). Hardest already
    // drops leftover sibling theory (N64). Solve already
    // drops them (N65). Hunt calls play() after installing
    // tour — do not null tour (N50). startFog still must
    // not null tour (N17).
    state.analysis = null; state.field = null;
    state.sanctuaries = null; state.lens = null;
    state.fingerprint = null;
    // Leftover Solve path stays armed after Open session.
    // N57 only dropped Compare hover. Leftover solver route
    // paints over the seat and a living tick remints POST
    // /solve (N67). Hunt calls play() after installing tour
    // — do not null tour (N50). startFog still must not null
    // tour (N17).
    state.path = null;
    state.expansions = [];
    // Leftover ASCII stays armed after Open session. Generate
    // and Fog hide #asciiOut. Play did not, so leftover dump
    // stayed on screen and a living tick reminted the
    // text/plain maze under the seat (N68). Hunt calls play()
    // after installing tour — do not null tour (N50). startFog
    // still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Leftover Solve stats stay after Open session. Generate
    // rewrites #stats. Play did not, so leftover solver
    // numbers named the previous walk under the seat (N92).
    // Hunt calls play() after installing tour — do not null
    // tour (N50). startFog still must not null tour (N17).
    host.$("stats").innerHTML =
        `<span>maze</span> ${host.esc(state.maze.id.slice(0, 8))}&hellip;<br>`
        + `<span>by</span> ${host.esc(state.maze.generatorId)} &middot; ${state.maze.rows}&times;${state.maze.cols} `
        + `&middot; <span>seed</span> ${state.maze.seed}`
        + (state.maze.braid > 0 ? ` &middot; braided ${state.maze.braid}` : "")
        + `<br>`;
    // Leftover tourGot stays after Open session. Hunt remints
    // collected coins. Play reminted trails / won but left
    // leftover tourGot, so leftover collected coins painted
    // on the new seat until the first move reminted (N117).
    // Hunt calls play() after installing tour — do not null
    // tour (N50). startFog still must not null tour (N17).
    state.tourGot = [];
    // Hardest stays armed after Open session when caption is
    // not hardest. Join already drops leftover gold
    // unconditionally (N77). Play gated it (N58), so leftover
    // gold painted under the seat (N85). Hunt calls play()
    // after installing tour — do not null tour (N50). startFog
    // still must not null tour (N17).
    state.hardest = null;
    // Compare hover stays armed after Open session. Leftover
    // solver path paints over the walk (N57). Hunt already
    // emptied #compareBox (N50). Do not null tour.
    if (state.caption === "race" || state.caption === "compare"
        || state.caption === "hardest"
        || state.caption === "analysis" || state.caption === "field"
        || state.caption === "sanctuaries" || state.caption === "lens"
        || state.caption === "fingerprint") {
      state.caption = null;
      host.$("compareBox").innerHTML = "";
    }
    host.setGodModeEnabled(true);
    state.session = {id: s.sessionId, positions: {[name]: s.position}, primary: name};
    state.seat = name;
    state.joined = null; state.won = null;
    state.trails = {[name]: [s.position]};
    state.sessionStart = performance.now();
    host.$("join").disabled = false;
    host.$("join").textContent = "Join as second player";
    host.$("join").title = "Requires daedalus.session.multiplayer=true";
    // A leftover wall-block restore would put the previous seat's
    // line on this new session (N48).
    host.clearStatusFlash();
    host.$("status").textContent = `session ${s.sessionId.slice(0, 8)}… — arrow keys to move`;
    host.log("state", `spectate link: ${location.origin}${location.pathname}#session=${s.sessionId}`);
    host.pinHash();
    host.resubscribe();
    host.summonGhost(); // race the maze's best recorded run, if one exists
    host.draw();
  }

  async function joinSeat(state, host) {
    if (!state.session) return;
    const fromSpectate = state.readOnly;
    const name = fromSpectate
        ? (host.$("player").value || "web")
        : (host.$("player").value || "web") + "-2";
    const sessionId = state.session.id;
    const mazeId = state.maze && state.maze.id;
    try {
      const s = await host.api(`/session/${sessionId}/join?player=${encodeURIComponent(name)}`,
          {method: "POST"});
      // Stay a watcher until join lands — leaveSpectate after a successful
      // POST, not before (spectate honesty). A Fog that started mid-flight
      // dropped the seat; do not write it back onto the walk.
      // Generate + Play / a new #session=: the POST would write the
      // joiner (seat, leaveSpectate, pin) onto the maze now on screen (N36).
      if (state.fog) return;
      if (!state.session) return;
      if (state.session.id !== sessionId) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      // Leftover ASCII stays armed after Join. Open session
      // hides #asciiOut (N68). Join did not, so leftover dump
      // reminted the text/plain maze under the seat just taken
      // (N74). Join-from-spectate still keeps the hunt — do
      // not null tour. startFog still must not null tour (N17).
      host.$("asciiOut").hidden = true;
      host.$("asciiOut").textContent = "";
      // Sibling theory stays armed after Join. Open session
      // drops leftover cuts (N66). Join did not, so leftover
      // analysis reminted GET /analysis under the seat just
      // taken (N75). Join-from-spectate still keeps the hunt
      // — do not null tour. startFog still must not null tour
      // (N17).
      state.analysis = null; state.field = null;
      state.sanctuaries = null; state.lens = null;
      state.fingerprint = null;
      if (state.caption === "analysis" || state.caption === "field"
          || state.caption === "sanctuaries" || state.caption === "lens"
          || state.caption === "fingerprint") {
        state.caption = null;
        host.$("compareBox").innerHTML = "";
      }
      // Leftover Solve path stays armed after Join. Open session
      // drops it (N67). Join did not, so leftover solver route
      // reminted POST /solve under the seat just taken (N76).
      // Join-from-spectate still keeps the hunt — do not null
      // tour. startFog still must not null tour (N17).
      state.path = null;
      state.expansions = [];
      // Hardest stays armed after Join. Open session drops leftover
      // gold when caption is hardest (N58). Join did not, so leftover
      // gold reminted GET /hardest-route under the seat just taken
      // (N77). Join-from-spectate still keeps the hunt — do not null
      // tour. startFog still must not null tour (N17).
      state.hardest = null;
      if (state.caption === "hardest" || state.caption === "race"
          || state.caption === "compare") {
        state.caption = null;
        host.$("compareBox").innerHTML = "";
      }
      // Race stays armed after Join. Open session drops leftover
      // arena (N55). Join did not, so leftover lanes painted under
      // the seat just taken (N79). Race stays a recording — do
      // not remint. Join-from-spectate still keeps the hunt — do
      // not null tour. startFog still must not null tour (N17).
      state.race = null;
      host.bumpAnim();
      // Leftover Solve stats stay after Join. Open session
      // rewrites #stats (N92). Hunt rewrites when play() is
      // skipped (N93). Join did not, so leftover solver
      // numbers named the previous walk under the seat just
      // taken (N94). Join-from-spectate still keeps the hunt
      // — do not null tour. startFog still must not null tour
      // (N17).
      host.$("stats").innerHTML =
          `<span>maze</span> ${host.esc(state.maze.id.slice(0, 8))}&hellip;<br>`
          + `<span>by</span> ${host.esc(state.maze.generatorId)} &middot; ${state.maze.rows}&times;${state.maze.cols} `
          + `&middot; <span>seed</span> ${state.maze.seed}`
          + (state.maze.braid > 0 ? ` &middot; braided ${state.maze.braid}` : "")
          + `<br>`;
      state.session.positions[name] = s.position;
      state.trails[name] = [s.position];
      if (fromSpectate) {
        // Seat first so leaveSpectate keeps this session (N51).
        // primary stays the opener — win-vs-ghost keys on it.
        // This tab's arrows and clicks move the seat we just took.
        state.seat = name;
        host.leaveSpectate();
        state.joined = name;
        state.sessionStart = performance.now();
        host.pinHash();
        // Leftover spectate join title stays after
        // Join-from-spectate. Open session rewrites #join
        // (label + title). leaveSpectate rewrites when it
        // drops a watch (N105). Join-from-spectate only
        // rewrote the label, so leftover spectate title
        // named a watch that is gone under the seat just
        // taken (N107). Join-from-spectate still keeps the
        // hunt — do not null tour. startFog still must not
        // null tour (N17).
        host.$("join").textContent = "Join as second player";
        host.$("join").title = "Requires daedalus.session.multiplayer=true";
        host.$("status").textContent = `session ${state.session.id.slice(0, 8)}… — arrow keys to move`;
        host.log("player", `${name} joined the spectated session`);
        host.resubscribe();
      } else {
        state.joined = name;
        host.log("player", `${name} joined (multiplayer flag is on)`);
      }
      host.draw();
    } catch (e) {
      const msg = e.message || "";
      // Flag-off join is the same 404 as an unknown session — do not name the flag.
      const why = /session-completed|already finished/i.test(msg)
          ? "this session already finished"
          : /session-full|is full/i.test(msg)
              ? "this session is full"
              : host.nameGone(msg) || msg;
      host.log("err", `join refused — ${why}`);
    }
  }

  async function hop(state, host, name, dr, dc) {
    if (!state.session || state.won) return;
    const at = state.session.positions[name];
    if (!at) return;
    const to = {row: at.row + dr, col: at.col + dc};
    const body = name === state.session.primary ? {to} : {to, player: name};
    const sessionId = state.session.id;
    const mazeId = state.maze && state.maze.id;
    try {
      const ok = await host.api(`/session/${sessionId}/move`, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
      });
      // Fog / Generate + a new Open session can replace the
      // seat while this hop is out. A blocked reply's
      // flashStatus would overwrite fog status; applyMove
      // would write the old hop onto the new seat. Arrows
      // and click-to-move both land here.
      if (state.fog) return;
      if (!state.session || state.session.id !== sessionId) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      if (state.session.positions[name] == null) return;
      if (ok === false) {
        host.flashStatus("blocked — that way is a wall");
        return;
      }
      // With STOMP connected, the frame is the source of truth (keeps every viewer
      // consistent, including other tabs). Without it, apply locally so play still works.
      if (!state.stomp) apply(state, host, name, to);
    } catch (e) {
      if (state.fog) return;
      if (!state.session || state.session.id !== sessionId) return;
      if (/evicted/.test(e.message)) {
        host.log("err", "this maze aged out of the cache — generate again");
        host.$("status").textContent = "this maze aged out of the cache — generate again";
      } else {
        host.log("err", e.message);
      }
    }
  }

  /** Shared position update: called from the STOMP frame handler or the local fallback. */
  function apply(state, host, who, to, from) {
    if (!state.session) return;
    state.session.positions[who] = to;
    state.trails[who] = DaedalusSeat.extendTrail(state.trails[who], from, to);
    const tile = DaedalusSeat.tileAt(state.maze.tiles, to);
    if (tile === "G") declare(state, host, who);
    else {
      const moves = (state.trails[who] || []).length - 1;
      if (state.tour) host.refreshTourStatus();
      else {
        host.$("status").textContent =
            `session ${state.session.id.slice(0, 8)}… — ${who}: ${moves} moves`;
      }
      if (!state.stomp && !state.won) confirm(state, host, who);
    }
    host.draw();
  }

  /** Offline path: tiles can lag a living tick. The session snapshot is the win. */
  async function confirm(state, host, who) {
    if (!state.session || state.won) return;
    const sessionId = state.session.id;
    const mazeId = state.maze && state.maze.id;
    try {
      const view = await host.api(`/session/${sessionId}`);
      // Fog dropped the seat while this snapshot was out. applyMove
      // already bails when !state.session; do not declareWin onto fog.
      // Generate + a new Play: the old snapshot would declareWin
      // (leaderboard, campaign) on the maze now on screen (N35).
      if (state.fog) return;
      if (!state.session) return;
      if (state.session.id !== sessionId) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      if (view.completed) declare(state, host, view.completedBy || who);
    } catch (ignored) { /* play still works; the next hop will ask again */ }
  }

  function declare(state, host, who) {
    if (state.won) return;
    if (state.fog) return;
    if (!state.session) return;
    const sessionId = state.session.id;
    const mazeId = state.maze && state.maze.id;
    state.won = who;
    let verdict = "";
    if (state.ghost) {
      const myMs = performance.now() - state.sessionStart;
      verdict = myMs < state.ghost.elapsedMs
          ? ` — you BEAT the ghost by ${((state.ghost.elapsedMs - myMs) / 1000).toFixed(1)}s!`
          : ` — the ghost was ${((myMs - state.ghost.elapsedMs) / 1000).toFixed(1)}s faster`;
      clearInterval(state.ghostTimer);
    }
    if (state.tour) {
      host.tourVerdict().then(tv => {
        if (state.fog) return;
        if (!state.session) return;
        if (state.session.id !== sessionId) return;
        if (!state.maze || state.maze.id !== mazeId) return;
        host.log("state", `${who} reached the goal — session complete${verdict}${tv}`);
        host.$("status").textContent = `${who} reached the goal${verdict}${tv}`;
      });
    } else {
      host.log("state", `${who} reached the goal — session complete${verdict}`);
      host.$("status").textContent = `${who} reached the goal — session complete${verdict}`;
    }
    host.refreshLeaderboard();
    if (state.campaign && state.stageIndex != null) host.onStageCleared();
    host.draw();
  }

  global.DaedalusSession = {open, joinSeat, hop, apply, confirm, declare};
})(window);
