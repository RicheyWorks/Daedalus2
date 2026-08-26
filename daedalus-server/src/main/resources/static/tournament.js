// SPDX-License-Identifier: MIT
// Solver-tournament leftover rules (ADR-007 ideas 10 and 7).
// app.js owns leftover-state wiring; this file does not read leftover globals —
// it takes `state` plus a host bag.
"use strict";
(function (global) {
  /**
   * Rank every solver over a sample, with intervals.
   *
   * The table deliberately leads with spread and ties rather than position. Measured, a single
   * race is already correct on perfect mazes (one solver won 30 of 30) and close to a coin flip on
   * braided ones (the winner split five ways) — so the number worth showing is not "who is first"
   * but "how much does first mean here".
   */
  async function run(state, host) {
    // Sidebar lab read — Load it goes through generate(), which already leaves.
    const generator = host.$("generator").value;
    const braid = host.braidFactor();
    host.$("tournament").disabled = true;
    host.$("tourBox").innerHTML = "running the sample…";
    let t;
    try {
      t = await host.api(`/tournament?generator=${encodeURIComponent(generator)}&size=21&mazes=16`
          + `&braid=${braid}`);
    } finally {
      host.$("tournament").disabled = false;
    }
    const tied = new Set();
    t.ties.forEach(x => { tied.add(x.a); tied.add(x.b); });
    const rows = t.standings.map(s => {
      if (s.excluded) {
        return `<tr><td>${s.solverId}</td><td colspan="4" class="hint">excluded — gave up on `
            + `${s.refusals} mazes${s.completed ? `, after finishing ${s.completed}` : ""}</td></tr>`;
      }
      const w = s.work;
      return `<tr><td>${s.solverId}${tied.has(s.solverId) ? " <span title='statistically tied "
          + "with a neighbour'>=</span>" : ""}</td>`
          + `<td style="text-align:right">${w.mean.toFixed(0)}</td>`
          + `<td style="text-align:right" class="hint">${w.low.toFixed(0)}–${w.high.toFixed(0)}</td>`
          + `<td style="text-align:right">${w.cv.toFixed(0)}%</td>`
          + `<td style="text-align:right">${s.wins}</td></tr>`;
    }).join("");
    const ties = t.ties.length
        ? t.ties.map(x => `${x.a} = ${x.b}`).join(" &middot; ")
        : "none — every neighbouring pair is separated by more than its error bars";
    const adv = (t.extremes || [])[0];
    host.$("tourBox").innerHTML = `<table style="width:100%"><tr><th style="text-align:left">solver</th>`
        + `<th>mean work</th><th>95% CI</th><th>spread</th><th>wins</th></tr>${rows}</table>`
        + `<div class="hint" style="margin-top:4px">= marks a solver whose gap to the one below `
        + `it is smaller than the error bars, so the order between them is not a result.</div>`
        + `<div style="margin-top:8px"><b>Statistically tied:</b> ${ties}</div>`
        + (adv ? `<div style="margin-top:6px">Hardest maze for <b>${adv.solver}</b> against `
            + `${adv.rival}: seed <b>${adv.seed}</b> (${adv.solverWork} vs ${adv.rivalWork} cells) — `
            + `<a href="#" id="loadAdversarial">load it</a></div>` : "")
        + `<div class="hint" style="margin-top:6px">${t.note}</div>`;
    const link = host.$("loadAdversarial");
    if (link && adv) {
      link.onclick = async (e) => {
        e.preventDefault();
        host.$("generator").value = t.generatorId;
        host.updateInfo();
        host.$("seed").value = adv.seed;
        host.$("rows").value = t.size; host.$("cols").value = t.size;
        const factor = t.braid == null ? 0 : t.braid;
        if (host.$("braid")) {
          const v = String(factor);
          if (![...host.$("braid").options].some(o => o.value === v)) {
            const o = document.createElement("option");
            o.value = v;
            o.textContent = v + " — from tournament";
            host.$("braid").appendChild(o);
          }
          host.$("braid").value = v;
        }
        host.syncBraid("braid");
        await host.generate({braid: factor});
      };
    }
    host.log("state", `tournament: ${t.standings.filter(s => !s.excluded).length} solvers over `
        + `${t.mazes} mazes, ${t.ties.length} tied pairs`);
  }

  global.DaedalusTournament = {run};
})(window);
