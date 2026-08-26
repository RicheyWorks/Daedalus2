// SPDX-License-Identifier: MIT
// Complexity-lab chart. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
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

  global.DaedalusLab = {chartSvg, bindHover};
})(window);
