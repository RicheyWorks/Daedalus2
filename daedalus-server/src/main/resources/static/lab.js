// SPDX-License-Identifier: MIT
// Complexity-lab leftover rules (ADR-007 idea 2). app.js owns leftover-state
// wiring; this file does not read leftover globals — it takes `state` plus a host bag.
"use strict";
(function (global) {
  // One series (the measurements) plus a de-emphasised model overlay (the fitted curve), on
  // log-log axes so a power law reads as a straight line and its slope IS the exponent.
  // Colour: a single in-band step of the app's blue, validated against this panel's surface
  // (#1a2026) — the app's lighter #82b1ff sits outside the dark-mode lightness band.
  const LAB_SERIES = "#4f83d6";

  function chartSvg(fit, seriesColor, escapeHtml) {
    const W = 288, H = 150, L = 38, R = 8, T = 10, B = 22;
    const pts = fit.measured.filter(m => m.value > 0);
    if (pts.length < 2) return "";
    const lx = m => Math.log10(m.cells), ly = m => Math.log10(m.value);
    const xs = pts.map(lx), ys = pts.map(ly);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const px = v => L + (x1 === x0 ? 0.5 : (v - x0) / (x1 - x0)) * (W - L - R);
    const py = v => H - B - (y1 === y0 ? 0.5 : (v - y0) / (y1 - y0)) * (H - T - B);

    // Model overlay: the fitted power law through the first point, drawn de-emphasised so the
    // measurements stay the subject and the fit is visibly context.
    const e = fit.exponent;
    const modelY = v => ys[0] + e * (v - xs[0]);
    const model = `<line x1="${px(x0)}" y1="${py(modelY(x0))}" x2="${px(x1)}" `
        + `y2="${py(Math.max(y0, Math.min(y1, modelY(x1))))}" stroke="#8a949e" stroke-width="2" `
        + `stroke-dasharray="4 3" opacity="0.8"/>`;
    const path = pts.map((m, i) => `${i ? "L" : "M"}${px(lx(m)).toFixed(1)},${py(ly(m)).toFixed(1)}`).join("");
    const dots = pts.map((m, i) =>
        `<circle class="labdot" data-i="${i}" cx="${px(lx(m)).toFixed(1)}" cy="${py(ly(m)).toFixed(1)}" `
        + `r="4.5" fill="${seriesColor}" stroke="#1a2026" stroke-width="2"/>`).join("");
    const last = pts[pts.length - 1];

    return `<svg id="labChart" viewBox="0 0 ${W} ${H}" width="100%" height="${H}"
       role="img" aria-label="${escapeHtml(fit.metric)} against cell count, log-log">
    <line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" stroke="#2a323b"/>
    <line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" stroke="#2a323b"/>
    ${model}
    <path d="${path}" fill="none" stroke="${seriesColor}" stroke-width="2"
          stroke-linejoin="round" stroke-linecap="round"/>
    ${dots}
    <text x="${L}" y="${H-6}" fill="#8a949e" font-size="9">${pts[0].cells} cells</text>
    <text x="${W-R}" y="${H-6}" fill="#8a949e" font-size="9" text-anchor="end">${last.cells}</text>
    <text x="4" y="${T+8}" fill="#8a949e" font-size="9">${last.value}</text>
    <text x="4" y="${H-B}" fill="#8a949e" font-size="9">${pts[0].value}</text>
    <title>log-log: a straight line means a power law, and its slope is the exponent</title>
  </svg>
  <div id="labTip" class="hint" style="min-height:14px"></div>`;
  }

  function bindHover(dots, tipEl, fit) {
    const pts = fit.measured.filter(m => m.value > 0);
    if (!tipEl) return;
    dots.forEach(dot => {
      const show = () => {
        const m = pts[Number(dot.dataset.i)];
        tipEl.textContent = `${m.size}×${m.size} — ${m.cells} cells, ${fit.metric} ${m.value}`;
      };
      dot.addEventListener("mouseenter", show);
      dot.addEventListener("focus", show);
      dot.addEventListener("mouseleave", () => { tipEl.textContent = ""; });
    });
  }

  async function loadMetrics(state, host) {
    try {
      const metrics = await host.api("/complexity/metrics");
      const sel = host.$("labMetric");
      sel.innerHTML = "";
      metrics.forEach(m => {
        const o = document.createElement("option");
        o.value = m; o.textContent = m;
        sel.appendChild(o);
      });
      sel.value = metrics.includes("maxFrontierSize") ? "maxFrontierSize" : metrics[0];
    } catch (e) { /* lab is optional; the rest of the UI does not depend on it */ }
  }

  async function measure(state, host) {
    // Sidebar lab read — does not adopt, paint, or drop watch.
    const generator = host.$("generator").value;
    const metric = host.$("labMetric").value;
    host.$("labOut").textContent = `measuring ${generator}…`;
    const fit = await host.api(`/complexity?generator=${encodeURIComponent(generator)}`
        + `&metric=${encodeURIComponent(metric)}`);
    render(state, host, fit);
    host.log("state", `complexity: ${fit.generatorId} [${fit.metric}] -> ${fit.claimed}`
        + (fit.instrumented ? ` (exponent ${fit.exponent}, R² ${fit.rSquared})` : ""));
  }

  function render(state, host, fit) {
    const box = host.$("labOut");
    if (!fit.instrumented) {
      box.innerHTML = `<div><b>${host.esc(fit.generatorId)}</b> · ${host.esc(fit.metric)}: `
          + `<b>not reported</b></div><div class="hint" style="margin-top:4px">${host.esc(fit.note)}</div>`;
      return;
    }
    box.innerHTML =
        `<div style="margin-bottom:2px"><b>${host.esc(fit.generatorId)}</b> · ${host.esc(fit.metric)}</div>`
      + `<div style="font-size:20px;color:${LAB_SERIES};line-height:1.2">${host.esc(fit.claimed)}</div>`
      + `<div class="hint">exponent ${fit.exponent} · R² ${fit.rSquared} · ${fit.points} sizes</div>`
      + chartSvg(fit, LAB_SERIES, host.esc)
      + `<details style="margin-top:6px"><summary class="hint">measured points</summary>`
      + `<table style="width:100%;font-size:11px;margin-top:4px">`
      + `<tr class="hint"><th align="left">size</th><th align="right">cells</th>`
      + `<th align="right">${host.esc(fit.metric)}</th></tr>`
      + fit.measured.map(m => `<tr><td>${m.size}×${m.size}</td><td align="right">${m.cells}</td>`
          + `<td align="right">${m.value}</td></tr>`).join("")
      + `</table></details>`
      + `<div class="hint" style="margin-top:6px">${host.esc(fit.note)}</div>`;
    bindHover(document.querySelectorAll("#labChart .labdot"), host.$("labTip"), fit);
  }

  global.DaedalusLab = {chartSvg, bindHover, loadMetrics, measure, render};
})(window);
