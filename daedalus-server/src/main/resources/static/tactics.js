// SPDX-License-Identifier: MIT
// Squad tactics playground (ADR-060): tactics-core.js decides once a second; foes walk to their order points.
import * as tac from "/tactics-core.js";

const FIELD = 6000;   // cm across the field (60 m)
const SPEED = { ATTACK: 330, FLANK: 360, DEFEND: 260, RETREAT: 380, REINFORCE: 300, HOLD: 0 };   // cm/s
const COLOR = { ATTACK: "--atk", FLANK: "--flank", DEFEND: "--def", RETREAT: "--ret", REINFORCE: "--def", HOLD: "--hold" };
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

const canvas = document.getElementById("field");
const ctx = canvas.getContext("2d");
const player = { x: 0, y: 0, z: 0 };
let squad = [];
let spec = { squad: "demo", tick: 0, orders: [] };
let paused = false;
let tick = 0;

function reset() {
  squad = [
    { name: "slime-a", at: { x: -1500, y: -400, z: 0 }, health: 60, maxHealth: 60, seesPlayer: true },
    { name: "knight-b", at: { x: -1900, y: 500, z: 0 }, health: 120, maxHealth: 120, seesPlayer: true },
    { name: "wisp-c", at: { x: -2200, y: -900, z: 0 }, health: 40, maxHealth: 40, seesPlayer: true },
  ];
  player.x = 600; player.y = 0;
  buildSliders();
  decideNow();
}

function buildSliders() {
  const host = document.getElementById("sliders");
  host.textContent = "";
  for (const u of squad) {
    const l = document.createElement("label");
    const name = document.createElement("span");
    name.textContent = u.name;
    name.style.minWidth = "70px";
    const r = document.createElement("input");
    Object.assign(r, { type: "range", min: 0, max: u.maxHealth, step: 1, value: u.health });
    r.setAttribute("aria-label", u.name + " health");
    const v = document.createElement("span");
    v.textContent = u.health + " hp";
    r.addEventListener("input", () => { u.health = Number(r.value); v.textContent = u.health + " hp"; decideNow(); });
    l.append(name, r, v);
    host.append(l);
  }
}

function decideNow() {
  spec = tac.decide("demo", ++tick, squad.filter((u) => u.health > 0), player);
  document.getElementById("spec").textContent = tac.write(spec);
  const list = document.getElementById("orders");
  list.textContent = "";
  for (const o of spec.orders) {
    const li = document.createElement("li");
    const t = document.createElement("span");
    t.className = "tag";
    t.style.color = css(COLOR[o.verb]);
    t.textContent = o.verb + (o.side !== "-" ? " " + o.side : "");
    li.append(t, document.createTextNode(`${o.unit}: ${o.why}`));
    list.append(li);
  }
}

// ---- input: drag the player, or keys
const keys = new Set();
addEventListener("keydown", (e) => { if (/^(w|a|s|d|arrow)/i.test(e.key)) { keys.add(e.key.toLowerCase()); e.preventDefault(); } });
addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));
let dragging = false;
const toWorld = (e) => {
  const r = canvas.getBoundingClientRect();
  return { x: ((e.clientX - r.left) / r.width - 0.5) * FIELD, y: ((e.clientY - r.top) / r.height - 0.5) * FIELD };
};
canvas.addEventListener("pointerdown", (e) => { dragging = true; canvas.setPointerCapture(e.pointerId); Object.assign(player, toWorld(e)); });
canvas.addEventListener("pointermove", (e) => { if (dragging) Object.assign(player, toWorld(e)); });
canvas.addEventListener("pointerup", () => { dragging = false; });
document.getElementById("height").addEventListener("input", (e) => {
  player.z = Number(e.target.value);
  document.getElementById("hv").textContent = player.z + " cm";
  decideNow();
});
document.getElementById("reset").addEventListener("click", reset);
document.getElementById("pause").addEventListener("click", (e) => {
  paused = !paused;
  e.target.textContent = paused ? "Resume" : "Pause";
  e.target.setAttribute("aria-pressed", String(paused));
});

// ---- simulation: foes walk to their order points; attackers stop at 150 cm
function step(dt) {
  const k = 450 * dt;
  if (keys.has("w") || keys.has("arrowup")) player.y -= k;
  if (keys.has("s") || keys.has("arrowdown")) player.y += k;
  if (keys.has("a") || keys.has("arrowleft")) player.x -= k;
  if (keys.has("d") || keys.has("arrowright")) player.x += k;
  player.x = Math.max(-FIELD / 2, Math.min(FIELD / 2, player.x));
  player.y = Math.max(-FIELD / 2, Math.min(FIELD / 2, player.y));
  for (const o of spec.orders) {
    const u = squad.find((s) => s.name === o.unit);
    if (!u || u.health <= 0) continue;
    const goal = o.verb === "ATTACK" ? player : o.at;
    const dx = goal.x - u.at.x, dy = goal.y - u.at.y, d = Math.hypot(dx, dy);
    const stop = o.verb === "ATTACK" ? 150 : 40;
    if (d > stop) {
      const m = Math.min(d - stop, SPEED[o.verb] * dt);
      u.at = { x: u.at.x + dx / d * m, y: u.at.y + dy / d * m, z: u.at.z };
    }
  }
}

function draw() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const sx = (x) => (x / FIELD + 0.5) * w, sy = (y) => (y / FIELD + 0.5) * h, sr = (r) => r / FIELD * w;
  // grid every 5 m
  ctx.strokeStyle = "#1c2330";
  ctx.lineWidth = 1;
  for (let g = -FIELD / 2; g <= FIELD / 2; g += 500) {
    ctx.beginPath(); ctx.moveTo(sx(g), 0); ctx.lineTo(sx(g), h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, sy(g)); ctx.lineTo(w, sy(g)); ctx.stroke();
  }
  // engage radius and flank ring
  ctx.strokeStyle = "rgba(242,195,91,.18)";
  ctx.setLineDash([6, 6]);
  ctx.beginPath(); ctx.arc(sx(player.x), sy(player.y), sr(tac.SETTINGS.flankRadius), 0, Math.PI * 2); ctx.stroke();
  ctx.setLineDash([]);
  for (const o of spec.orders) {
    const u = squad.find((s) => s.name === o.unit);
    if (!u) continue;
    const c = css(COLOR[o.verb]);
    const goal = o.verb === "ATTACK" ? player : o.at;
    ctx.strokeStyle = c; ctx.globalAlpha = 0.5; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(sx(u.at.x), sy(u.at.y)); ctx.lineTo(sx(goal.x), sy(goal.y)); ctx.stroke();
    ctx.setLineDash([]); ctx.globalAlpha = 1;
    if (o.verb !== "ATTACK") { ctx.strokeStyle = c; ctx.strokeRect(sx(o.at.x) - 5, sy(o.at.y) - 5, 10, 10); }
  }
  for (const u of squad) {
    const o = spec.orders.find((x) => x.unit === u.name);
    ctx.fillStyle = u.health <= 0 ? "#3a4252" : css(COLOR[o ? o.verb : "HOLD"]);
    ctx.beginPath(); ctx.arc(sx(u.at.x), sy(u.at.y), 9, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#e9edf5"; ctx.font = "12px system-ui";
    ctx.fillText(u.name + (u.health <= 0 ? " (down)" : ""), sx(u.at.x) + 12, sy(u.at.y) + 4);
  }
  ctx.fillStyle = css("--gold");
  ctx.beginPath(); ctx.arc(sx(player.x), sy(player.y), 10, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#0f1218"; ctx.font = "bold 11px system-ui"; ctx.textAlign = "center";
  ctx.fillText("you", sx(player.x), sy(player.y) + 4); ctx.textAlign = "start";
}

let last = performance.now(), since = 0;
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (!paused) {
    step(dt);
    since += dt;
    if (since >= 1) { since = 0; decideNow(); }   // the director runs once a second, as in Unreal
  }
  draw();
  requestAnimationFrame(frame);
}
reset();
requestAnimationFrame(frame);
window.__tactics = () => ({ spec, squad, player });   // for the headless check
