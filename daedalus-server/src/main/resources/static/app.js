// SPDX-License-Identifier: MIT
// Daedalus web UI script. Served next to index.html; no build step.
"use strict";
const $ = id => document.getElementById(id);
const state = {
  maze: null,            // GenerateResponse (tiles as array of strings, thanks to Jackson char[])
  path: null,            // SolveResponse.path (cell coords)
  pathProgress: 1,       // 0..1 — animated reveal of the solver path
  session: null,         // { id, positions: {playerName: {row,col}}, primary, goal }
  seat: null,            // who this tab's arrows and clicks move (opener, or the spectate-join)
  joined: null,          // second player's name, when joined
  trails: {},            // playerName -> [Point] breadcrumbs during play
  algos: {},             // id -> AlgorithmDescriptor, for the info cards
  stomp: null,
  subs: [],
  livePoll: null,        // interval id — STOMP-less fallback while a maze is alive
  liveTickMs: 2000,      // last living cadence — reconnect re-arms with this
  trafficPoll: null,     // interval id — STOMP-less fallback while traffic is tracked
  trafficTickMs: 2000,   // last traffic cadence — reconnect re-arms with this
  race: null,            // {lanes: [{id, color, expansions, path, front, pathProg}]} during a race
  dailyId: null,         // set when the current maze is today's daily → scoped leaderboard
  analysis: null,        // AnalysisResponse — chokepoint/dead-end overlay when set
  ghost: null,           // {moves, name, score, elapsedMs, started, pos, done} during play
  ghostTimer: null,      // interval advancing the ghost
  sessionStart: null,    // performance.now() at session open — for the ghost verdict
  prevMazeId: null,      // last maze before this one — crossbreeding's other parent
  readOnly: false,       // spectating: render everything, control nothing
  spectatePoll: null,    // interval id — STOMP-less spectator fallback
  tour: null,            // {waypoints, optimalOrder, optimalCost} in waypoint-hunt mode
  tourGot: [],           // waypoints collected this session (display only; server scores)
  campaign: null,        // {seed, stages} once a campaign is loaded
  stageIndex: null,      // which stage is on screen
  cleared: {},           // stageIndex → true once its goal is reached
  token: null,           // JWT from POST /auth/login — attached to REST and STOMP
  user: null,            // display name that minted the token
  fog: null,             // AgentView + seen Set — cells this walk has stood on
  lbQuery: null,         // last /leaderboard path actually fetched (partition, not a title)
  caption: null,         // which theory panel last wrote #compareBox — living ticks refresh it
  fingerprint: null,     // last Identification — living ticks re-ask; the feature is erosion
};

/** Escape untrusted text (player names arrive from other clients) before it meets innerHTML. */
function esc(s) {
  return String(s).replace(/[&<>"']/g,
      ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
}

function log(kind, text) {
  const line = document.createElement("div");
  const t = new Date().toLocaleTimeString();
  line.innerHTML = `<span class="t">${t}</span>`;
  const span = document.createElement("span");
  span.className = kind;
  span.textContent = text; // never innerHTML: frame contents include other users' names
  line.appendChild(span);
  const box = $("log");
  box.prepend(line);
  while (box.childElementCount > 200) box.lastChild.remove();
}

// A shared maze gets its own board: the daily challenge, or a campaign stage. You compete
// against everyone who played that same topology, not against the world's easiest mazes.
function lbMazeScope() {
  if (!state.maze) return null;
  if (state.dailyId && state.maze.id === state.dailyId) return state.dailyId;
  if (state.campaign && state.stageIndex != null
      && state.campaign.stages[state.stageIndex].mazeId === state.maze.id) {
    return state.maze.id;
  }
  return null;
}

/** Which partition this refresh will ask for. maze= wins; never send both (the server
 *  would drop generator= and the select would be lying). */
function lbRequest() {
  const maze = lbMazeScope();
  const generator = $("lbGen") ? $("lbGen").value : "";
  if (maze) return {path: `/leaderboard?n=10&maze=${maze}`, maze, generator: ""};
  if (generator) {
    return {path: `/leaderboard?n=10&generator=${encodeURIComponent(generator)}`,
            maze: null, generator};
  }
  return {path: "/leaderboard?n=10", maze: null, generator: ""};
}

async function refreshLeaderboard() {
  try {
    const req = lbRequest();
    const rows = await api(req.path);
    if (lbRequest().path !== req.path) return; // scope changed in flight
    state.lbQuery = req.path; // what we actually asked — sweep pins generator= vs maze=
    const mazeScoped = !!req.maze;
    if ($("lbGen")) {
      $("lbGen").disabled = mazeScoped;
    }
    $("lbTitle").textContent = mazeScoped
        ? (req.maze === state.dailyId ? "Daily leaderboard"
            : `Stage ${state.stageIndex + 1} leaderboard`)
        : req.generator
            ? `${(state.algos[req.generator] && state.algos[req.generator].displayName)
                || req.generator} leaderboard`
            : "Leaderboard";
    $("lb").innerHTML = rows.length === 0
        ? `<span class="hint">no completed runs yet — reach a goal</span>`
        : rows.map((e, i) =>
            `<div><span class="rank">${i + 1}</span><b>${esc(e.playerName)}</b> `
            + `<span class="score">${e.score}</span> `
            + `<span>&middot; ${e.moveCount} moves &middot; ${(e.elapsedMs / 1000).toFixed(1)}s</span>`
            + (!mazeScoped && e.mazeGeneratorId
                ? ` <span>&middot; ${esc(e.mazeGeneratorId)}</span>` : "")
            + `</div>`
          ).join("");
  } catch (e) {
    $("lb").textContent = "leaderboard unavailable";
  }
}

// ---------- REST ----------
const TOKEN_KEY = "daedalus.token";
const USER_KEY = "daedalus.user";

function renderAuth() {
  const in_ = !!state.token;
  $("user").hidden = in_;
  $("pass").hidden = in_;
  $("login").hidden = in_;
  $("authWho").hidden = !in_;
  $("logout").hidden = !in_;
  $("authWho").textContent = in_ ? state.user : "";
}

async function login() {
  const username = $("user").value.trim();
  const password = $("pass").value;
  if (!username || !password) {
    log("err", "sign in needs a username and password");
    return;
  }
  const r = await api("/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username, password}),
  });
  state.token = r.token;
  state.user = username;
  sessionStorage.setItem(TOKEN_KEY, r.token);
  sessionStorage.setItem(USER_KEY, username);
  $("pass").value = "";
  renderAuth();
  log("state", `signed in as ${username} — token attached to REST and STOMP`);
  // CONNECT is when the principal is established (ADR-012). A socket opened
  // before login has no subject, so join-with-token would still be a seat without a feed.
  connectStomp();
  refreshPlugins();
}

function logout() {
  const who = state.user;
  state.token = null;
  state.user = null;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  renderAuth();
  if (who) $("user").value = who;
  log("state", "signed out");
  connectStomp();
  refreshPlugins();
}

/** RFC 7807 + fetch live in api.js. Wrappers keep leftover-state name pins. */
const CAPACITY_WHY = DaedalusApi.CAPACITY_WHY;
const GONE_WHY = DaedalusApi.GONE_WHY;
const BUDGET_WHY = DaedalusApi.BUDGET_WHY;
async function problemWhy(res) { return DaedalusApi.problemWhy(res); }
function nameCapacity(msg) { return DaedalusApi.nameCapacity(msg); }
function nameGone(msg) { return DaedalusApi.nameGone(msg); }
function nameBudget(msg) { return DaedalusApi.nameBudget(msg); }
function permalinkLoadFailed(getErr, rebuildErr) {
  return DaedalusApi.permalinkLoadFailed(getErr, rebuildErr);
}
async function api(path, opts) { return DaedalusApi.request(path, opts, state.token); }
async function apiPlain(path) { return DaedalusApi.requestPlain(path, state.token); }

/** Host bags for extracted coordinators. Built at call time so leftover helpers can stay below. */
function liveHost() {
  return {
    $, log,
    startSpectatePolling, startTrafficPolling, onTrafficPulse,
    applyMove, refreshPlugins, refreshLivingMaze,
  };
}
function sessionHost() {
  return {
    $, api, log, esc, draw,
    leaveSpectate, setGodModeEnabled, pinHash, resubscribe, summonGhost,
    nameGone, flashStatus, refreshTourStatus, tourVerdict,
    refreshLeaderboard, onStageCleared,
    bumpAnim() { DaedalusSolve.bump(); },
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}
function fogHost() {
  return {
    $, api, log, esc, draw,
    leaveSpectate, setGodModeEnabled, pinHash, resubscribe,
    bumpAnim() { DaedalusSolve.bump(); },
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}

function connectStomp() { return DaedalusLive.connect(state, liveHost()); }
function armStompFallbacks() { return DaedalusLive.armFallbacks(state, liveHost()); }
function resubscribe() { return DaedalusLive.resubscribe(state, liveHost()); }
function startLivePolling(mazeId, tickMillis, ticks) {
  return DaedalusLive.startPolling(state, liveHost(), mazeId, tickMillis, ticks);
}
async function onMutation(m) { return DaedalusLive.applyMutation(state, liveHost(), m); }

async function play() { return DaedalusSession.open(state, sessionHost()); }
async function join() { return DaedalusSession.joinSeat(state, sessionHost()); }
async function move(name, dr, dc) { return DaedalusSession.hop(state, sessionHost(), name, dr, dc); }
function applyMove(who, to, from) { return DaedalusSession.apply(state, sessionHost(), who, to, from); }
async function confirmWin(who) { return DaedalusSession.confirm(state, sessionHost(), who); }
function declareWin(who) { return DaedalusSession.declare(state, sessionHost(), who); }

function applyFogView(view) { return DaedalusFogWalk.applyView(state, view); }
function carveFogOpenings(view) { return DaedalusFogWalk.carveOpenings(state, view); }
async function startFog() { return DaedalusFogWalk.start(state, fogHost()); }
async function fogStep(dr, dc) { return DaedalusFogWalk.step(state, fogHost(), dr, dc); }

function mintHost() {
  return {
    $, api, log, esc, draw,
    leaveSpectate, setGodModeEnabled, pinHash, resubscribe,
    refreshLeaderboard, updateInfo, syncBraid,
    bumpAnim() { DaedalusSolve.bump(); },
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}
function campaignHost() {
  return {
    $, api, log, esc,
    leaveSpectate, setGodModeEnabled, pinHash, adoptMaze, play,
    startLivePolling, refreshLeaderboard,
  };
}

function applyHotspotsFromMaze(maze) { return DaedalusMint.applySpots(state, mintHost(), maze); }
function applyBraidFromMaze(maze) { return DaedalusMint.applyBraid(state, mintHost(), maze); }
function adoptMaze(maze, roundTripMs, sourceLabel) {
  return DaedalusMint.adopt(state, mintHost(), maze, roundTripMs, sourceLabel);
}
async function generate(opts) { return DaedalusMint.mint(state, mintHost(), opts); }
async function loadDaily() { return DaedalusMint.daily(state, mintHost()); }
async function crossbreed() { return DaedalusMint.breed(state, mintHost()); }

async function loadCampaign(seed, stage) {
  return DaedalusCampaign.load(state, campaignHost(), seed, stage);
}
function leaveCampaign() { return DaedalusCampaign.leave(state, campaignHost()); }
function renderCampaign() { return DaedalusCampaign.render(state, campaignHost()); }
function onStageCleared() { return DaedalusCampaign.onCleared(state, campaignHost()); }
async function playStage(index) { return DaedalusCampaign.playRung(state, campaignHost(), index); }

function theoryHost() {
  return {
    $, api, log, esc, draw,
    leaveSpectate, showAscii,
    bumpAnim() { DaedalusSolve.bump(); },
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}
async function fingerprintWhenReady(id) {
  return DaedalusTheory.waitFingerprint(state, theoryHost(), id);
}
async function identifyGenerator() { return DaedalusTheory.identify(state, theoryHost()); }
function paintFingerprintCaption(f) { return DaedalusTheory.paintFingerprint(state, theoryHost(), f); }
async function analyzeStructure() { return DaedalusTheory.analyze(state, theoryHost()); }
function paintAnalysisCaption(a) { return DaedalusTheory.paintAnalysis(state, theoryHost(), a); }
async function hardestRoute() { return DaedalusTheory.hardest(state, theoryHost()); }
function paintHardestCaption(h) { return DaedalusTheory.paintHardest(state, theoryHost(), h); }
async function distanceHeatMap() { return DaedalusTheory.heat(state, theoryHost()); }
function paintFieldCaption(f) { return DaedalusTheory.paintField(state, theoryHost(), f); }
async function placeSanctuaries() { return DaedalusTheory.sanctuaries(state, theoryHost()); }
function paintSanctuariesCaption(s) { return DaedalusTheory.paintSanctuaries(state, theoryHost(), s); }
async function heuristicLens() { return DaedalusTheory.lens(state, theoryHost()); }
function paintLensCaption(l) { return DaedalusTheory.paintLens(state, theoryHost(), l); }
async function refreshTheoryOverlays(forMaze, stale) {
  return DaedalusTheory.refreshOverlays(state, theoryHost(), forMaze, stale);
}

function huntHost() {
  return {
    $, api, log, esc, draw,
    refuseSpectatorWrite, play,
    bumpAnim() { DaedalusSolve.bump(); },
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}
async function startTour() { return DaedalusHunt.start(state, huntHost()); }
async function refreshTourStatus() { return DaedalusHunt.refresh(state, huntHost()); }
async function tourVerdict() { return DaedalusHunt.verdict(state, huntHost()); }

function solveHost() {
  return {
    $, api, log, esc, draw,
    leaveSpectate,
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}
async function solve() { return DaedalusSolve.run(state, solveHost()); }
function animateSearch() { return DaedalusSolve.search(state, solveHost()); }
function animatePath() { return DaedalusSolve.path(state, solveHost()); }
async function raceSolvers() { return DaedalusSolve.race(state, solveHost()); }
function animateRace() { return DaedalusSolve.raceTick(state, solveHost()); }
function raceSummary() { return DaedalusSolve.summary(state, solveHost()); }
async function compareSolvers() { return DaedalusSolve.compare(state, solveHost()); }

function spectateHost() {
  return {
    $, api, log, esc, draw, drawEmpty,
    updateInfo, syncBraid, generate,
    leaveCampaign, playStage, loadCampaign, loadDaily, adoptMaze,
    setGodModeEnabled, resubscribe, refreshLeaderboard,
    permalinkLoadFailed, nameGone, summonGhost,
    bumpAnim() { DaedalusSolve.bump(); },
    clearStatusFlash() { clearTimeout(statusFlashTimer); statusFlashTimer = null; },
  };
}
function applyRecipeToForm(h) { return DaedalusSpectate.applyRecipe(state, spectateHost(), h); }
async function rebuildFromRecipe(h) { return DaedalusSpectate.rebuild(state, spectateHost(), h); }
function currentPermalink() { return DaedalusSpectate.permalink(state, spectateHost()); }
function pinHash() { return DaedalusSpectate.pin(state, spectateHost()); }
function hashShowsCurrent() { return DaedalusSpectate.showsCurrent(state, spectateHost()); }
function leaveSpectate() { return DaedalusSpectate.leaveWatch(state, spectateHost()); }
function armSpectatorWrites(on) { return DaedalusSpectate.armWrites(state, spectateHost(), on); }
function refuseSpectatorWrite(what) { return DaedalusSpectate.refuseWrite(state, spectateHost(), what); }
function leaveMaze() { return DaedalusSpectate.leave(state, spectateHost()); }
async function loadFromHash() { return DaedalusSpectate.load(state, spectateHost()); }
async function spectate(sessionId) { return DaedalusSpectate.watch(state, spectateHost(), sessionId); }
function startSpectatePolling() { return DaedalusSpectate.startPolling(state, spectateHost()); }
function adoptSessionView(view) { return DaedalusSpectate.adoptView(state, spectateHost(), view); }
async function hydrateSpectatorOverlays(view) {
  return DaedalusSpectate.hydrate(state, spectateHost(), view);
}

async function refreshPlugins() {
  try {
    const list = await api("/plugins");
    if (!list.length) {
      $("pluginBox").textContent = "no external plugins loaded";
      return;
    }
    $("pluginBox").innerHTML = list.map(p => {
      const m = p.manifest || {};
      const err = p.error ? ` — ${esc(p.error)}` : "";
      const desc = m.description ? `<div class="hint">${esc(m.description)}</div>` : "";
      return `<div><b>${esc(m.displayName || p.id)}</b> `
          + `<span class="rank">${esc(p.state)}</span> `
          + `${esc(m.version || "")}${err}${desc}</div>`;
    }).join("");
  } catch (e) {
    $("pluginBox").textContent = "plugins unavailable — sign in if this is prod";
  }
}

async function showAscii() {
  if (!state.maze || state.fog) return;
  // A text/plain dump of the maze on screen, not a leave path and not a solve.
  // Living ticks refresh this pre; dropping watch here re-armed Bring to life
  // mid-erosion. A solver query ran the solver and published MazeSolvedEvent
  // on a read.
  const mazeId = state.maze.id;
  const art = await apiPlain(`/maze/${mazeId}`);
  // Fog emptied the pre (N18). Generate mid-flight: the old dump
  // would paint the maze now on screen. Discard — same as N18 / N30.
  if (state.fog) return;
  if (!state.maze || state.maze.id !== mazeId) return;
  const out = $("asciiOut");
  out.hidden = false;
  out.textContent = art;
  log("state", `ASCII via Accept: text/plain (${art.length} chars)`);
}

async function loadAlgorithms() {
  const all = await api("/algorithms");
  for (const [selId, list] of [["generator", all.generators], ["solver", all.solvers]]) {
    const sel = $(selId);
    sel.innerHTML = "";
    list.sort((a, b) => a.id.localeCompare(b.id)).forEach(a => {
      state.algos[a.id] = a;
      const o = document.createElement("option");
      o.value = a.id; o.textContent = a.displayName || a.id;
      sel.appendChild(o);
    });
  }
  $("generator").value = "recursive-backtracker";
  $("solver").value = "bfs";
  const lbGen = $("lbGen");
  const keep = lbGen.value;
  lbGen.innerHTML = "";
  const allOpt = document.createElement("option");
  allOpt.value = ""; allOpt.textContent = "all generators";
  lbGen.appendChild(allOpt);
  all.generators.slice().sort((a, b) => a.id.localeCompare(b.id)).forEach(a => {
    const o = document.createElement("option");
    o.value = a.id; o.textContent = a.displayName || a.id;
    lbGen.appendChild(o);
  });
  if ([...lbGen.options].some(o => o.value === keep)) lbGen.value = keep;
  // The arena's rival lane gets the same solver roster.
  const rival = $("rival");
  rival.innerHTML = "";
  all.solvers.sort((a, b) => a.id.localeCompare(b.id)).forEach(a => {
    const o = document.createElement("option");
    o.value = a.id; o.textContent = a.displayName || a.id;
    rival.appendChild(o);
  });
  rival.value = "astar";
  updateInfo();
}

/** The catalog ships bias notes and complexity for every algorithm — show them off. */
function updateInfo() {
  for (const [selId, infoId] of [["generator", "genInfo"], ["solver", "solInfo"]]) {
    const a = state.algos[$(selId).value];
    $(infoId).innerHTML = !a ? "" :
        `<b>${esc(a.displayName)}</b> &middot; ${esc(a.complexity || "")}<br>`
        + `${esc(a.biasNote || a.description || "")}`;
  }
}
$("generator").addEventListener("change", updateInfo);
$("solver").addEventListener("change", updateInfo);
$("lbGen").addEventListener("change", () => { refreshLeaderboard(); pinHash(); });

/** One braid factor. Generate and the tournament used to have two selects that
 *  could disagree — Load it then rebuilt a different maze than the ranking. */
function braidFactor() {
  return ($("braid") && $("braid").value) || ($("tourBraid") && $("tourBraid").value) || "0";
}

function syncBraid(fromId) {
  const src = $(fromId);
  if (!src) return;
  const v = src.value;
  ["braid", "tourBraid"].forEach(id => {
    const el = $(id);
    if (!el || id === fromId) return;
    if (![...el.options].some(o => o.value === v)) {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v + " — from tournament";
      el.appendChild(o);
    }
    el.value = v;
  });
}

if ($("braid")) $("braid").addEventListener("change", () => syncBraid("braid"));
if ($("tourBraid")) $("tourBraid").addEventListener("change", () => syncBraid("tourBraid"));

function mulberry32(a) { return DaedalusShare.rng32(a); }
function placeHotspots(rows, cols, count, seed, cost) {
  return DaedalusShare.placeSpots(rows, cols, count, seed, cost);
}

/**
 * Buttons whose paint draw() swallows while fog is on. Living, play, and
 * generate stay armed — those are how you leave the walk or keep eroding
 * without a god-mode GET /maze.
 */
const GOD_MODE = ["solve", "compare", "race", "tour", "fingerprint", "analyze",
    "hardest", "heatmap", "sanctuaries", "lens", "ascii"];

function setGodModeEnabled(on) {
  GOD_MODE.forEach(id => { const el = $(id); if (el) el.disabled = !on; });
}

// Snapshot whatever is on the canvas at click time — path overlays and players included.
$("pngExport").addEventListener("click", function refresh() {
  this.href = $("maze").toDataURL("image/png");
});

/**
 * Shareable address-bar state. adoptMaze used to write #maze= unconditionally, which
 * turned a campaign link into a mute maze, a daily into an unscoped board, and a
 * spectator refresh into "just this topology". One writer, one reader.
 *
 * Exclusive kinds, first match wins: session, campaign, daily, maze, generator.
 */
function parseHash() {
  return DaedalusShare.readHash(location.hash);
}

/** Seed and optional stage from `#campaign=SEED` / `#campaign=SEED:N`. Missing stage is 0. */
function parseCampaignToken(h) {
  return DaedalusShare.campaignToken(h);
}

/** Recipe that rebuilds this maze when the cached id is gone. `g` not `generator` —
 *  `#generator=` is its own permalink kind (the partition), not a field on `#maze=`. */
function recipeParts(maze) {
  return DaedalusShare.mazeRecipe(maze);
}

// Spectate / hash leftover writes live in spectate.js (DaedalusSpectate).

/** Who this tab moves — join-from-spectate keeps primary as the opener. */
function thisTabSeat() {
  return DaedalusSeat.whoMoves(state.session, state.seat);
}

window.addEventListener("hashchange", () => {
  loadFromHash().catch(e => log("err", e.message));
});

// Spectator leftover writes live in spectate.js (DaedalusSpectate).

/** Maze start plus every recorded `to` — one player's 4-walk. */
function sessionWalk(start, moves) {
  return DaedalusShare.walkFromMoves(start, moves);
}

function mazeStart(maze) {
  return DaedalusShare.startFromTiles(maze && maze.tiles);
}

// ---------- living mazes (ADR-006) ----------
/**
 * Ask the server to erode this maze in place. Progress arrives as MutationFrames on the
 * /state topic; without STOMP (CDN blocked / offline) we fall back to polling at the
 * server-reported tick interval, so the maze still visibly lives.
 */
async function bringToLife() {
  if (refuseSpectatorWrite("bring the maze to life")) return;
  if ($("live").disabled) {
    log("err", "already alive — Harden only applies on the first Bring to life");
    return;
  }
  const harden = $("harden") && $("harden").checked;
  const mazeId = state.maze.id;
  const q = `/maze/${mazeId}/live?ticks=30` + (harden ? "&seal=0.08" : "");
  let r;
  try {
    r = await api(q, {method: "POST"});
  } catch (e) {
    const why = nameCapacity(e.message);
    if (why) {
      log("err", why);
      return;
    }
    throw e;
  }
  // Generate / Daily / Campaign / Breed replaced the maze while
  // this POST was out. Disabling #live and arming a poller would
  // bind the maze now on screen — the one that is gone. Fog stays:
  // living under fog is honest (N19 / Q2).
  if (!state.maze || state.maze.id !== mazeId) return;
  $("live").disabled = true;
  if ($("harden")) $("harden").disabled = true;
  log("state", `maze is alive — ${r.ticksRequested} ticks`
      + (harden ? " (eroding and hardening)" : " (erosion only)")
      + `, one every ${(r.tickMillis / 1000).toFixed(1)}s`);
  if (!state.stomp) startLivePolling(mazeId, r.tickMillis, r.ticksRequested);
}

// ---------- complexity lab (ADR-007 idea 2) ----------
// One series (the measurements) plus a de-emphasised model overlay (the fitted curve), on
// log-log axes so a power law reads as a straight line and its slope IS the exponent.
// Colour: a single in-band step of the app's blue, validated against this panel's surface
// (#1a2026) — the app's lighter #82b1ff sits outside the dark-mode lightness band.
const LAB_SERIES = "#4f83d6";

async function loadLabMetrics() {
  try {
    const metrics = await api("/complexity/metrics");
    const sel = $("labMetric");
    sel.innerHTML = "";
    metrics.forEach(m => {
      const o = document.createElement("option");
      o.value = m; o.textContent = m;
      sel.appendChild(o);
    });
    sel.value = metrics.includes("maxFrontierSize") ? "maxFrontierSize" : metrics[0];
  } catch (e) { /* lab is optional; the rest of the UI does not depend on it */ }
}

async function measureGrowth() {
  // Sidebar lab read — does not adopt, paint, or drop watch.
  const generator = $("generator").value;
  const metric = $("labMetric").value;
  $("labOut").textContent = `measuring ${generator}…`;
  const fit = await api(`/complexity?generator=${encodeURIComponent(generator)}`
      + `&metric=${encodeURIComponent(metric)}`);
  renderLab(fit);
  log("state", `complexity: ${fit.generatorId} [${fit.metric}] -> ${fit.claimed}`
      + (fit.instrumented ? ` (exponent ${fit.exponent}, R² ${fit.rSquared})` : ""));
}

function renderLab(fit) {
  const box = $("labOut");
  if (!fit.instrumented) {
    box.innerHTML = `<div><b>${esc(fit.generatorId)}</b> · ${esc(fit.metric)}: `
        + `<b>not reported</b></div><div class="hint" style="margin-top:4px">${esc(fit.note)}</div>`;
    return;
  }
  box.innerHTML =
      `<div style="margin-bottom:2px"><b>${esc(fit.generatorId)}</b> · ${esc(fit.metric)}</div>`
    + `<div style="font-size:20px;color:${LAB_SERIES};line-height:1.2">${esc(fit.claimed)}</div>`
    + `<div class="hint">exponent ${fit.exponent} · R² ${fit.rSquared} · ${fit.points} sizes</div>`
    + growthChart(fit)
    + `<details style="margin-top:6px"><summary class="hint">measured points</summary>`
    + `<table style="width:100%;font-size:11px;margin-top:4px">`
    + `<tr class="hint"><th align="left">size</th><th align="right">cells</th>`
    + `<th align="right">${esc(fit.metric)}</th></tr>`
    + fit.measured.map(m => `<tr><td>${m.size}×${m.size}</td><td align="right">${m.cells}</td>`
        + `<td align="right">${m.value}</td></tr>`).join("")
    + `</table></details>`
    + `<div class="hint" style="margin-top:6px">${esc(fit.note)}</div>`;
  wireChartHover(fit);
}

/** Log-log scatter+line: on these axes a power law is a straight line whose slope is the exponent. */
function growthChart(fit) {
  return DaedalusLab.chartSvg(fit, LAB_SERIES, esc);
}

/** Per-point hover: an SVG chart is interactive, so it ships with a readout. */
function wireChartHover(fit) {
  DaedalusLab.bindHover(document.querySelectorAll("#labChart .labdot"), $("labTip"), fit);
}

// Hunt leftover writes live in hunt.js (DaedalusHunt).
function sameCell(a, b) { return a && b && a.row === b.row && a.col === b.col; }

// ---------- hardest route (ADR-007 idea 3) ----------
/**
 * The longest simple route from start to goal, drawn over the maze.
 *
 * The honest bit of this feature is the perfect-maze case. A tree has exactly one simple path
 * between two cells, so on 22 of the 23 generators the "hardest" route is the only route and the
 * detour is 1.00 by mathematics, not by a bug. Rather than hide that, the panel says it and
 * points at the operations that make the question interesting — braiding, erosion, dungeons.
 */
// ---------- distance field + sanctuaries (ADR-007 ideas 6 and 5) ----------
/**
 * A sequential ramp: ONE hue, monotone in lightness, with the near-zero end receding into the
 * maze floor rather than competing with it. Distance is a magnitude, so it gets a magnitude
 * encoding — not a rainbow, which would invent boundaries the data does not have. Steps are the
 * validated blue scale; the ramp was checked for single-hue (4 degrees of spread) and monotone
 * lightness against this UI's actual floor colour rather than eyeballed.
 */
const DISTANCE_RAMP = DaedalusCaption.DISTANCE_RAMP;

// ---------- solver tournament (ADR-007 ideas 10 and 7) ----------
/**
 * Rank every solver over a sample, with intervals.
 *
 * The table deliberately leads with spread and ties rather than position. Measured, a single
 * race is already correct on perfect mazes (one solver won 30 of 30) and close to a coin flip on
 * braided ones (the winner split five ways) — so the number worth showing is not "who is first"
 * but "how much does first mean here".
 */
async function runTournament() {
  // Sidebar lab read — Load it goes through generate(), which already leaves.
  const generator = $("generator").value;
  const braid = braidFactor();
  $("tournament").disabled = true;
  $("tourBox").innerHTML = "running the sample…";
  let t;
  try {
    t = await api(`/tournament?generator=${encodeURIComponent(generator)}&size=21&mazes=16`
        + `&braid=${braid}`);
  } finally {
    $("tournament").disabled = false;
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
  $("tourBox").innerHTML = `<table style="width:100%"><tr><th style="text-align:left">solver</th>`
      + `<th>mean work</th><th>95% CI</th><th>spread</th><th>wins</th></tr>${rows}</table>`
      + `<div class="hint" style="margin-top:4px">= marks a solver whose gap to the one below `
      + `it is smaller than the error bars, so the order between them is not a result.</div>`
      + `<div style="margin-top:8px"><b>Statistically tied:</b> ${ties}</div>`
      + (adv ? `<div style="margin-top:6px">Hardest maze for <b>${adv.solver}</b> against `
          + `${adv.rival}: seed <b>${adv.seed}</b> (${adv.solverWork} vs ${adv.rivalWork} cells) — `
          + `<a href="#" id="loadAdversarial">load it</a></div>` : "")
      + `<div class="hint" style="margin-top:6px">${t.note}</div>`;
  const link = $("loadAdversarial");
  if (link && adv) {
    link.onclick = async (e) => {
      e.preventDefault();
      $("generator").value = t.generatorId;
      updateInfo();
      $("seed").value = adv.seed;
      $("rows").value = t.size; $("cols").value = t.size;
      const factor = t.braid == null ? 0 : t.braid;
      if ($("braid")) {
        const v = String(factor);
        if (![...$("braid").options].some(o => o.value === v)) {
          const o = document.createElement("option");
          o.value = v;
          o.textContent = v + " — from tournament";
          $("braid").appendChild(o);
        }
        $("braid").value = v;
      }
      syncBraid("braid");
      await generate({braid: factor});
    };
  }
  log("state", `tournament: ${t.standings.filter(s => !s.excluded).length} solvers over `
      + `${t.mazes} mazes, ${t.ties.length} tied pairs`);
}

// ---------- heuristic lens (ADR-007 idea 8) ----------
/**
 * Three bands, not a gradient of "lying".
 *
 * The obvious version of this feature — shade each cell by how badly the heuristic underestimates
 * it — was measured and thrown away: per-cell error correlates with A*'s wasted expansions
 * anywhere from +0.42 to -0.17, so the picture would have explained nothing. What A* actually
 * obeys is exact: it expands a cell only when f = g* + h is at most the optimal cost. So the
 * overlay draws that partition instead, and the counts underneath it are provable rather than
 * suggestive.
 */
const LENS_COLORS = DaedalusCaption.LENS_COLORS;   // must expand / tie / never

// ---------- ghost runs (ADR-006 idea #8) ----------
/** If this maze has a recorded best run, race it: same pacing, hesitations and all. */
async function summonGhost() {
  if (!state.session) return;
  const mazeId = state.maze && state.maze.id;
  if (!mazeId) return;
  let run;
  try { run = await api(`/maze/${mazeId}/ghost`); }
  catch (ignored) { return; } // 404 — nobody has finished this maze yet
  // Fog dropped the seat and cleared the ghost while this GET was
  // out. Do not re-arm the ticker onto a walk that just emptied it.
  // Generate + Play: a late /ghost would seat the old recording
  // on the maze now on screen (N37). Maze-bound, not seat-bound —
  // a new Play on the same maze still races this recording.
  if (state.fog) return;
  if (!state.session) return;
  if (!state.maze || state.maze.id !== mazeId) return;
  // Recording is a walk from the maze start. A late #session= hydrate used
  // the opener's current cell, so the ghost trail teleported from mid-run.
  const start = mazeStart(state.maze) || state.session.positions[thisTabSeat()];
  state.ghost = {
    moves: run.moves, name: run.playerName, score: run.score, elapsedMs: run.elapsedMs,
    started: performance.now(), pos: start, start, done: false,
  };
  log("player", `ghost summoned: ${run.playerName}'s best run `
      + `(${(run.elapsedMs / 1000).toFixed(1)}s, score ${run.score}) — beat it`);
  clearInterval(state.ghostTimer);
  state.ghostTimer = setInterval(() => {
    const g = state.ghost;
    if (!g || !state.session) { clearInterval(state.ghostTimer); return; }
    const e = performance.now() - g.started;
    let pos = g.pos, done = true;
    for (const m of g.moves) {
      if (m.tMs <= e) pos = m.to;
      else { done = false; break; }
    }
    g.pos = pos;
    if (done && !g.done) {
      g.done = true;
      log("player", `the ghost finished its run (${(g.elapsedMs / 1000).toFixed(1)}s)`);
      clearInterval(state.ghostTimer);
    }
    draw();
  }, 100);
}

// ---------- traffic simulation (ADR-006 idea #3) ----------
/** Track congestion: everywhere you (or agents) walk gets expensive, then cools off. */
async function simulateTraffic() {
  if (refuseSpectatorWrite("track traffic")) return;
  const mazeId = state.maze.id;
  let r;
  try {
    r = await api(`/maze/${mazeId}/traffic`, {method: "POST"});
  } catch (e) {
    const why = nameCapacity(e.message);
    if (why) {
      log("err", why);
      return;
    }
    throw e;
  }
  // Same steal as bringToLife: a late /traffic after Generate
  // must not disable #traffic or arm a poller for the maze now
  // on screen. Fog stays — traffic under fog is honest (Q2).
  if (!state.maze || state.maze.id !== mazeId) return;
  $("traffic").disabled = true;
  log("state", `traffic tracking on — walk around and watch the costs bloom `
      + `(pulse every ${(r.tickMillis / 1000).toFixed(1)}s)`);
  if (!state.stomp) startTrafficPolling(mazeId, r.tickMillis);
}

/** STOMP-less traffic fallback. CONNECT drops this (N44); disconnect re-arms (N45). */
function startTrafficPolling(mazeId, tickMillis = 2000) {
  state.trafficTickMs = tickMillis;
  clearInterval(state.trafficPoll);
  state.trafficPoll = setInterval(async () => {
    if (state.stomp || !state.maze || state.maze.id !== mazeId) {
      clearInterval(state.trafficPoll); state.trafficPoll = null;
      return;
    }
    await refreshLivingMaze(true);
  }, tickMillis);
}

/** A traffic pulse arrived: costs moved — re-fetch, re-solve, redraw (same as mutation). */
async function onTrafficPulse(m) {
  const mazeId = m.mazeId;
  if (!state.maze || state.maze.id !== mazeId) return;
  log("state", m.settled
      ? "traffic fully decayed — tracking retired"
      : `traffic: ${m.congestedCells} congested cell${m.congestedCells === 1 ? "" : "s"}, `
          + `peak cost ${m.peakCost.toFixed(1)}`);
  await refreshLivingMaze();
  if (!state.maze || state.maze.id !== mazeId) return;
  if (m.settled) $("traffic").disabled = false;
}

// Theory overlay refresh lives in theory.js (DaedalusTheory.refreshOverlays).

/** Swap in the latest snapshot without resetting session/solver state (unlike adoptMaze). */
async function refreshLivingMaze(fromPoll) {
  try {
    const before = state.maze;
    // Which maze this refresh is FOR. Every await below is a window in which the player can
    // switch mazes (Daily, a campaign stage, Generate), and a response that lands after that
    // must be dropped rather than applied. Without this the poll's in-flight response
    // reinstates the maze the player just left: reproduced deterministically by delaying the
    // old maze's fetch and loading the daily challenge during it, which left state.maze on
    // the old maze under a "Daily leaderboard" heading — a session opened then would play a
    // different maze than the one being scored.
    const forMaze = state.maze.id;
    const stale = () => !state.maze || state.maze.id !== forMaze;

    // Fog is the agent contract: position, openings, goal. GET /maze is the
    // god-mode grid. Pulling it here would let a living tick paint rooms the
    // walk has never stood in (and openings behind you that you have not
    // re-seen). Re-poll the agent only; carveFogOpenings writes the cell
    // underfoot.
    if (state.fog) {
      const agentId = state.fog.agentId;
      try {
        const v = await api(`/agent/${agentId}`);
        // Play / Open session dropped the walk while this GET was
        // out. Maze id still matches (same maze), so stale() is
        // not enough — applyFogView would recreate state.fog on
        // the session walk. Same class as N26.
        if (stale()) return;
        if (!state.fog || state.fog.agentId !== agentId) return;
        if (fromPoll && state.stomp) return;
        applyFogView(v);
        draw();
        return;
      } catch (gone) {
        if (stale()) return;
        if (!state.fog || state.fog.agentId !== agentId) return;
        // Agent is gone. carveFogOpenings mutated tiles and living ticks
        // skipped GET /maze on purpose — fall through and refetch the live grid.
        state.fog = null;
        setGodModeEnabled(true);
        log("err", `fog walk ended: ${gone.message}`);
      }
    }

    const maze = await api(`/maze/${forMaze}`);
    // startFog can land while this snapshot is out. The fog path
    // skipped GET /maze on purpose; a late assign would write the
    // god-mode grid — unseen rooms and openings you have not
    // re-seen — into that walk. Discard, matching N18.
    if (stale() || state.fog) return;
    if (fromPoll && state.stomp) return;
    state.maze = maze;
    // Narrate on the polling path too. Tick/pulse messages normally come from STOMP frames,
    // so with the broker unreachable a living or congested maze changed under the player in
    // total silence — worst exactly where hazards matter most, the late campaign stages.
    if (!state.stomp && before && before.id === maze.id) {
      const walls = t => t.reduce((n, row) => n + (row.match(/#/g) || []).length, 0);
      const openedNow = walls(before.tiles) - walls(maze.tiles);
      const congestedNow = (maze.hotspots || []).length;
      const congestedBefore = (before.hotspots || []).length;
      if (openedNow > 0) {
        log("state", `erosion: ${openedNow} wall${openedNow === 1 ? "" : "s"} opened`);
      }
      if (congestedNow !== congestedBefore) {
        log("state", `traffic: ${congestedNow} congested cell${congestedNow === 1 ? "" : "s"}`);
      }
    }
    if (!(await refreshTheoryOverlays(forMaze, stale))) return;
    if (state.tour) {
      // Placement is frozen; the optimum is not (ADR-014). A seated
      // session — player or spectator — must rescore via
      // GET /session/{id}/tour. That read already reruns Held-Karp on
      // the live grid, and it is the public paint source. The old
      // body always asked GET /maze/{id}/tour (tourFor): auth-required
      // in prod, and it can mint. Spectator hydrate already used the
      // session read; a living tick then 401'd and kept a stale
      // optimum on the watched hunt (N42). Maze tour is only the
      // Hunt-before-Play fallback, when no seat exists to progress.
      try {
        if (state.session) {
          const sessionId = state.session.id;
          const p = await api(`/session/${sessionId}/tour`);
          if (stale() || state.fog) return;
          if (!state.session || state.session.id !== sessionId) return;
          if (p.optimal !== state.tour.optimalCost) {
            log("state", `tour optimum is now ${p.optimal} steps (was ${state.tour.optimalCost})`);
          }
          state.tour = {
            waypoints: p.waypoints,
            path: p.path || [],
            optimalCost: p.optimal,
            feasible: true,
          };
        } else {
          const t = await api(`/maze/${forMaze}/tour?count=${state.tour.waypoints.length}`);
          if (stale() || state.fog) return;
          if (t.optimalCost !== state.tour.optimalCost) {
            log("state", `tour optimum is now ${t.optimalCost} steps (was ${state.tour.optimalCost})`);
          }
          state.tour = t;
        }
        await refreshTourStatus();
        if (stale() || state.fog) return;
      } catch (ignored) { /* tour overlay; losing one refresh is harmless */ }
    }
    if (state.path) {
      // The drawn route may now cross freshly-opened walls or stale costs — re-solve
      // quietly (no replay animation; the mutation itself is the show).
      const r = await api(`/maze/${forMaze}/solve/${$("solver").value}`, {method: "POST"});
      if (stale() || state.fog) return;
      state.path = r.path;
      state.expansions = [];
      state.searchProgress = 1;
      state.pathProgress = 1;
    }
    draw();
  } catch (e) {
    log("err", `living refresh failed: ${e.message}`);
  }
}

// Solve leftover writes live in solve.js (DaedalusSolve).

let statusFlashTimer = null;
function flashStatus(text) {
  const el = $("status"), prev = el.textContent;
  el.textContent = text;
  clearTimeout(statusFlashTimer);
  statusFlashTimer = setTimeout(() => { el.textContent = prev; }, 900);
}


// ---------- rendering ----------
// Geometry and paint live in draw.js. This file snapshots state into a
// scene so leftover overlays cannot hide inside a 300-line draw() that
// reads globals. Smoke pins still look for function draw / drawEmpty.
let geom = null;

function pathRevealMs(n) {
  return DaedalusDraw.pathRevealMs(n);
}

/** The Held-Karp walk the tour scores against — coins are stops; this is the corridor. */
function tourWalk() {
  return (state.tour && state.tour.path) || [];
}

/** The ghost's walked prefix so far — start plus every `to` whose clock has elapsed. */
function ghostWalk() {
  return DaedalusShare.ghostPrefix(state.ghost, performance.now());
}

function cellKey(r, c) { return DaedalusFog.key(r, c); }

function mazeScene() {
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
    tourPath: tourWalk(),
    tour: state.tour,
    tourGot: state.tourGot,
    race: state.race,
    trails: state.trails,
    session: state.session,
    ghostWalk: ghostWalk(),
    ghost: state.ghost,
    won: state.won,
    distanceRamp: DISTANCE_RAMP,
    lensColors: LENS_COLORS,
  };
}

function draw() {
  if (!state.maze) return;
  geom = DaedalusDraw.paint($("maze"), mazeScene());
}

// Click (or tap) an adjacent cell to move — session first, then the fog agent.
$("maze").addEventListener("click", ev => {
  if (!geom) return;
  const rect = $("maze").getBoundingClientRect();
  const scale = $("maze").width / rect.width; // canvas may be CSS-shrunk by max-width
  const x = (ev.clientX - rect.left) * scale, y = (ev.clientY - rect.top) * scale;
  const hit = DaedalusDraw.hitCell(geom, x, y);
  if (!hit) return;
  const row = hit.row, col = hit.col;
  if (state.session && !state.won && !state.readOnly) {
    const who = thisTabSeat();
    const at = who && state.session.positions[who];
    if (!at) return;
    const dr = row - at.row, dc = col - at.col;
    if (Math.abs(dr) + Math.abs(dc) === 1) move(who, dr, dc);
    return;
  }
  if (state.fog && !state.fog.arrived && !state.fog.expired) {
    const at = state.fog.position;
    const dr = row - at.row, dc = col - at.col;
    if (Math.abs(dr) + Math.abs(dc) === 1) fogStep(dr, dc).catch(e => log("err", e.message));
  }
});

/** Empty-state canvas: an invitation, not a void. */
function drawEmpty() {
  DaedalusDraw.paintEmpty($("maze"));
}

// ---------- wiring ----------
$("generate").onclick = () => generate().catch(e => log("err", e.message));
$("daily").onclick = () => loadDaily().catch(e => log("err", e.message));
$("breed").onclick = () => crossbreed().catch(e => log("err", e.message));
$("campaign").onclick = () => loadCampaign(null).catch(e => log("err", e.message));
$("solve").onclick = () => solve().catch(e => log("err", e.message));
$("compare").onclick = () => compareSolvers().catch(e => log("err", e.message));
$("live").onclick = () => bringToLife().catch(e => log("err", e.message));
$("traffic").onclick = () => simulateTraffic().catch(e => log("err", e.message));
$("race").onclick = () => raceSolvers().catch(e => log("err", e.message));
$("analyze").onclick = () => analyzeStructure().catch(e => log("err", e.message));
$("hardest").onclick = () => hardestRoute().catch(e => log("err", e.message));
$("heatmap").onclick = () => distanceHeatMap().catch(e => log("err", e.message));
$("sanctuaries").onclick = () => placeSanctuaries().catch(e => log("err", e.message));
$("tournament").onclick = () => runTournament().catch(e => log("err", e.message));
$("lens").onclick = () => heuristicLens().catch(e => log("err", e.message));
$("tour").onclick = () => startTour().catch(e => log("err", e.message));
$("fingerprint").onclick = () => identifyGenerator().catch(e => log("err", e.message));
$("measure").onclick = () => measureGrowth().catch(e => {
  log("err", e.message); $("labOut").textContent = "measurement failed — see the log";
});
$("play").onclick = () => play().catch(e => log("err", e.message));
$("join").onclick = () => join();
$("fog").onclick = () => startFog().catch(e => log("err", e.message));
$("ascii").onclick = () => showAscii().catch(e => log("err", e.message));
$("auth").addEventListener("submit", e => {
  e.preventDefault();
  login().catch(err => log("err", err.message));
});
$("logout").onclick = logout;
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  const arrows = {ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1]};
  if (state.session && !state.readOnly) {
    const wasd = {KeyW: [-1, 0], KeyS: [1, 0], KeyA: [0, -1], KeyD: [0, 1]};
    if (arrows[e.key]) {
      e.preventDefault();
      move(thisTabSeat(), ...arrows[e.key]);
    } else if (state.joined && state.joined !== state.seat && wasd[e.code]) {
      e.preventDefault();
      move(state.joined, ...wasd[e.code]);
    }
    return;
  }
  if (state.fog && arrows[e.key]) {
    e.preventDefault();
    fogStep(...arrows[e.key]).catch(err => log("err", err.message));
  }
});

state.token = sessionStorage.getItem(TOKEN_KEY);
state.user = sessionStorage.getItem(USER_KEY);
renderAuth();
drawEmpty();
refreshLeaderboard();
refreshPlugins();
loadLabMetrics();
loadAlgorithms().then(connectStomp).then(loadFromHash).catch(e => log("err", e.message));
