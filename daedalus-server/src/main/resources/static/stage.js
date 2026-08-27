// SPDX-License-Identifier: MIT
// Paint snapshot + input leftover rules. app.js owns leftover-state wiring;
// this file does not read `state`.
"use strict";
(function (global) {
  let geom = null;

  /** The Held-Karp walk the tour scores against — coins are stops; this is the corridor. */
  function tourWalk(state) {
    return (state.tour && state.tour.path) || [];
  }

  /** The ghost's walked prefix so far — start plus every `to` whose clock has elapsed. */
  function ghostWalk(state) {
    return DaedalusShare.ghostPrefix(state.ghost, performance.now());
  }

  /**
   * Snapshot leftover overlays into a scene so paint cannot hide inside a
   * 300-line draw() that reads globals.
   *
   * Distance field is a sequential ramp: ONE hue, monotone in lightness.
   * The heuristic lens is three bands, not a gradient of "lying".
   */
  function scene(state) {
    return {
      tiles: state.maze.tiles,
      fog: state.fog,
      hotspots: state.maze.hotspots || [],
      field: state.field,
      lens: state.lens,
      expansions: state.expansions,
      searchProgress: state.searchProgress,
      path: state.path,
      pathProgress: state.pathProgress,
      analysis: state.analysis,
      sanctuaries: state.sanctuaries,
      hardest: state.hardest,
      tourPath: tourWalk(state),
      tour: state.tour,
      tourGot: state.tourGot,
      race: state.race,
      trails: state.trails,
      session: state.session,
      ghostWalk: ghostWalk(state),
      ghost: state.ghost,
      won: state.won,
      distanceRamp: DaedalusCaption.DISTANCE_RAMP,
      lensColors: DaedalusCaption.LENS_COLORS,
    };
  }

  function paint(state, host) {
    if (!state.maze) return;
    const snap = scene(state);
    geom = DaedalusDraw.paint(host.$("maze"), snap);
    syncLegend(host, snap);
  }

  function paintEmpty(host) {
    DaedalusDraw.paintEmpty(host.$("maze"));
    syncLegend(host, null);
  }

  /**
   * Name only what is on the board. A fresh maze listing fog, ghosts, and
   * hot spots that are not there is leftover chrome on the well.
   */
  function syncLegend(host, snap) {
    const legend = host.$("legend");
    if (!legend) return;
    if (!snap) {
      legend.hidden = true;
      return;
    }
    legend.hidden = false;
    const seats = snap.session && snap.session.positions
        ? Object.keys(snap.session.positions).length : 0;
    const show = {
      floor: true,
      wall: true,
      start: true,
      goal: true,
      path: !!(snap.path && snap.path.length)
          || !!(snap.hardest && snap.hardest.path && snap.hardest.path.length)
          || !!(snap.race && snap.race.lanes
              && snap.race.lanes.some(lane => lane.path && lane.path.length)),
      hotspot: !!(snap.hotspots && snap.hotspots.length),
      player: seats > 0,
      choke: !!(snap.analysis && snap.analysis.chokepoints
          && snap.analysis.chokepoints.length),
      waypoint: !!(snap.tour && snap.tour.waypoints && snap.tour.waypoints.length),
      ghost: !!(snap.ghostWalk && snap.ghostWalk.length),
      fog: !!snap.fog,
    };
    legend.querySelectorAll("[data-key]").forEach(el => {
      el.hidden = !show[el.dataset.key];
    });
  }

  function watch(host, getState) {
    const canvas = host.$("maze");
    const wrap = canvas && canvas.parentElement;
    if (!wrap || wrap._daedalusRO) return;
    let raf = 0;
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const s = getState();
        if (s.maze) paint(s, host);
        else paintEmpty(host);
      });
    });
    wrap._daedalusRO = ro;
    ro.observe(wrap);
  }

  // Click (or tap) an adjacent cell to move — session first, then the fog agent.
  function click(state, host, ev) {
    if (!geom) return;
    const canvas = host.$("maze");
    const rect = canvas.getBoundingClientRect();
    const scale = canvas.width / rect.width; // canvas may be CSS-shrunk by max-width
    const x = (ev.clientX - rect.left) * scale, y = (ev.clientY - rect.top) * scale;
    const hit = DaedalusDraw.hitCell(geom, x, y);
    if (!hit) return;
    const row = hit.row, col = hit.col;
    if (state.session && !state.won && !state.readOnly) {
      const who = host.thisTabSeat();
      const at = who && state.session.positions[who];
      if (!at) return;
      const dr = row - at.row, dc = col - at.col;
      if (Math.abs(dr) + Math.abs(dc) === 1) host.move(who, dr, dc);
      return;
    }
    if (state.fog && !state.fog.arrived && !state.fog.expired) {
      const at = state.fog.position;
      const dr = row - at.row, dc = col - at.col;
      if (Math.abs(dr) + Math.abs(dc) === 1) {
        host.fogStep(dr, dc).catch(e => host.log("err", e.message));
      }
    }
  }

  function key(state, host, e) {
    if (e.target.tagName === "INPUT") return;
    const arrows = {ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1]};
    if (state.session && !state.readOnly) {
      const wasd = {KeyW: [-1, 0], KeyS: [1, 0], KeyA: [0, -1], KeyD: [0, 1]};
      if (arrows[e.key]) {
        e.preventDefault();
        host.move(host.thisTabSeat(), ...arrows[e.key]);
      } else if (state.joined && state.joined !== state.seat && wasd[e.code]) {
        e.preventDefault();
        host.move(state.joined, ...wasd[e.code]);
      }
      return;
    }
    if (state.fog && arrows[e.key]) {
      e.preventDefault();
      host.fogStep(...arrows[e.key]).catch(err => host.log("err", err.message));
    }
  }

  global.DaedalusStage = {tourWalk, ghostWalk, scene, paint, paintEmpty, watch, click, key};
})(window);
