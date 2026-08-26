// SPDX-License-Identifier: MIT
// Theory-overlay captions. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  const DISTANCE_RAMP = ["#1c5cab", "#2a78d6", "#3987e5", "#5598e7",
                         "#6da7ec", "#86b6ef", "#9ec5f4", "#cde2fb"];
  const LENS_COLORS = ["#e5484d", "#f2c94c", "#4cc38a"];

  function fingerprintHtml(f, escapeHtml) {
    const pct = Math.round(f.confidence * 100);
    const verdict = f.agrees
        ? `<b style="color:#4cc38a">${escapeHtml(f.predictedGeneratorId)}</b> — matches the record`
        : `<b style="color:#f0b429">${escapeHtml(f.predictedGeneratorId)}</b> — record says `
          + `${escapeHtml(f.recordedGeneratorId)}`;
    const sig = f.signature;
    return `<div style="margin-top:8px">Structure says ${verdict} `
      + `<span class="hint">(margin over ${escapeHtml(f.runnerUp)}: ${pct}%)</span></div>`
      + `<div class="hint" style="margin-top:4px">${escapeHtml(f.note)}</div>`
      + `<div class="hint" style="margin-top:4px">dead ends ${(sig.deadEndRatio*100).toFixed(0)}% · `
      + `corridors ${(sig.corridorRatio*100).toFixed(0)}% · junctions ${(sig.junctionRatio*100).toFixed(0)}% · `
      + `horizontal bias ${(sig.horizontalBias*100).toFixed(0)}% · straight-through `
      + `${(sig.straightRatio*100).toFixed(0)}% · mean run ${sig.meanStraightRun.toFixed(2)}</div>`;
  }

  function analysisHtml(a) {
    const cp = a.cutSize === 1 ? "1 chokepoint" : `${a.cutSize} chokepoints`;
    return `<div style="margin-top:8px">`
        + `<b style="color:#c084fc">${cp}</b> — sever ${a.cutSize === 1 ? "it" : "them"} and `
        + `start and goal split into different worlds &middot; `
        + `${a.deadEndCount} dead ends &middot; shortest route ${a.routeLength} cells`
        + (a.cutSize === 1
            ? ` &middot; <span class="hint">every perfect maze has exactly one cut — braid or `
              + `erode it (Bring to life) and re-analyze</span>` : "")
        + `</div>`;
  }

  function hardestHtml(h) {
    const flat = h.loops === 0 || h.hardestLength === h.shortestLength;
    return `<div style="margin-top:8px">`
        + (flat
            ? `<b style="color:#f2c94c">One route only</b> — ${h.hardestLength} steps. `
            : `<b style="color:#f2c94c">${h.hardestLength} steps</b> the cruel way against `
              + `<b>${h.shortestLength}</b> direct — a <b>&times;${h.detour.toFixed(2)}</b> detour. `)
        + `${h.loops} independent loop${h.loops === 1 ? "" : "s"} &middot; `
        + (h.exact ? `proven optimal` : `lower bound (search budget spent)`)
        + `<div class="hint" style="margin-top:4px">${h.note}</div></div>`;
  }

  function fieldHtml(f) {
    const swatches = DISTANCE_RAMP
        .map(c => `<span style="display:inline-block;width:16px;height:10px;background:${c}"></span>`)
        .join("");
    return `<div style="margin-top:8px">`
        + `<b style="color:#9ec5f4">Distance from the ${f.from.toLowerCase()}</b> — the `
        + `breadth-first field, shaded. `
        + `<div style="margin-top:6px">0 ${swatches} ${f.maxDistance} steps</div>`
        + `<div class="hint" style="margin-top:4px">This is maze distance, not distance across `
        + `the picture, so it will not look like a smooth halo: two cells touching on screen can `
        + `be 200 steps apart. Every abrupt jump in shade is a wall doing that work.</div>`
        + (f.unreachable > 0
            ? `<div class="hint">${f.unreachable} cells are unreachable rock and stay `
              + `unshaded</div>` : "")
        + `</div>`;
  }

  function sanctuariesHtml(s) {
    return `<div style="margin-top:8px">`
        + `<b style="color:#4cc38a">${s.placements.length} sanctuaries</b> &middot; `
        + `nobody is more than <b>${s.coveringRadius} steps</b> from one &middot; `
        + `serving ${s.servedCells} of ${s.habitableCells} walkable cells`
        + `<div class="hint" style="margin-top:4px">The ring marks the worst-served cell — the `
        + `loneliest place in this maze. ${s.note}</div></div>`;
  }

  function lensHtml(l) {
    const chip = (i, label, n) => `<span style="display:inline-block;width:10px;height:10px;`
        + `background:${LENS_COLORS[i]};margin-right:4px"></span>${label} <b>${n}</b>`;
    return `<div style="margin-top:8px">`
        + `${chip(0, "must expand", l.mustExpand)} &middot; ${chip(1, "tie decides", l.tie)} `
        + `&middot; ${chip(2, "never touched", l.never)}`
        + `<div style="margin-top:4px">A* really expanded <b>${l.actualExpansions}</b> of `
        + `${l.reachable} reachable cells; route ${l.routeLength} steps against an optimum of `
        + `${l.optimalCost}${l.routeOptimal ? "" : " — <b style='color:#e5484d'>not optimal</b>"}`
        + `</div><div class="hint" style="margin-top:4px">${l.note}</div></div>`;
  }

  function raceHtml(lanes, escapeHtml) {
    if (!lanes || lanes.length < 2) return "";
    const [A, B] = lanes;
    const ok = l => l.success !== false && l.path && l.path.length > 0;
    let text;
    if (ok(A) && ok(B)) {
      const [w, l] = A.expansions.length <= B.expansions.length ? [A, B] : [B, A];
      const ratio = (l.expansions.length / Math.max(1, w.expansions.length)).toFixed(1);
      text = `<b style="color:${w.color}">${escapeHtml(w.id)}</b> wins the arena — route found after `
          + `${w.expansions.length} expansions vs ${l.expansions.length} (${ratio}&times; less work). `
          + `Path lengths: ${escapeHtml(A.id)} ${A.path.length}, ${escapeHtml(B.id)} ${B.path.length}.`;
    } else if (ok(A) || ok(B)) {
      const w = ok(A) ? A : B, l = w === A ? B : A;
      text = `<b style="color:${w.color}">${escapeHtml(w.id)}</b> wins by default — `
          + `${escapeHtml(l.id)} legitimately gave up (no route under its rules).`;
    } else {
      text = "neither solver found a route.";
    }
    return `<div style="margin-top:8px">${text}</div>`;
  }

  global.DaedalusCaption = {
    DISTANCE_RAMP, LENS_COLORS,
    fingerprintHtml, analysisHtml, hardestHtml, fieldHtml, sanctuariesHtml, lensHtml, raceHtml,
  };
})(window);
