// SPDX-License-Identifier: MIT
// Solve leftover rules. app.js owns leftover-state wiring; this file does not
// read leftover globals — it takes `state` plus a host bag.
"use strict";
(function (global) {
  let animGen = 0;

  function bump() { animGen++; }

  function sessionStatus(state) {
    return DaedalusCaption.sessionStatus(state.session);
  }

  async function run(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const r = await host.api(`/maze/${mazeId}/solve/${host.$("solver").value}?replay=true`,
        {method: "POST"});
    // Fog emptied the overlay (N18). Generate mid-flight: the old
    // path / expansions would paint onto the maze now on screen.
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Hunt coins / Hardest / sibling theory stay armed after
    // Solve. Leftover tourWalk is not the solver route;
    // leftover gold is not either; leftover cuts remint
    // GET /analysis under the walk (N65). Race / Compare
    // already drop those (N53). Hardest already drops
    // leftover Hunt and sibling theory (N59 / N64).
    // startFog still must not null tour (N17).
    state.tour = null; state.tourGot = [];
    // Leftover Hunt status stays after Solve. Generate / Fog /
    // Play rewrite #status (N48). Solve dropped tour (N65) but
    // left leftover hunt text, so leftover "waypoint hunt"
    // named a hunt that is gone under the solver path (N101).
    // startFog still must not null tour (N17).
    host.clearStatusFlash();
    host.$("status").textContent = sessionStatus(state);
    state.analysis = null; state.hardest = null;
    state.field = null; state.sanctuaries = null;
    state.lens = null; state.fingerprint = null;
    state.race = null; // a plain solve replaces any arena overlay
    if (state.caption) {
      state.caption = null;
      host.$("compareBox").innerHTML = "";
    }
    // Leftover ASCII stays armed after Solve. Generate, Fog,
    // and Play hide #asciiOut (N68). Solve did not, so leftover
    // dump reminted the text/plain maze under the solver path
    // (N69). startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Ghost stays armed after Solve. Fog already drops the
    // ticker. Theory writes already drop it (N80). Solve
    // dropped leftover Race but not ghost, so leftover
    // recording painted under the solver path (N81).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    state.path = r.path;
    state.expansions = r.expansions || [];
    host.log("solver", `${r.solverId}: path ${r.path.length}, visited ${r.visited}, `
        + `${r.elapsedMs}ms, success=${r.success}`);
    host.$("stats").innerHTML +=
        `<span>${host.esc(r.solverId)}</span> path ${r.path.length} &middot; visited ${r.visited} `
        + `&middot; explored ${r.explored} &middot; ${r.elapsedMs} ms`
        + (r.success ? "" : " &middot; <b>no route</b>") + "<br>";
    search(state, host);
  }

  /**
   * Two-act animation of a REAL recorded search (the server replays the solver's actual
   * expansion order — this is observation, never a client-side reenactment): first the
   * exploration front spreads cell by cell exactly as the algorithm expanded, then the found
   * route draws over it. BFS visibly floods, A* visibly beelines, Trémaux visibly wanders.
   * Solvers with no recorded expansions (off the graph seam) skip straight to the path.
   */
  function search(state, host) {
    const gen = ++animGen;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      state.searchProgress = 1;
      state.pathProgress = 1;
      host.draw();
      return;
    }
    const n = (state.expansions || []).length;
    const searchMs = n ? Math.min(2200, Math.max(600, n * 6)) : 0;
    // A 400-step wall-follower in 700ms is a flash, not a walk.
    const pathMs = DaedalusDraw.pathRevealMs((state.path || []).length);
    const started = performance.now();
    const step = now => {
      if (gen !== animGen) return;
      const t = now - started;
      state.searchProgress = n ? Math.min(1, t / searchMs) : 1;
      state.pathProgress = Math.max(0, Math.min(1, (t - searchMs) / pathMs));
      host.draw();
      if (state.pathProgress < 1) requestAnimationFrame(step);
    };
    state.searchProgress = 0;
    state.pathProgress = 0;
    requestAnimationFrame(step);
  }

  /** Kept for callers that only have a path (compare hover) — no exploration act. */
  function path(state, host) {
    state.expansions = [];
    search(state, host);
  }

  /**
   * Race two solvers head-to-head: both REAL recorded expansion orders replay at the SAME
   * expansions-per-second, so the algorithm that found the route with less work visibly
   * finishes first. This is observation, not reenactment — the fronts are the searches the
   * server actually ran, cell for cell.
   */
  async function race(state, host) {
    const a = host.$("solver").value, b = host.$("rival").value;
    if (a === b) { host.log("err", "pick two different solvers to race"); return; }
    host.leaveSpectate();
    const mazeId = state.maze.id;
    host.$("race").disabled = true;
    try {
      const ra = await host.api(`/maze/${mazeId}/solve/${a}?replay=true`, {method: "POST"});
      if (state.fog) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      const rb = await host.api(`/maze/${mazeId}/solve/${b}?replay=true`, {method: "POST"});
      if (state.fog) return;
      if (!state.maze || state.maze.id !== mazeId) return;
      // Hunt coins / hardest stay armed after Race. Leftover
      // tourWalk is not a solver lane — the arena is observation
      // of two searches (N53). Hunt already drops leftover theory
      // (N50). startFog still must not null tour (N17).
      state.tour = null; state.tourGot = [];
      // Leftover Hunt status stays after Race. Generate / Fog /
      // Play rewrite #status (N48). Solve / Hardest rewrite
      // after dropping tour (N101 / N102). Race dropped tour
      // (N53) but left leftover hunt text, so leftover
      // "waypoint hunt" named a hunt that is gone under the
      // arena (N103). startFog still must not null tour (N17).
      host.clearStatusFlash();
      host.$("status").textContent = sessionStatus(state);
      state.analysis = null; state.hardest = null;
      state.field = null; state.sanctuaries = null;
      state.lens = null; state.fingerprint = null;
      state.path = null; state.expansions = []; state.searchProgress = 1; state.pathProgress = 1;
      // Leftover ASCII stays armed after Race. Generate / Fog /
      // Play / Solve / Hardest hide #asciiOut (N68–N70). Race did
      // not, so leftover dump reminted the text/plain maze under
      // the arena (N71). startFog still must not null tour (N17).
      host.$("asciiOut").hidden = true;
      host.$("asciiOut").textContent = "";
      // Ghost stays armed after Race. Fog already drops the
      // ticker. Theory / Solve / Hardest already drop it
      // (N80–N82). Race did not, so leftover recording painted
      // under the arena (N83). startFog still must not null
      // tour (N17).
      clearInterval(state.ghostTimer); state.ghostTimer = null;
      state.ghost = null;
      // Leftover sidebar stays after Race. Hunt already empties
      // #compareBox (N50). Race did not, so leftover cuts caption
      // or a leftover compare hover painted under the arena (N89).
      state.caption = null;
      host.$("compareBox").innerHTML = "";
      // Leftover Solve stats stay after Race. Play / Hunt /
      // Join / Fog / Hardest rewrite #stats (N92–N96). Race
      // did not, so leftover solver numbers named the previous
      // walk under the arena (N97). startFog still must not
      // null tour (N17).
      host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
      state.race = { lanes: [
        {id: a, color: "#82b1ff", expansions: ra.expansions || [], path: ra.path,
         success: ra.success, front: 0, pathProg: 0},
        {id: b, color: "#f0b429", expansions: rb.expansions || [], path: rb.path,
         success: rb.success, front: 0, pathProg: 0},
      ]};
      host.log("solver", `arena: ${a} (${(ra.expansions || []).length} expansions) vs `
          + `${b} (${(rb.expansions || []).length} expansions) — racing at equal speed`);
      raceTick(state, host);
    } finally {
      host.$("race").disabled = false;
    }
  }

  function raceTick(state, host) {
    const gen = ++animGen;
    const lanes = state.race.lanes;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      lanes.forEach(l => { l.front = 1; l.pathProg = 1; });
      host.draw(); summary(state, host);
      return;
    }
    const maxN = Math.max(1, ...lanes.map(l => l.expansions.length));
    const rate = Math.max(150, maxN / 3.5); // expansions/sec — biggest lane takes ≤3.5s
    const started = performance.now();
    const step = now => {
      if (gen !== animGen) return;
      const t = (now - started) / 1000;
      let running = false;
      lanes.forEach(l => {
        const n = l.expansions.length;
        l.front = n ? Math.min(1, (t * rate) / n) : 1;
        const doneAt = n / rate; // seconds at which this lane's search finished
        const pathMs = DaedalusDraw.pathRevealMs((l.path || []).length);
        l.pathProg = l.front >= 1 ? Math.min(1, ((t - doneAt) * 1000) / pathMs) : 0;
        if (l.pathProg < 1) running = true;
      });
      host.draw();
      if (running) requestAnimationFrame(step);
      else summary(state, host);
    };
    requestAnimationFrame(step);
  }

  function summary(state, host) {
    if (state.fog || !state.race) return;
    const html = DaedalusCaption.raceHtml(state.race.lanes, host.esc);
    if (!html) return;
    state.caption = "race";
    host.$("compareBox").innerHTML = html;
  }

  /**
   * Race every registered solver against the current maze and table the results — ten
   * algorithms, one topology, hover a row to see how that solver actually went. Best path
   * length and fewest visits are highlighted; a solver that legitimately gives up (wall
   * follower on a braided maze) shows as such rather than as an error.
   */
  async function compare(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const ids = [...host.$("solver").options].map(o => o.value);
    host.$("compare").disabled = true;
    const results = [];
    try {
      for (const id of ids) {
        try {
          const r = await host.api(`/maze/${mazeId}/solve/${id}`, {method: "POST"});
          if (state.fog) return;
          if (!state.maze || state.maze.id !== mazeId) return;
          results.push(r);
        } catch (e) {
          host.log("err", `${id}: ${e.message}`);
        }
      }
    } finally {
      host.$("compare").disabled = false;
    }
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Same leftover as Race: Hunt coins stay under a compare
    // hover path that is not the Held-Karp corridor (N53).
    state.tour = null; state.tourGot = [];
    // Leftover Hunt status stays after Compare. Generate /
    // Fog / Play rewrite #status (N48). Solve / Hardest /
    // Race rewrite after dropping tour (N101–N103). Compare
    // dropped tour (N53) but left leftover hunt text, so
    // leftover "waypoint hunt" named a hunt that is gone
    // under the table (N104). Hover still arms a preview.
    // startFog still must not null tour (N17).
    host.clearStatusFlash();
    host.$("status").textContent = sessionStatus(state);
    state.analysis = null; state.hardest = null;
    state.field = null; state.sanctuaries = null;
    state.lens = null; state.fingerprint = null;
    // Leftover ASCII stays armed after Compare. Same leftover
    // as Race (N71). startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Ghost stays armed after Compare. Same leftover as Race
    // (N83). startFog still must not null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Race stays armed after Compare. Play / theory / Solve /
    // Hardest / Join / Hunt already drop leftover arena
    // (N55 / N60 / N59 / N79). Compare did not, so leftover
    // lanes painted under a compare hover (N88). startFog
    // still must not null tour (N17).
    state.race = null;
    bump();
    // Leftover Solve path stays armed after Compare. Race
    // already drops leftover path. Compare did not, so leftover
    // solver route painted under the table until a hover (N90).
    // Hover still arms a preview. startFog still must not null
    // tour (N17).
    state.path = null;
    state.expansions = [];
    state.searchProgress = 1;
    state.pathProgress = 1;
    // Leftover Solve stats stay after Compare. Play / Hunt /
    // Join / Fog / Hardest / Race rewrite #stats (N92–N97).
    // Compare did not, so leftover solver numbers named the
    // previous walk under the table (N98). Hover still arms a
    // preview. startFog still must not null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    const ok = results.filter(r => r.success);
    // Math.min() of an empty list is Infinity — the log used to say "best path Infinity".
    const bestPath = ok.length ? Math.min(...ok.map(r => r.path.length)) : null;
    const bestVisited = ok.length ? Math.min(...ok.map(r => r.visited)) : null;
    results.sort((a, b) => (a.success !== b.success) ? (a.success ? -1 : 1) : a.visited - b.visited);

    state.caption = "compare";
    host.$("compareBox").innerHTML = `<table><tr>
        <th>solver</th><th>path</th><th>visited</th><th>ms</th></tr>` +
      results.map(r => r.success
          ? `<tr class="solver-row" data-id="${host.esc(r.solverId)}">
               <td>${host.esc((state.algos[r.solverId] || {}).displayName || r.solverId)}</td>
               <td class="${r.path.length === bestPath ? "best" : ""}">${r.path.length}</td>
               <td class="${r.visited === bestVisited ? "best" : ""}">${r.visited}</td>
               <td>${r.elapsedMs}</td></tr>`
          : `<tr><td>${host.esc((state.algos[r.solverId] || {}).displayName || r.solverId)}</td>
               <td class="gave-up" colspan="3">gave up (documented limitation)</td></tr>`
      ).join("") + `</table>
      <div class="hint" style="text-align:center;margin-top:6px">
        hover a row to preview that solver's route &middot; click to pin</div>`;

    const byId = Object.fromEntries(results.map(r => [r.solverId, r]));
    let pinned = null;
    host.$("compareBox").querySelectorAll("tr.solver-row").forEach(tr => {
      const show = () => {
        state.path = byId[tr.dataset.id].path;
        state.expansions = []; state.searchProgress = 1; state.pathProgress = 1;
        host.draw();
      };
      tr.addEventListener("mouseenter", show);
      tr.addEventListener("mouseleave", () => {
        if (pinned) { state.path = byId[pinned].path; } else { state.path = null; }
        host.draw();
      });
      tr.addEventListener("click", () => {
        pinned = tr.dataset.id;
        host.$("compareBox").querySelectorAll("tr").forEach(x => x.classList.remove("pinned"));
        tr.classList.add("pinned");
        show();
      });
    });
    host.log("solver", ok.length
        ? `compared ${ok.length}/${results.length} solvers — `
            + `best path ${bestPath}, fewest visits ${bestVisited}`
        : `compared 0/${results.length} solvers — every solver failed`);
  }

  global.DaedalusSolve = { bump, run, search, path, race, raceTick, summary, compare };
})(window);
