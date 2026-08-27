// SPDX-License-Identifier: MIT
// Operator-desk leftover rules (auth, board, catalog). app.js owns leftover-state
// wiring; this file does not read `state`.
"use strict";
(function (global) {
  const TOKEN_KEY = "daedalus.token";
  const USER_KEY = "daedalus.user";

  /** Buttons whose paint draw() swallows while fog is on. Living, play, and
   *  generate stay armed — those are how you leave the walk or keep eroding
   *  without a god-mode GET /maze. */
  const GOD_MODE = ["solve", "compare", "race", "tour", "fingerprint", "analyze",
      "hardest", "heatmap", "sanctuaries", "lens", "ascii"];

  function restore(state) {
    state.token = sessionStorage.getItem(TOKEN_KEY);
    state.user = sessionStorage.getItem(USER_KEY);
  }

  // A shared maze gets its own board: the daily challenge, or a campaign stage. You compete
  // against everyone who played that same topology, not against the world's easiest mazes.
  function mazeScope(state) {
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
  function request(state, host) {
    const maze = mazeScope(state);
    const generator = host.$("lbGen") ? host.$("lbGen").value : "";
    if (maze) return {path: `/leaderboard?n=10&maze=${maze}`, maze, generator: ""};
    if (generator) {
      return {path: `/leaderboard?n=10&generator=${encodeURIComponent(generator)}`,
              maze: null, generator};
    }
    return {path: "/leaderboard?n=10", maze: null, generator: ""};
  }

  async function refresh(state, host) {
    try {
      const req = request(state, host);
      const rows = await host.api(req.path);
      if (request(state, host).path !== req.path) return; // scope changed in flight
      state.lbQuery = req.path; // what we actually asked — sweep pins generator= vs maze=
      const mazeScoped = !!req.maze;
      if (host.$("lbGen")) {
        host.$("lbGen").disabled = mazeScoped;
      }
      host.$("lbTitle").textContent = mazeScoped
          ? (req.maze === state.dailyId ? "Daily leaderboard"
              : `Stage ${state.stageIndex + 1} leaderboard`)
          : req.generator
              ? `${(state.algos[req.generator] && state.algos[req.generator].displayName)
                  || req.generator} leaderboard`
              : "Leaderboard";
      host.$("lb").innerHTML = rows.length === 0
          ? `<span class="hint">no completed runs yet — reach a goal</span>`
          : rows.map((e, i) =>
              `<div><span class="rank">${i + 1}</span><b>${host.esc(e.playerName)}</b> `
              + `<span class="score">${e.score}</span> `
              + `<span>&middot; ${e.moveCount} moves &middot; ${(e.elapsedMs / 1000).toFixed(1)}s</span>`
              + (!mazeScoped && e.mazeGeneratorId
                  ? ` <span>&middot; ${host.esc(e.mazeGeneratorId)}</span>` : "")
              + `</div>`
            ).join("");
    } catch (e) {
      host.$("lb").textContent = "leaderboard unavailable";
    }
  }

  function renderAuth(state, host) {
    const in_ = !!state.token;
    host.$("user").hidden = in_;
    host.$("pass").hidden = in_;
    host.$("login").hidden = in_;
    host.$("authWho").hidden = !in_;
    host.$("logout").hidden = !in_;
    host.$("authWho").textContent = in_ ? state.user : "";
  }

  async function login(state, host) {
    const username = host.$("user").value.trim();
    const password = host.$("pass").value;
    if (!username || !password) {
      host.log("err", "sign in needs a username and password");
      return;
    }
    const r = await host.api("/auth/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username, password}),
    });
    state.token = r.token;
    state.user = username;
    sessionStorage.setItem(TOKEN_KEY, r.token);
    sessionStorage.setItem(USER_KEY, username);
    host.$("pass").value = "";
    renderAuth(state, host);
    host.log("state", `signed in as ${username} — token attached to REST and STOMP`);
    // CONNECT is when the principal is established (ADR-012). A socket opened
    // before login has no subject, so join-with-token would still be a seat without a feed.
    host.connectStomp();
    host.refreshPlugins();
  }

  function logout(state, host) {
    const who = state.user;
    state.token = null;
    state.user = null;
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    renderAuth(state, host);
    if (who) host.$("user").value = who;
    host.log("state", "signed out");
    host.connectStomp();
    host.refreshPlugins();
  }

  async function plugins(state, host) {
    try {
      const list = await host.api("/plugins");
      if (!list.length) {
        host.$("pluginBox").textContent = "no external plugins loaded";
        return;
      }
      host.$("pluginBox").innerHTML = list.map(p => {
        const m = p.manifest || {};
        const err = p.error ? ` — ${host.esc(p.error)}` : "";
        const desc = m.description ? `<div class="hint">${host.esc(m.description)}</div>` : "";
        return `<div><b>${host.esc(m.displayName || p.id)}</b> `
            + `<span class="rank">${host.esc(p.state)}</span> `
            + `${host.esc(m.version || "")}${err}${desc}</div>`;
      }).join("");
    } catch (e) {
      host.$("pluginBox").textContent = "plugins unavailable — sign in if this is prod";
    }
  }

  async function ascii(state, host) {
    if (!state.maze || state.fog) return;
    // A text/plain dump of the maze on screen, not a leave path and not a solve.
    // Living ticks refresh this pre; dropping watch here re-armed Bring to life
    // mid-erosion. A solver query ran the solver and published MazeSolvedEvent
    // on a read.
    const mazeId = state.maze.id;
    const art = await host.apiPlain(`/maze/${mazeId}`);
    // Fog emptied the pre (N18). Generate mid-flight: the old dump
    // would paint the maze now on screen. Discard — same as N18 / N30.
    if (state.fog) return;
    if (!state.maze || state.maze.id !== mazeId) return;
    const out = host.$("asciiOut");
    out.hidden = false;
    out.textContent = art;
    host.log("state", `ASCII via Accept: text/plain (${art.length} chars)`);
  }

  async function algorithms(state, host) {
    const all = await host.api("/algorithms");
    for (const [selId, list] of [["generator", all.generators], ["solver", all.solvers]]) {
      const sel = host.$(selId);
      sel.innerHTML = "";
      list.sort((a, b) => a.id.localeCompare(b.id)).forEach(a => {
        state.algos[a.id] = a;
        const o = document.createElement("option");
        o.value = a.id; o.textContent = a.displayName || a.id;
        sel.appendChild(o);
      });
    }
    host.$("generator").value = "recursive-backtracker";
    host.$("solver").value = "bfs";
    const lbGen = host.$("lbGen");
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
    const rival = host.$("rival");
    rival.innerHTML = "";
    all.solvers.sort((a, b) => a.id.localeCompare(b.id)).forEach(a => {
      const o = document.createElement("option");
      o.value = a.id; o.textContent = a.displayName || a.id;
      rival.appendChild(o);
    });
    rival.value = "astar";
    host.updateInfo();
  }

  /** Bias on the card; complexity lives on the select title so the maze stays the hero. */
  function updateInfo(state, host) {
    for (const [selId, infoId] of [["generator", "genInfo"], ["solver", "solInfo"]]) {
      const a = state.algos[host.$(selId).value];
      const card = host.$(infoId);
      const sel = host.$(selId);
      if (!a) {
        if (card) card.innerHTML = "";
        if (sel) sel.removeAttribute("title");
        continue;
      }
      if (card) card.innerHTML = host.esc(a.biasNote || a.description || "");
      if (sel) sel.title = [a.displayName, a.complexity].filter(Boolean).join(" · ");
    }
  }

  /** One braid factor. Generate and the tournament used to have two selects that
   *  could disagree — Load it then rebuilt a different maze than the ranking. */
  function braidFactor(host) {
    return (host.$("braid") && host.$("braid").value)
        || (host.$("tourBraid") && host.$("tourBraid").value) || "0";
  }

  function syncBraid(host, fromId) {
    const src = host.$(fromId);
    if (!src) return;
    const v = src.value;
    ["braid", "tourBraid"].forEach(id => {
      const el = host.$(id);
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

  function setGodModeEnabled(host, on) {
    GOD_MODE.forEach(id => { const el = host.$(id); if (el) el.disabled = !on; });
  }

  global.DaedalusDesk = {
    TOKEN_KEY, USER_KEY, GOD_MODE,
    restore, mazeScope, request, refresh,
    renderAuth, login, logout, plugins, ascii, algorithms, updateInfo,
    braidFactor, syncBraid, setGodModeEnabled,
  };
})(window);
