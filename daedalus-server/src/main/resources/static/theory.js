// SPDX-License-Identifier: MIT
// Theory leftover rules. Captions live in caption.js; this file does not
// read leftover globals — it takes `state` plus a host bag.
"use strict";
(function (global) {
  /** First Identify used to hang the tab on a 40s request-thread fit. 503 means warming. */
  async function waitFingerprint(state, host, id) {
    const t0 = performance.now();
    let warned = false;
    while (performance.now() - t0 < 60000) {
      // Generate / Fog left this maze while we waited on 503. Another
      // fingerprint GET would still mint work against the id you left
      // (N47). identifyGenerator already discards the paint.
      if (state.fog || !state.maze || state.maze.id !== id) return null;
      try {
        return await host.api(`/maze/${id}/fingerprint`);
      } catch (e) {
        if (!/503/.test(e.message)) throw e;
        if (!warned) {
          host.log("state", "fingerprint: classifier is warming");
          warned = true;
        }
        await new Promise(r => setTimeout(r, 800));
      }
    }
    throw new Error("classifier is still warming");
  }

  function paintFingerprint(state, host, f) {
    host.$("compareBox").innerHTML = DaedalusCaption.fingerprintHtml(f, host.esc);
  }

  function paintAnalysis(state, host, a) {
    host.$("compareBox").innerHTML = DaedalusCaption.analysisHtml(a);
  }

  function paintHardest(state, host, h) {
    host.$("compareBox").innerHTML = DaedalusCaption.hardestHtml(h);
  }

  function paintField(state, host, f) {
    host.$("compareBox").innerHTML = DaedalusCaption.fieldHtml(f);
  }

  function paintSanctuaries(state, host, s) {
    host.$("compareBox").innerHTML = DaedalusCaption.sanctuariesHtml(s);
  }

  function paintLens(state, host, l) {
    host.$("compareBox").innerHTML = DaedalusCaption.lensHtml(l);
  }

  /** Name the algorithm from the shape alone, and say how sure the structure allows us to be. */
  async function identify(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const f = await waitFingerprint(state, host, mazeId);
    // Fog emptied the sidebar (N18). Generate mid-flight: a late
    // fingerprint would name the old maze on the one now on screen.
    if (!f) return;
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Race lanes stay armed after Identify. Leftover arena
    // keeps racing under the sidebar (N60). Hunt stays.
    // Hardest stays too — leftover gold remints on a living
    // tick (N61). Compare hover stays too — leftover
    // solver path remints POST /solve on a living tick (N62).
    state.race = null;
    host.bumpAnim();
    state.hardest = null;
    // Leftover Solve search wash stays armed after Identify.
    // Leftover path stays as a route hint (N62). Leftover
    // expansions painted the search wash under the sidebar
    // (N87). Hunt stays. startFog still must not null tour
    // (N17).
    state.expansions = [];
    state.searchProgress = 1;
    if (state.path) state.pathProgress = 1;
    if (state.caption === "compare") {
      state.path = null;
    }
    // Ghost stays armed after Identify. Fog already drops the
    // ticker. Theory writes dropped leftover Race (N60) but
    // not ghost, so leftover recording painted under the
    // sidebar (N80). Hunt and a leftover Solve path stay.
    // startFog still must not null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Sibling theory stays armed after Identify. Leftover
    // cuts / heat / rings / bands remint on a living tick
    // (N63). Hunt and a leftover Solve path stay.
    state.analysis = null; state.field = null;
    state.sanctuaries = null; state.lens = null;
    // Leftover ASCII stays armed after Identify. Generate /
    // Fog / Play / Solve / Hardest / Race / Hunt hide
    // #asciiOut (N68–N72). Theory writes did not, so leftover
    // dump reminted the text/plain maze under the sidebar
    // (N73). Hunt and a leftover Solve path stay. startFog
    // still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Leftover Solve stats stay after Identify. Play / Hunt /
    // Join / Fog / Hardest / Race / Compare rewrite #stats
    // (N92–N98). Theory writes did not, so leftover solver
    // numbers named the previous walk under the sidebar (N99).
    // Hunt and a leftover Solve path stay. startFog still
    // must not null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    state.fingerprint = f;
    state.caption = "fingerprint";
    host.log("state", `fingerprint: structure says ${f.predictedGeneratorId}`
        + (f.agrees ? " (matches record)" : `, record says ${f.recordedGeneratorId}`));
    paintFingerprint(state, host, f);
    host.draw();
  }

  /** Min-cut chokepoints + dead ends from the theory module, drawn over the maze. */
  async function analyze(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const a = await host.api(`/maze/${mazeId}/analysis`);
    // startFog already emptied #compareBox (N17). A response that
    // was already out still landed and named chokepoints again.
    // Generate mid-flight: paint would name the old maze's cuts
    // on the maze now on screen. Discard — same as N18 / N28.
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Race lanes stay armed after Analyze. Leftover arena
    // paints over the cuts (N60). Hunt stays — chokepoints
    // during a hunt are useful. Hardest stays too —
    // leftover gold paints over the cuts and a living tick
    // remints GET /hardest-route (N61). Compare hover
    // stays too — leftover solver path remints POST
    // /solve on a living tick (N62). startFog still
    // must not null tour (N17).
    state.race = null;
    host.bumpAnim();
    state.hardest = null;
    // Leftover Solve search wash stays armed after Analyze.
    // Leftover path stays as a route hint (N62). Leftover
    // expansions painted the search wash under the cuts
    // (N87). Hunt stays. startFog still must not null tour
    // (N17).
    state.expansions = [];
    state.searchProgress = 1;
    if (state.path) state.pathProgress = 1;
    if (state.caption === "compare") {
      state.path = null;
    }
    // Ghost stays armed after Analyze. Fog already drops the
    // ticker. Theory writes dropped leftover Race (N60) but
    // not ghost, so leftover recording painted under the cuts
    // (N80). Hunt and a leftover Solve path stay. startFog
    // still must not null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Sibling theory stays armed after Analyze. Leftover
    // heat remints GET /distance-field on a living tick
    // (N63). Field already drops sibling overlays. Hunt
    // and a leftover Solve path stay.
    state.field = null; state.sanctuaries = null;
    state.lens = null; state.fingerprint = null;
    // Leftover ASCII remints the text/plain maze under the
    // cuts (N73). Hunt and a leftover Solve path stay.
    // startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Leftover Solve stats stay after Analyze. Play / Hunt /
    // Join / Fog / Hardest / Race / Compare rewrite #stats
    // (N92–N98). Theory writes did not, so leftover solver
    // numbers named the previous walk under the cuts (N99).
    // Hunt and a leftover Solve path stay. startFog still
    // must not null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    state.analysis = a;
    state.caption = "analysis";
    const cp = a.cutSize === 1 ? "1 chokepoint" : `${a.cutSize} chokepoints`;
    host.log("state", `analysis: ${cp}, ${a.deadEndCount} dead ends, route length ${a.routeLength}`);
    paintAnalysis(state, host, a);
    host.draw();
  }

  async function hardest(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const h = await host.api(`/maze/${mazeId}/hardest-route`);
    // Fog emptied the overlay (N18). Generate mid-flight: the old
    // route would paint the maze now on screen. Discard — same as N18 / N30.
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Hunt coins / Race lanes stay armed after Hardest. Leftover
    // tourWalk is not the cruel route; leftover arena is not
    // either (N59). Race / Compare already drop leftover Hunt
    // (N53). startFog still must not null tour (N17).
    state.tour = null; state.tourGot = [];
    // Leftover Hunt status stays after Hardest. Generate /
    // Fog / Play rewrite #status (N48). Solve rewrites after
    // dropping tour (N101). Hardest dropped tour (N59) but
    // left leftover hunt text, so leftover "waypoint hunt"
    // named a hunt that is gone under the gold walk (N102).
    // startFog still must not null tour (N17).
    host.clearStatusFlash();
    host.$("status").textContent = DaedalusCaption.sessionStatus(state.session);
    state.race = null;
    host.bumpAnim();
    state.path = null; state.expansions = [];
    state.searchProgress = 1; state.pathProgress = 1;
    // Sibling theory stays armed after Hardest. Leftover
    // cuts remint GET /analysis under the gold walk (N64).
    // Theory writes already drop siblings (N63). startFog
    // still must not null tour (N17).
    state.analysis = null; state.field = null;
    state.sanctuaries = null; state.lens = null;
    state.fingerprint = null;
    // Leftover ASCII stays armed after Hardest. Generate, Fog,
    // Play, and Solve hide #asciiOut (N68 / N69). Hardest did
    // not, so leftover dump reminted the text/plain maze under
    // the gold walk (N70). startFog still must not null tour
    // (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Ghost stays armed after Hardest. Fog already drops the
    // ticker. Theory / Solve already drop it (N80 / N81).
    // Hardest dropped leftover Race but not ghost, so leftover
    // recording painted under the gold walk (N82).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Leftover Solve stats stay after Hardest. Play / Hunt /
    // Join / Fog rewrite #stats (N92–N95). Hardest did not,
    // so leftover solver numbers named the previous walk
    // under the gold walk (N96). startFog still must not
    // null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    state.hardest = h;
    state.caption = "hardest";
    host.log("state", `hardest route: ${h.hardestLength} steps vs ${h.shortestLength} shortest `
        + `(x${h.detour.toFixed(2)}), ${h.loops} loops, ${h.exact ? "proven optimal" : "lower bound"}`);
    paintHardest(state, host, h);
    host.draw();
  }

  async function heat(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const f = await host.api(`/maze/${mazeId}/distance-field`);
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Race lanes stay armed after the heat map. Leftover
    // arena paints over the field (N60). Hunt stays.
    // Hardest stays too — leftover gold remints (N61).
    // Compare hover remints POST /solve (N62).
    state.race = null;
    host.bumpAnim();
    state.hardest = null;
    // Leftover Solve search wash paints under the field (N87).
    // Leftover path stays as a route hint (N62). Hunt stays.
    // startFog still must not null tour (N17).
    state.expansions = [];
    state.searchProgress = 1;
    if (state.path) state.pathProgress = 1;
    if (state.caption === "compare") {
      state.path = null;
    }
    // Leftover ghost paints under the field (N80). Hunt and
    // a leftover Solve path stay. startFog still must not
    // null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Leftover cuts remint GET /analysis under the field (N63).
    state.analysis = null; state.fingerprint = null;
    // Leftover ASCII remints the text/plain maze under the
    // field (N73). Hunt and a leftover Solve path stay.
    // startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Leftover Solve stats stay after heat. Play / Hunt /
    // Join / Fog / Hardest / Race / Compare rewrite #stats
    // (N92–N98). Theory writes did not, so leftover solver
    // numbers named the previous walk under the field (N99).
    // Hunt and a leftover Solve path stay. startFog still
    // must not null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    state.field = f;
    state.sanctuaries = null; state.lens = null;   // one overlay at a time stays readable
    state.caption = "field";
    host.log("state", `distance field from ${f.from.toLowerCase()}: farthest cell ${f.maxDistance} `
        + `steps away, ${f.unreachable} cells unreachable`);
    paintField(state, host, f);
    host.draw();
  }

  async function sanctuaries(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const s = await host.api(`/maze/${mazeId}/sanctuaries?k=5`);
    // Fog emptied the overlay (N18). Generate mid-flight: the old
    // rings would paint the maze now on screen. Discard — same as N18 / N30.
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Race lanes stay armed after Sanctuaries. Leftover
    // arena paints over the rings (N60). Hunt stays.
    // Hardest stays too — leftover gold remints (N61).
    // Compare hover remints POST /solve (N62).
    state.race = null;
    host.bumpAnim();
    state.hardest = null;
    // Leftover Solve search wash paints under the rings (N87).
    // Leftover path stays as a route hint (N62). Hunt stays.
    // startFog still must not null tour (N17).
    state.expansions = [];
    state.searchProgress = 1;
    if (state.path) state.pathProgress = 1;
    if (state.caption === "compare") {
      state.path = null;
    }
    // Leftover ghost paints under the rings (N80). Hunt and
    // a leftover Solve path stay. startFog still must not
    // null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Leftover cuts remint GET /analysis under the rings (N63).
    state.analysis = null; state.fingerprint = null;
    // Leftover ASCII remints the text/plain maze under the
    // rings (N73). Hunt and a leftover Solve path stay.
    // startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Leftover Solve stats stay after sanctuaries. Play /
    // Hunt / Join / Fog / Hardest / Race / Compare rewrite
    // #stats (N92–N98). Theory writes did not, so leftover
    // solver numbers named the previous walk under the rings
    // (N99). Hunt and a leftover Solve path stay. startFog
    // still must not null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    state.sanctuaries = s;
    state.field = null; state.lens = null;
    state.caption = "sanctuaries";
    host.log("state", `${s.placements.length} sanctuaries: covering radius ${s.coveringRadius}, `
        + `serving ${s.servedCells}/${s.habitableCells} cells`);
    paintSanctuaries(state, host, s);
    host.draw();
  }

  async function lens(state, host) {
    host.leaveSpectate();
    const mazeId = state.maze.id;
    const which = host.$("lensH").value;
    const l = await host.api(`/maze/${mazeId}/heuristic-lens?heuristic=${which}`);
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    // Race lanes stay armed after Lens. Leftover arena
    // paints over the bands (N60). Hunt stays.
    // Hardest stays too — leftover gold remints (N61).
    // Compare hover remints POST /solve (N62).
    state.race = null;
    host.bumpAnim();
    state.hardest = null;
    // Leftover Solve search wash paints under the bands (N87).
    // Leftover path stays as a route hint (N62). Hunt stays.
    // startFog still must not null tour (N17).
    state.expansions = [];
    state.searchProgress = 1;
    if (state.path) state.pathProgress = 1;
    if (state.caption === "compare") {
      state.path = null;
    }
    // Leftover ghost paints under the bands (N80). Hunt and
    // a leftover Solve path stay. startFog still must not
    // null tour (N17).
    clearInterval(state.ghostTimer); state.ghostTimer = null;
    state.ghost = null;
    // Leftover cuts remint GET /analysis under the bands (N63).
    state.analysis = null; state.fingerprint = null;
    // Leftover ASCII remints the text/plain maze under the
    // bands (N73). Hunt and a leftover Solve path stay.
    // startFog still must not null tour (N17).
    host.$("asciiOut").hidden = true;
    host.$("asciiOut").textContent = "";
    // Leftover Solve stats stay after lens. Play / Hunt /
    // Join / Fog / Hardest / Race / Compare rewrite #stats
    // (N92–N98). Theory writes did not, so leftover solver
    // numbers named the previous walk under the bands (N99).
    // Hunt and a leftover Solve path stay. startFog still
    // must not null tour (N17).
    host.$("stats").innerHTML = DaedalusCaption.mazeStats(state.maze, host.esc);
    state.lens = l;
    state.field = null; state.sanctuaries = null;
    state.caption = "lens";
    host.log("state", `lens [${which}]: must ${l.mustExpand}, tie ${l.tie}, never ${l.never}; `
        + `A* expanded ${l.actualExpansions}`);
    paintLens(state, host, l);
    host.draw();
  }

  /**
   * Theory overlays claim to be about the maze underfoot. Analysis, tour and the
   * solver route already re-asked on each living tick; hardest-route, the heat
   * map, sanctuaries, the lens, the fingerprint and the ASCII dump did not —
   * they painted the tree they were first asked about while the grid eroded
   * under them. The fingerprint button's whole claim is eroded mazes whose
   * recorded author no longer matches. Race and ghost stay recordings.
   *
   * @return false when the maze on screen changed mid-refresh (caller must stop)
   */
  async function refreshOverlays(state, host, forMaze, stale) {
    if (state.analysis) {
      try {
        const a = await host.api(`/maze/${forMaze}/analysis`);
        if (stale() || state.fog) return false;
        if (a.cutSize !== state.analysis.cutSize || a.deadEndCount !== state.analysis.deadEndCount) {
          host.log("state", `analysis: ${a.cutSize} chokepoint${a.cutSize === 1 ? "" : "s"}, `
              + `${a.deadEndCount} dead ends (was ${state.analysis.cutSize} / `
              + `${state.analysis.deadEndCount})`);
        }
        state.analysis = a;
        if (state.caption === "analysis") paintAnalysis(state, host, a);
      } catch (ignored) { /* overlay; losing one refresh is harmless */ }
    }
    if (state.hardest) {
      try {
        const h = await host.api(`/maze/${forMaze}/hardest-route`);
        if (stale() || state.fog) return false;
        if (h.loops !== state.hardest.loops || h.hardestLength !== state.hardest.hardestLength) {
          host.log("state", `hardest route is now ${h.hardestLength} steps vs ${h.shortestLength} `
              + `(x${h.detour.toFixed(2)}), ${h.loops} loops`);
        }
        state.hardest = h;
        if (state.caption === "hardest") paintHardest(state, host, h);
      } catch (ignored) { /* overlay */ }
    }
    if (state.field) {
      try {
        const f = await host.api(`/maze/${forMaze}/distance-field`);
        if (stale() || state.fog) return false;
        if (f.maxDistance !== state.field.maxDistance) {
          host.log("state", `distance field: farthest cell now ${f.maxDistance} steps`);
        }
        state.field = f;
        if (state.caption === "field") paintField(state, host, f);
      } catch (ignored) { /* overlay */ }
    }
    if (state.sanctuaries) {
      try {
        const s = await host.api(`/maze/${forMaze}/sanctuaries?k=5`);
        if (stale() || state.fog) return false;
        if (s.coveringRadius !== state.sanctuaries.coveringRadius) {
          host.log("state", `sanctuaries: covering radius now ${s.coveringRadius}`);
        }
        state.sanctuaries = s;
        if (state.caption === "sanctuaries") paintSanctuaries(state, host, s);
      } catch (ignored) { /* overlay */ }
    }
    if (state.lens) {
      try {
        const which = (state.lens.heuristic || host.$("lensH").value);
        const l = await host.api(`/maze/${forMaze}/heuristic-lens?heuristic=${encodeURIComponent(which)}`);
        if (stale() || state.fog) return false;
        if (l.mustExpand !== state.lens.mustExpand || l.actualExpansions !== state.lens.actualExpansions) {
          host.log("state", `lens: must ${l.mustExpand}, A* expanded ${l.actualExpansions}`);
        }
        state.lens = l;
        if (state.caption === "lens") paintLens(state, host, l);
      } catch (ignored) { /* overlay */ }
    }
    if (state.fingerprint) {
      try {
        const f = await host.api(`/maze/${forMaze}/fingerprint`);
        if (stale() || state.fog) return false;
        const before = state.fingerprint;
        if (f.agrees !== before.agrees
            || f.predictedGeneratorId !== before.predictedGeneratorId
            || f.signature.deadEndRatio !== before.signature.deadEndRatio) {
          host.log("state", `fingerprint: structure says ${f.predictedGeneratorId}`
              + (f.agrees ? " (matches record)" : `, record says ${f.recordedGeneratorId}`));
        }
        state.fingerprint = f;
        if (state.caption === "fingerprint") paintFingerprint(state, host, f);
      } catch (ignored) { /* overlay */ }
    }
    if (host.$("asciiOut") && !host.$("asciiOut").hidden) {
      try {
        await host.showAscii();
        if (stale() || state.fog) return false;
      } catch (ignored) { /* dump */ }
    }
    return true;
  }

  global.DaedalusTheory = {
    waitFingerprint, identify, analyze, hardest, heat, sanctuaries, lens,
    paintFingerprint, paintAnalysis, paintHardest, paintField, paintSanctuaries, paintLens,
    refreshOverlays,
  };
})(window);
