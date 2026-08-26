// SPDX-License-Identifier: MIT
// Campaign leftover rules. app.js owns leftover-state wiring; this file does not read `state`.
"use strict";
(function (global) {
  /**
   * Load a campaign and render its ladder. Everything a stage needs already exists as an
   * endpoint — the maze by id, its own leaderboard partition, its ghost, its hazards — so the
   * campaign is a table of contents, not a new game mode.
   */
  async function load(state, host, seed, stage) {
    host.leaveSpectate();
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    // Generate mid-flight: installing the ladder then playStage
    // would capture the generated id and adopt the stage over it
    // (N40). Capture maze id (or none); discard after the GET.
    // Fog discard stays (N21).
    const mazeId = state.maze && state.maze.id;
    const c = await host.api(`/campaign${seed != null ? "?seed=" + seed : ""}`);
    if (state.fog) return;
    if (state.maze && state.maze.id !== mazeId) return;
    if (!state.maze && mazeId) return;
    state.campaign = c;
    state.cleared = {};
    render(state, host);
    host.log("state", `campaign ${c.seed} — ${c.stages.length} stages, `
        + `${c.stages[0].grade.label} to ${c.stages[c.stages.length - 1].grade.label} `
        + `(share: ${location.origin}${location.pathname}#campaign=${c.seed})`);
    const index = Number.isInteger(stage) && stage >= 0 && stage < c.stages.length ? stage : 0;
    await playRung(state, host, index);
  }

  /** Drop the ladder so a leftover stage click cannot play a maze the bar does not name. */
  function leave(state, host) {
    state.campaign = null;
    state.stageIndex = null;
    state.cleared = {};
    host.$("campaignBox").innerHTML = "six stages, gentle to brutal — hazards ramp in late";
  }

  function render(state, host) {
    const c = state.campaign;
    if (!c) return;
    host.$("campaignBox").innerHTML = c.stages.map(s => {
      const active = s.index === state.stageIndex;
      const done = state.cleared[s.index];
      const hazards = s.hazards.length ? ` · ${host.esc(s.hazards.join(" + "))}` : "";
      return `<div style="margin:4px 0;padding:4px 6px;border-radius:4px;`
          + `${active ? "background:#1c2531;" : ""}">`
          + `<a href="#" data-stage="${s.index}" style="color:${done ? "#4cc38a" : "#82b1ff"}">`
          + `${done ? "✓" : s.index + 1}. ${host.esc(s.name)}</a> `
          + `<span class="hint">${s.rows}×${s.cols} ${host.esc(s.generatorId)} · `
          + `<b>${host.esc(s.grade.label)}</b> ${s.grade.score}${hazards}</span></div>`;
    }).join("");
    host.$("campaignBox").querySelectorAll("a[data-stage]").forEach(a => {
      a.onclick = ev => {
        ev.preventDefault();
        playRung(state, host, Number(a.dataset.stage)).catch(e => host.log("err", e.message));
      };
    });
  }

  /** Stage cleared: mark it, then offer the next rung (the player chooses when to climb). */
  function onCleared(state, host) {
    const index = state.stageIndex;
    state.cleared[index] = true;
    render(state, host);
    const next = index + 1;
    if (next < state.campaign.stages.length) {
      const s = state.campaign.stages[next];
      host.log("state", `stage ${index + 1} cleared — next: ${s.name} (${s.grade.label})`);
      host.$("status").textContent += ` · stage ${index + 1} cleared — click stage ${next + 1} to continue`;
    } else {
      host.log("state", `campaign complete — all ${state.campaign.stages.length} stages cleared`);
      host.$("status").textContent += " · CAMPAIGN COMPLETE";
    }
  }

  /** Load a stage: its maze, its own leaderboard, its ghost, and the hazards it declares. */
  async function playRung(state, host, index) {
    host.leaveSpectate();
    if (state.fog) {
      state.fog = null;
      host.setGodModeEnabled(true);
    }
    // Canvas we left, not the stage's maze — re-clicking this rung
    // (or climbing to another) still adopts. Generate mid-flight
    // changes the canvas id and the late adopt is discarded (N40).
    // Fog discard stays (N21).
    const mazeId = state.maze && state.maze.id;
    const stage = state.campaign.stages[index];
    const maze = await host.api(`/maze/${stage.mazeId}`);
    if (state.fog) return;
    if (state.maze && state.maze.id !== mazeId) return;
    if (!state.maze && mazeId) return;
    host.adoptMaze(maze, null, `campaign stage ${index + 1}`);
    state.stageIndex = index; // after adoptMaze, which resets per-maze state
    state.dailyId = null;
    host.pinHash();
    render(state, host);
    host.log("state", `stage ${index + 1}/${state.campaign.stages.length} — ${stage.name}: `
        + `${stage.grade.label} (${stage.grade.score}), route ${stage.grade.routeLength} cells, `
        + `${stage.grade.deadEnds} dead ends`);
    await host.play();                       // opens the session (and summons this stage's ghost)
    // Generate won the canvas while play() was out. N29 discarded
    // the UI bind after a late /live; the POST still started the
    // stage you left. Do not mint a ticker on a maze the bar no
    // longer names (N46).
    if (!state.maze || state.maze.id !== stage.mazeId) return;
    for (const hazard of stage.hazards) {
      // Hazard names are domain words; endpoint paths are an API detail and the two do NOT
      // line up ("living" the hazard is served by POST /live). Interpolating the hazard name
      // straight into the path silently 404s every hazard, so the mapping is explicit.
      //
      // hardening is not its own call. A second POST /live joins the existing run and
      // ignores ?seal= (LivingMazeService.start is idempotent per maze). Fold it into
      // living so the finale breathes both ways in one ticker.
      if (hazard === "hardening") continue;
      const livingPath = stage.hazards.includes("hardening")
          ? "live?ticks=30&seal=0.08" : "live?ticks=30";
      const path = {living: livingPath, traffic: "traffic"}[hazard];
      if (!path) { host.log("err", `unknown hazard "${hazard}" — server declares one this client can't start`); continue; }
      if (!state.maze || state.maze.id !== stage.mazeId) return;
      try {
        await host.api(`/maze/${stage.mazeId}/${path}`, {method: "POST"});
        // Generate / Daily / Breed replaced the maze while this POST
        // was out. Disabling #live and arming a poller would bind the
        // maze now on screen. Fog stays — living under fog is honest.
        if (!state.maze || state.maze.id !== stage.mazeId) return;
        host.log("state", `hazard active on this stage: ${hazard}`
            + (hazard === "living" && stage.hazards.includes("hardening") ? " + hardening" : ""));
      } catch (e) {
        host.log("err", `could not start ${hazard}: ${e.message}`);
      }
    }
    if (!state.maze || state.maze.id !== stage.mazeId) return;
    if (stage.hazards.includes("living") || stage.hazards.includes("hardening")) {
      host.$("live").disabled = true;
      if (host.$("harden")) host.$("harden").disabled = true;
      if (!state.stomp) host.startLivePolling(stage.mazeId);
    }
    host.refreshLeaderboard();               // this stage's own board (per-maze partition)
  }

  global.DaedalusCampaign = {load, leave, render, onCleared, playRung};
})(window);
