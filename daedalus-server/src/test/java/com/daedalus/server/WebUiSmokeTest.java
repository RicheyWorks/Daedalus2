// SPDX-License-Identifier: MIT

package com.daedalus.server;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Pins that the static web UI (BACKLOG stretch goal) is actually served. The page is plain
 * static content under {@code resources/static}, which Boot serves by convention — and
 * conventions are exactly what starter upgrades silently change (the lesson
 * {@code ApplicationSmokeTest} exists to teach). Uses the same context configuration as the
 * other smoke tests, so Spring reuses the cached context instead of booting another one.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class WebUiSmokeTest {

    @LocalServerPort
    private int port;

    @Test
    void theWebUiIsServedAtTheRoot() {
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();
        byte[] body = client.get().uri("/index.html").exchange()
                .expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        assertThat(body).isNotNull();
        String html = new String(body);
        // Contract, not implementation: the page talks to the versioned API and the STOMP
        // endpoint, can sign in, open a fog-of-war walk, negotiate ASCII, list plugins,
        // ask the per-generator leaderboard, hydrate a spectator walk from the
        // session snapshot, paint the Held-Karp tour walk, and keep permalink
        // kinds honest, and carve fog openings from the agent rather than
        // GET /maze. If any of those disappear, the UI broke or moved.
        assertThat(html).contains("DAEDALUS").contains("/api/v1").contains("/ws")
                .contains("/auth/login").contains("id=\"login\"").contains("id=\"fog\"")
                .contains("Authorization").contains("text/plain").contains("id=\"ascii\"")
                .contains("/plugins").contains("id=\"pluginBox\"")
                .contains("id=\"lbGen\"").contains("generator=")
                .contains("paintWalk").contains("ghostWalk")
                .contains("sessionWalk").contains("view.walks").contains("#session=")
                .contains("tourWalk").contains("pinHash").contains("parseHash")
                .contains("hydrateSpectatorOverlays").contains("#daily")
                .contains("carveFogOpenings")
                .contains("id=\"braid\"").contains("t.generatorId").contains("t.braid")
                .contains("refreshTheoryOverlays").contains("paintFingerprintCaption")
                .contains("braidFactor").contains("/topic/plugins/failures")
                .contains("maze.braid").contains("applyBraidFromMaze")
                .contains("state.seat").contains("if (state.session) return {session")
                .contains("p.waypoints").contains("fog walk ended")
                .contains("esc(a.displayName)").contains("integrity=")
                .contains("$(\"generator\").value = h.generator")
                .contains("already alive")
                .contains("placeHotspots").contains("applyHotspotsFromMaze")
                .contains("confirmWin").contains("declareWin")
                .contains("problemWhy").contains("every solver failed")
                .contains("aged out of the cache")
                .contains("fingerprintWhenReady").contains("classifier is warming")
                .contains("recipeParts").contains("rebuildFromRecipe")
                .contains("setGodModeEnabled").contains("GOD_MODE")
                .contains("this session already finished")
                .contains("that session is gone")
                .contains("Three frame shapes ride /state")
                .contains("too many mazes are already alive")
                .contains("too many mazes are already tracked")
                .contains("nameCapacity").contains("CAPACITY_WHY")
                .contains("session-capacity").contains("agent-capacity")
                .contains("maze-capacity").contains("tour-capacity")
                .contains("too many sessions are already open")
                .contains("too many fog walks are already open")
                .contains("too many mazes are already cached")
                .contains("too many waypoint hunts are already seated")
                .contains("permalinkLoadFailed")
                .contains("permalink maze aged out —")
                .contains("nameGone").contains("GONE_WHY")
                .contains("that maze is gone")
                .contains("that fog walk is gone")
                .contains("nameBudget").contains("BUDGET_WHY")
                .contains("solver-budget")
                .contains("this solver spent its node budget")
                .contains("nameBudget(raw)")
                .contains("leaveSpectate").contains("thisTabSeat")
                .contains("armSpectatorWrites").contains("refuseSpectatorWrite")
                .contains("hashShowsCurrent").contains("addEventListener(\"hashchange\"")
                .contains("mazeStart(state.maze) || state.session.positions")
                .contains("spectating is read-only")
                .doesNotContain("positions[state.session.primary]")
                .doesNotContain("move(state.session.primary")
                .doesNotContain("move(state.seat || state.session.primary");
        // Fog / Generate / Open session used to write while readOnly was still set.
        // Daily / Campaign / Breed fetched, then adoptMaze cleared watch as a side effect.
        // Solve painted a god-mode overlay on the watched maze.
        // leaveSpectate must run before those fetches, not after (play) or never (fog).
        assertLeaveBeforeWrite(html, "async function generate", "/maze/generate");
        assertLeaveBeforeWrite(html, "async function startFog", "/agent");
        assertLeaveBeforeWrite(html, "async function play", "/session?");
        // Open session pinned #session= and subscribed /player. Fog
        // dropped the seat (N15 pinned the hash) and left the
        // subscription and ghost ticker, so a joiner frame still logged
        // a session move and the ghost still advanced while draw()
        // returned early. resubscribe / ghost clear after the null.
        int fogFrom = html.indexOf("async function startFog");
        int fogTo = html.indexOf("async function fogStep");
        assertThat(fogFrom).isGreaterThanOrEqualTo(0);
        assertThat(fogTo).isGreaterThan(fogFrom);
        String fog = html.substring(fogFrom, fogTo);
        assertThat(fog.indexOf("pinHash()"))
                .isGreaterThan(fog.indexOf("state.session = null"));
        assertThat(fog.indexOf("resubscribe()"))
                .isGreaterThan(fog.indexOf("state.session = null"));
        assertThat(fog.indexOf("clearInterval(state.ghostTimer)"))
                .isGreaterThan(fog.indexOf("state.session = null"));
        // N26. startFog POSTed /agent then always applied. Generate
        // that replaced the maze mid-flight still got the old agent's
        // openings carved into the new tiles. Discard after the POST;
        // startFog still must not null tour.
        int fogMint = fog.indexOf("/agent");
        int fogMazeId = fog.indexOf("mazeId");
        int fogDiscard = fog.indexOf("state.maze.id !== mazeId");
        assertThat(fogMint).isGreaterThanOrEqualTo(0);
        assertThat(fogMazeId).isGreaterThanOrEqualTo(0);
        assertThat(fogMazeId).isLessThan(fogMint);
        assertThat(fogDiscard).isGreaterThan(fogMint);
        assertThat(fog.indexOf("state.session = null")).isGreaterThan(fogDiscard);
        assertThat(fog.indexOf("applyFogView")).isGreaterThan(fogDiscard);
        // Analyze / Compare wrote #compareBox. Fog dropped the overlay
        // objects (N16) and left the sidebar, so a leftover caption still
        // named chokepoints and a leftover compare row could hover-arm a
        // solve path draw() swallowed until Play. Empty after the drop.
        // state.tour stays — same maze, not a GET/mutate under fog.
        assertThat(fog.indexOf("$(\"compareBox\").innerHTML"))
                .isGreaterThan(fog.indexOf("state.session = null"));
        assertThat(fog).doesNotContain("state.tour = null");
        // N17 emptied the sidebar when Fog started. An Analyze /
        // Compare (or Identify / Heat / Lens) that was already out
        // still landed and rewrote #compareBox / armed state.path.
        // Discard after the fetch; startFog still must not null tour.
        assertDiscardAfterFetch(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "paintAnalysisCaption");
        assertDiscardAfterFetch(html, "async function compareSolvers",
                "async function play", "$(\"compareBox\")");
        assertDiscardAfterFetch(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "paintFingerprintCaption");
        assertDiscardAfterFetch(html, "async function distanceHeatMap",
                "function paintFieldCaption", "paintFieldCaption");
        assertDiscardAfterFetch(html, "async function heuristicLens",
                "function paintLensCaption", "paintLensCaption");
        assertDiscardAfterFetch(html, "async function solve",
                "function animateSearch", "state.path");
        // N19. A living refresh that passed the fog gate can still
        // have GET /maze in flight. Fog starts; late state.maze = maze
        // would install the god-mode grid into a walk that skipped
        // that fetch on purpose. Discard after the snapshot; the fog
        // path still must not GET /maze. startFog still must not null tour.
        int liveFrom = html.indexOf("async function refreshLivingMaze");
        int liveTo = html.indexOf("async function solve");
        assertThat(liveFrom).isGreaterThanOrEqualTo(0);
        assertThat(liveTo).isGreaterThan(liveFrom);
        String live = html.substring(liveFrom, liveTo);
        int snap = live.indexOf("await api(`/maze/${forMaze}`)");
        int assign = live.indexOf("state.maze = maze");
        int discard = live.indexOf("if (stale() || state.fog)", snap);
        assertThat(snap).isGreaterThanOrEqualTo(0);
        assertThat(discard).isGreaterThan(snap);
        assertThat(assign).isGreaterThan(discard);
        assertThat(live.substring(live.indexOf("if (state.fog)"), snap))
                .doesNotContain("await api(`/maze/${forMaze}`)");
        // N20. play() snapshotted hadFog, POSTed, then always
        // state.fog = null. A Fog that started mid-flight was "no
        // fog" and the session still pinned #session=. Leave fog
        // before the fetch (play is a leave-fog path); discard the
        // session apply when state.fog is set after the POST.
        // Hunt waypoints → play: discard /tour too, or a late Hunt
        // still calls play() and leaves the walk.
        int playFrom = html.indexOf("async function play()");
        int playTo = html.indexOf("async function join");
        assertThat(playFrom).isGreaterThanOrEqualTo(0);
        assertThat(playTo).isGreaterThan(playFrom);
        String play = html.substring(playFrom, playTo);
        int sessionPost = play.indexOf("/session?");
        int sessionDiscard = play.indexOf("if (state.fog)", sessionPost);
        int sessionApply = play.indexOf("state.session =");
        assertThat(sessionPost).isGreaterThanOrEqualTo(0);
        assertThat(sessionDiscard).isGreaterThan(sessionPost);
        assertThat(sessionApply).isGreaterThan(sessionDiscard);
        assertThat(play.indexOf("pinHash()")).isGreaterThan(sessionDiscard);
        assertThat(play.indexOf("summonGhost()")).isGreaterThan(sessionDiscard);
        assertThat(play.indexOf("resubscribe()")).isGreaterThan(sessionDiscard);
        assertThat(play.indexOf("state.fog = null")).isLessThan(sessionPost);
        assertThat(play).doesNotContain("hadFog");
        assertDiscardAfterFetch(html, "async function startTour",
                "function sameCell", "state.tour = t");
        // N21. Generate / Daily / Campaign / Breed stay armed during
        // fog (leave-walk paths). They fetched, then adoptMaze always
        // replaced the maze, so a generate that was already out still
        // stole the walk. Leave fog before the fetch; discard adopt
        // when state.fog is set after the POST.
        assertLeaveFogBeforeFetch(html, "async function generate", "function adoptMaze",
                "/maze/generate");
        assertDiscardAfterFetch(html, "async function generate", "function adoptMaze",
                "adoptMaze");
        assertLeaveFogBeforeFetch(html, "async function loadDaily", "async function loadCampaign",
                "/maze/daily");
        assertDiscardAfterFetch(html, "async function loadDaily", "async function loadCampaign",
                "adoptMaze");
        assertLeaveFogBeforeFetch(html, "async function loadCampaign", "function leaveCampaign",
                "/campaign");
        assertDiscardAfterFetch(html, "async function loadCampaign", "function leaveCampaign",
                "state.campaign");
        assertLeaveFogBeforeFetch(html, "async function playStage", "async function crossbreed",
                "/maze/${stage.mazeId}");
        assertDiscardAfterFetch(html, "async function playStage", "async function crossbreed",
                "adoptMaze");
        assertLeaveFogBeforeFetch(html, "async function crossbreed", "function parseHash",
                "/maze/breed");
        assertDiscardAfterFetch(html, "async function crossbreed", "function parseHash",
                "adoptMaze");
        // N22. #maze= / #session= hydrate fetched then adoptMaze no-op'd
        // during fog, so the bar named a maze the canvas still walked, and
        // a late #session= still ran adoptSessionView after adopt discarded.
        // Leave fog before those fetches (leave-walk path, same as N20);
        // same-hash still no-ops. Discard adopt / adoptSessionView when
        // Fog starts mid-flight.
        assertLeaveFogBeforeFetch(html, "async function loadFromHash",
                "// ---------- spectator mode", "/maze/${h.maze}");
        assertLeaveFogBeforeFetch(html, "async function loadFromHash",
                "// ---------- spectator mode", "spectate(h.session)");
        int hashMaze = html.indexOf("if (h.maze)", html.indexOf("async function loadFromHash"));
        int hashSpec = html.indexOf("// ---------- spectator mode", hashMaze);
        assertThat(hashMaze).isGreaterThanOrEqualTo(0);
        assertThat(hashSpec).isGreaterThan(hashMaze);
        String mazeHydrate = html.substring(hashMaze, hashSpec);
        int mazeGet = mazeHydrate.indexOf("await api(`/maze/${h.maze}`)");
        int mazeDiscard = mazeHydrate.indexOf("if (state.fog)", mazeGet);
        int mazeAdopt = mazeHydrate.indexOf("adoptMaze", mazeDiscard);
        assertThat(mazeGet).isGreaterThanOrEqualTo(0);
        assertThat(mazeDiscard).isGreaterThan(mazeGet);
        assertThat(mazeAdopt).isGreaterThan(mazeDiscard);
        assertLeaveFogBeforeFetch(html, "async function spectate",
                "function adoptSessionView", "/session/${sessionId}");
        assertDiscardAfterFetch(html, "async function spectate",
                "function adoptSessionView", "adoptSessionView");
        // N23. join() POSTed /join then always wrote the seat. A Fog
        // that started mid-flight hit a nulled state.session or
        // reattached the seat after the walk dropped it. Stay a
        // watcher until join lands (leaveSpectate after the POST);
        // discard the apply when state.fog is set. Not a
        // leave-fog-before-fetch path — that would break spectate.
        int joinFrom = html.indexOf("async function join()");
        int joinTo = html.indexOf("async function move(");
        assertThat(joinFrom).isGreaterThanOrEqualTo(0);
        assertThat(joinTo).isGreaterThan(joinFrom);
        String join = html.substring(joinFrom, joinTo);
        int joinPost = join.indexOf("/join?");
        int joinDiscard = join.indexOf("if (state.fog)", joinPost);
        int joinSeat = join.indexOf("state.seat");
        assertThat(joinPost).isGreaterThanOrEqualTo(0);
        assertThat(joinDiscard).isGreaterThan(joinPost);
        assertThat(joinSeat).isGreaterThan(joinDiscard);
        assertThat(join.indexOf("pinHash()")).isGreaterThan(joinDiscard);
        assertThat(join.indexOf("resubscribe()")).isGreaterThan(joinDiscard);
        assertThat(join.indexOf("leaveSpectate")).isGreaterThan(joinPost);
        assertThat(join).doesNotContain("state.fog = null");
        assertThat(join.indexOf("if (!state.session)", joinPost)).isGreaterThan(joinDiscard);
        // N24. confirmWin GETs /session/{id} then declareWin with no
        // fog/session re-check. Fog mid-flight painted a win (status,
        // leaderboard, campaign) on a fog walk. refreshTourStatus is
        // the same class. Discard after the GET; startFog still must
        // not null tour. applyMove already bails when !state.session.
        assertDiscardAfterFetch(html, "async function confirmWin",
                "function declareWin", "declareWin");
        assertDiscardAfterFetch(html, "async function refreshTourStatus",
                "async function tourVerdict", "$(\"status\")");
        int winFrom = html.indexOf("async function confirmWin");
        int winTo = html.indexOf("function declareWin");
        assertThat(winFrom).isGreaterThanOrEqualTo(0);
        assertThat(winTo).isGreaterThan(winFrom);
        String win = html.substring(winFrom, winTo);
        int winGet = win.indexOf("/session/${state.session.id}");
        int winDiscard = win.indexOf("if (state.fog)", winGet);
        int winDeclare = win.indexOf("declareWin", winDiscard);
        assertThat(winGet).isGreaterThanOrEqualTo(0);
        assertThat(winDiscard).isGreaterThan(winGet);
        assertThat(winDeclare).isGreaterThan(winDiscard);
        assertThat(win.indexOf("if (!state.session)", winGet)).isGreaterThan(winDiscard);
        int huntFrom = html.indexOf("async function refreshTourStatus");
        int huntTo = html.indexOf("async function tourVerdict");
        assertThat(huntFrom).isGreaterThanOrEqualTo(0);
        assertThat(huntTo).isGreaterThan(huntFrom);
        String hunt = html.substring(huntFrom, huntTo);
        int huntGet = hunt.indexOf("/tour");
        int huntDiscard = hunt.indexOf("if (state.fog)", huntGet);
        assertThat(huntGet).isGreaterThanOrEqualTo(0);
        assertThat(huntDiscard).isGreaterThan(huntGet);
        assertThat(hunt.indexOf("$(\"status\")", huntDiscard)).isGreaterThan(huntDiscard);
        assertThat(hunt.indexOf("if (!state.session)", huntGet)).isGreaterThan(huntDiscard);
        // N25. summonGhost GETs /ghost then always armed state.ghost and
        // the ticker. Fog mid-flight cleared both; the GET still re-armed
        // the ghost onto the walk. Discard after the GET; startFog still
        // must not null tour. hydrateSpectatorOverlays only calls this.
        assertDiscardAfterFetch(html, "async function summonGhost",
                "async function simulateTraffic", "state.ghost");
        int ghostFrom = html.indexOf("async function summonGhost");
        int ghostTo = html.indexOf("async function simulateTraffic");
        assertThat(ghostFrom).isGreaterThanOrEqualTo(0);
        assertThat(ghostTo).isGreaterThan(ghostFrom);
        String ghost = html.substring(ghostFrom, ghostTo);
        int ghostGet = ghost.indexOf("/ghost");
        int ghostDiscard = ghost.indexOf("if (state.fog)", ghostGet);
        int ghostArm = ghost.indexOf("state.ghost =", ghostDiscard);
        assertThat(ghostGet).isGreaterThanOrEqualTo(0);
        assertThat(ghostDiscard).isGreaterThan(ghostGet);
        assertThat(ghostArm).isGreaterThan(ghostDiscard);
        assertThat(ghost.indexOf("if (!state.session)", ghostGet)).isGreaterThan(ghostDiscard);
        assertThat(ghost.indexOf("setInterval", ghostDiscard)).isGreaterThan(ghostArm);
        // N26. fogStep POSTed /step then always applyFogView, which
        // recreates state.fog. Generate / Play that dropped the walk
        // mid-flight still got the old openings carved into the maze
        // now on screen. Discard after the POST; startFog still must
        // not null tour.
        int stepFrom = html.indexOf("async function fogStep");
        int stepTo = html.indexOf("function draw()");
        assertThat(stepFrom).isGreaterThanOrEqualTo(0);
        assertThat(stepTo).isGreaterThan(stepFrom);
        String step = html.substring(stepFrom, stepTo);
        int stepPost = step.indexOf("/step");
        int stepDiscard = step.indexOf("state.fog.agentId !== agentId", stepPost);
        int stepApply = step.indexOf("applyFogView(view)", stepDiscard);
        assertThat(stepPost).isGreaterThanOrEqualTo(0);
        assertThat(stepDiscard).isGreaterThan(stepPost);
        assertThat(stepApply).isGreaterThan(stepDiscard);
        // N27. move() POSTed /move then always flashStatus / applyMove.
        // Fog mid-flight: a blocked reply overwrote fog status.
        // Generate + a new Open session: applyMove wrote the old hop
        // onto the new seat. Arrows and click-to-move both call move().
        // Discard after the POST; startFog still must not null tour.
        assertDiscardAfterFetch(html, "async function move(",
                "function applyMove", "flashStatus");
        int mvFrom = html.indexOf("async function move(");
        int mvTo = html.indexOf("function applyMove");
        assertThat(mvFrom).isGreaterThanOrEqualTo(0);
        assertThat(mvTo).isGreaterThan(mvFrom);
        String mv = html.substring(mvFrom, mvTo);
        int mvId = mv.indexOf("sessionId");
        int mvMaze = mv.indexOf("mazeId");
        int mvPost = mv.indexOf("sessionId}/move");
        int mvFog = mv.indexOf("if (state.fog)", mvPost);
        int mvSession = mv.indexOf("state.session.id !== sessionId", mvPost);
        int mvMazeCheck = mv.indexOf("state.maze.id !== mazeId", mvPost);
        int mvSeat = mv.indexOf("positions[name] == null", mvPost);
        int mvFlash = mv.indexOf("flashStatus", mvSeat);
        int mvApply = mv.indexOf("applyMove", mvFlash);
        assertThat(mvId).isGreaterThanOrEqualTo(0);
        assertThat(mvMaze).isGreaterThanOrEqualTo(0);
        assertThat(mvId).isLessThan(mvPost);
        assertThat(mvMaze).isLessThan(mvPost);
        assertThat(mvPost).isGreaterThanOrEqualTo(0);
        assertThat(mvFog).isGreaterThan(mvPost);
        assertThat(mvSession).isGreaterThan(mvFog);
        assertThat(mvMazeCheck).isGreaterThan(mvFog);
        assertThat(mvSeat).isGreaterThan(mvFog);
        assertThat(mvFlash).isGreaterThan(mvSeat);
        assertThat(mvApply).isGreaterThan(mvFlash);
        int clickFrom = html.indexOf("$(\"maze\").addEventListener(\"click\"");
        int clickTo = html.indexOf("function drawEmpty");
        assertThat(clickFrom).isGreaterThanOrEqualTo(0);
        assertThat(clickTo).isGreaterThan(clickFrom);
        assertThat(html.substring(clickFrom, clickTo))
                .contains("move(who, dr, dc)")
                .doesNotContain("flashStatus")
                .doesNotContain("applyMove")
                .doesNotContain("/move");
        // N28. bringToLife / simulateTraffic POSTed then always disabled
        // the button and armed a poller. Generate that replaced the maze
        // mid-flight still bound #live / #traffic to a maze that is gone.
        // onMutation logged the tick and could re-enable #live after
        // refreshLivingMaze discarded. Discard after the POST / refresh
        // when maze id no longer matches. Fog stays — living+fog is
        // honest (N19 / Q2). Not if (state.fog); that would stop the run.
        int lifeFrom = html.indexOf("async function bringToLife");
        int lifeTo = html.indexOf("function startLivePolling");
        assertThat(lifeFrom).isGreaterThanOrEqualTo(0);
        assertThat(lifeTo).isGreaterThan(lifeFrom);
        String life = html.substring(lifeFrom, lifeTo);
        int lifeId = life.indexOf("mazeId");
        int lifePost = life.indexOf("/live");
        int lifeDiscard = life.indexOf("state.maze.id !== mazeId", lifePost);
        int lifeOff = life.indexOf("$(\"live\").disabled = true");
        int lifePoll = life.indexOf("startLivePolling");
        assertThat(lifeId).isGreaterThanOrEqualTo(0);
        assertThat(lifePost).isGreaterThan(lifeId);
        assertThat(lifeDiscard).isGreaterThan(lifePost);
        assertThat(lifeOff).isGreaterThan(lifeDiscard);
        assertThat(lifePoll).isGreaterThan(lifeDiscard);
        assertThat(life).doesNotContain("if (state.fog)");
        int mutFrom = html.indexOf("async function onMutation");
        int mutTo = html.indexOf("async function fingerprintWhenReady");
        assertThat(mutFrom).isGreaterThanOrEqualTo(0);
        assertThat(mutTo).isGreaterThan(mutFrom);
        String mut = html.substring(mutFrom, mutTo);
        int mutId = mut.indexOf("mazeId");
        int mutLog = mut.indexOf("log(\"state\"");
        int mutRefresh = mut.indexOf("await refreshLivingMaze");
        int mutDiscard = mut.indexOf("state.maze.id !== mazeId", mutRefresh);
        int mutOn = mut.indexOf("$(\"live\").disabled = false");
        assertThat(mutId).isGreaterThanOrEqualTo(0);
        assertThat(mutId).isLessThan(mutLog);
        assertThat(mutRefresh).isGreaterThan(mutLog);
        assertThat(mutDiscard).isGreaterThan(mutRefresh);
        assertThat(mutOn).isGreaterThan(mutDiscard);
        assertThat(mut).doesNotContain("if (state.fog)");
        int trafFrom = html.indexOf("async function simulateTraffic");
        int trafTo = html.indexOf("async function onTrafficPulse");
        assertThat(trafFrom).isGreaterThanOrEqualTo(0);
        assertThat(trafTo).isGreaterThan(trafFrom);
        String traf = html.substring(trafFrom, trafTo);
        int trafId = traf.indexOf("mazeId");
        int trafPost = traf.indexOf("/traffic");
        int trafDiscard = traf.indexOf("state.maze.id !== mazeId", trafPost);
        int trafOff = traf.indexOf("$(\"traffic\").disabled = true");
        assertThat(trafId).isGreaterThanOrEqualTo(0);
        assertThat(trafPost).isGreaterThan(trafId);
        assertThat(trafDiscard).isGreaterThan(trafPost);
        assertThat(trafOff).isGreaterThan(trafDiscard);
        assertThat(traf).doesNotContain("if (state.fog)");
        int pulseFrom = html.indexOf("async function onTrafficPulse");
        int pulseTo = html.indexOf("async function refreshTheoryOverlays");
        assertThat(pulseFrom).isGreaterThanOrEqualTo(0);
        assertThat(pulseTo).isGreaterThan(pulseFrom);
        String pulse = html.substring(pulseFrom, pulseTo);
        int pulseId = pulse.indexOf("mazeId");
        int pulseLog = pulse.indexOf("log(\"state\"");
        int pulseRefresh = pulse.indexOf("await refreshLivingMaze");
        int pulseDiscard = pulse.indexOf("state.maze.id !== mazeId", pulseRefresh);
        int pulseOn = pulse.indexOf("$(\"traffic\").disabled = false");
        assertThat(pulseId).isGreaterThanOrEqualTo(0);
        assertThat(pulseId).isLessThan(pulseLog);
        assertThat(pulseRefresh).isGreaterThan(pulseLog);
        assertThat(pulseDiscard).isGreaterThan(pulseRefresh);
        assertThat(pulseOn).isGreaterThan(pulseDiscard);
        assertThat(pulse).doesNotContain("if (state.fog)");
        // N29. playStage POSTed hazard /live / /traffic then always
        // disabled #live and armed a poller. Generate mid-flight
        // bound the maze now on screen. Discard after those POSTs
        // when maze id no longer matches the stage. Fog stays —
        // living+fog is honest (N19 / Q2 / N28). Not if (state.fog)
        // after the POST; that would stop the run.
        int n29From = html.indexOf("async function playStage");
        int n29To = html.indexOf("async function crossbreed");
        assertThat(n29From).isGreaterThanOrEqualTo(0);
        assertThat(n29To).isGreaterThan(n29From);
        String n29 = html.substring(n29From, n29To);
        int n29Post = n29.indexOf("method: \"POST\"");
        int n29Discard = n29.indexOf("state.maze.id !== stage.mazeId", n29Post);
        int n29Off = n29.indexOf("$(\"live\").disabled = true");
        int n29Poll = n29.indexOf("startLivePolling");
        assertThat(n29Post).isGreaterThanOrEqualTo(0);
        assertThat(n29Discard).isGreaterThan(n29Post);
        assertThat(n29Off).isGreaterThan(n29Discard);
        assertThat(n29Poll).isGreaterThan(n29Discard);
        int n29Hazards = n29.indexOf("for (const hazard");
        assertThat(n29Hazards).isGreaterThanOrEqualTo(0);
        assertThat(n29.substring(n29Hazards)).doesNotContain("if (state.fog)");
        // N30. solve / race / compare POSTed /solve then painted after
        // only a fog check. Generate mid-flight applied the old
        // expansions / #compareBox onto the maze now on screen; Race
        // / Compare could even POST later /solve against the new id.
        // Discard after the fetch when maze id no longer matches.
        // Fog discard stays (N18). startFog still must not null tour.
        assertMazeIdDiscardAfterFetch(html, "async function solve",
                "function animateSearch", "state.path");
        assertMazeIdDiscardAfterFetch(html, "async function raceSolvers",
                "function animateRace", "state.race");
        assertMazeIdDiscardAfterFetch(html, "async function compareSolvers",
                "async function play", "$(\"compareBox\")");
        assertMazeIdDiscardAfterFetch(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "paintAnalysisCaption");
        assertMazeIdDiscardAfterFetch(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "paintFingerprintCaption");
        assertMazeIdDiscardAfterFetch(html, "async function distanceHeatMap",
                "function paintFieldCaption", "paintFieldCaption");
        assertMazeIdDiscardAfterFetch(html, "async function heuristicLens",
                "function paintLensCaption", "paintLensCaption");
        // N31. Hunt / hardest / sanctuaries / ASCII fetched then painted
        // after only a fog check. Generate mid-flight assigned the old
        // tour / route / rings / dump onto the maze now on screen; Hunt
        // could even play() a session on the new id. Discard after the
        // fetch when maze id no longer matches. Fog discard stays (N18).
        assertMazeIdDiscardAfterFetch(html, "async function startTour",
                "function sameCell", "state.tour = t");
        assertMazeIdDiscardAfterFetch(html, "async function hardestRoute",
                "function paintHardestCaption", "paintHardestCaption");
        assertMazeIdDiscardAfterFetch(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "paintSanctuariesCaption");
        assertMazeIdDiscardAfterFetch(html, "async function showAscii",
                "async function loadAlgorithms", "$(\"asciiOut\")");
        int n31From = html.indexOf("async function startTour");
        int n31To = html.indexOf("function sameCell");
        assertThat(n31From).isGreaterThanOrEqualTo(0);
        assertThat(n31To).isGreaterThan(n31From);
        String n31 = html.substring(n31From, n31To);
        int n31Play = n31.indexOf("await play()");
        int n31Discard = n31.indexOf("state.maze.id !== mazeId");
        assertThat(n31.indexOf("/maze/${mazeId}/tour")).isGreaterThanOrEqualTo(0);
        assertThat(n31Discard).isGreaterThan(n31.indexOf("await "));
        assertThat(n31Play).isGreaterThan(n31Discard);
        // N32. play() POSTed /session after only a fog check. Generate
        // mid-flight pinned #session= and seated the old session on the
        // maze now on screen. Capture maze id before the POST; discard
        // after /session (and the leave-fog GET /maze) when fog is on
        // OR maze id no longer matches. Fog discard stays (N20).
        assertMazeIdDiscardAfterFetch(html, "async function play()",
                "async function join", "state.session =");
        int n32From = html.indexOf("async function play()");
        int n32To = html.indexOf("async function join");
        assertThat(n32From).isGreaterThanOrEqualTo(0);
        assertThat(n32To).isGreaterThan(n32From);
        String n32 = html.substring(n32From, n32To);
        int n32Id = n32.indexOf("const mazeId");
        int n32Get = n32.indexOf("api(`/maze/${mazeId}`)");
        int n32Post = n32.indexOf("/maze/${mazeId}/session");
        int n32Maze = n32.indexOf("state.maze.id !== mazeId", n32Post);
        assertThat(n32Id).isGreaterThanOrEqualTo(0);
        assertThat(n32Id).isLessThan(n32Get);
        assertThat(n32Get).isGreaterThanOrEqualTo(0);
        assertThat(n32Get).isLessThan(n32Post);
        assertThat(n32Post).isGreaterThanOrEqualTo(0);
        assertThat(n32.indexOf("if (state.fog)", n32Get)).isGreaterThan(n32Get);
        assertThat(n32.indexOf("state.maze.id !== mazeId", n32Get)).isGreaterThan(n32Get);
        assertThat(n32.indexOf("Object.assign", n32Get))
                .isGreaterThan(n32.indexOf("state.maze.id !== mazeId", n32Get));
        assertThat(n32.indexOf("if (state.fog)", n32Post)).isGreaterThan(n32Post);
        assertThat(n32Maze).isGreaterThan(n32Post);
        assertThat(n32.indexOf("state.session =")).isGreaterThan(n32Maze);
        assertThat(n32.indexOf("pinHash()")).isGreaterThan(n32Maze);
        assertThat(n32.indexOf("summonGhost()")).isGreaterThan(n32Maze);
        assertThat(n32.indexOf("resubscribe()")).isGreaterThan(n32Maze);
        assertThat(n32.substring(n32Id)).doesNotContain("/maze/${state.maze.id}");
        // N33. hydrateSpectatorOverlays GETs /session/{id}/tour then
        // always wrote state.tour. Generate / Fog / a new #session=
        // mid-flight painted the old hunt onto the maze now on screen.
        // Capture session + maze id before the GET; discard after when
        // fog is on, the session no longer matches, or maze id no
        // longer matches. Sibling summonGhost is the same discard.
        // Progress only — must not GET /maze/{id}/tour. startFog still
        // must not null tour (N17).
        assertMazeIdDiscardAfterFetch(html, "async function hydrateSpectatorOverlays",
                "async function bringToLife", "state.tour =");
        int n33From = html.indexOf("async function hydrateSpectatorOverlays");
        int n33To = html.indexOf("async function bringToLife");
        assertThat(n33From).isGreaterThanOrEqualTo(0);
        assertThat(n33To).isGreaterThan(n33From);
        String n33 = html.substring(n33From, n33To);
        int n33Id = n33.indexOf("const sessionId");
        int n33Maze = n33.indexOf("const mazeId");
        int n33Get = n33.indexOf("/session/${sessionId}/tour");
        int n33Fog = n33.indexOf("if (state.fog)", n33Get);
        int n33Sess = n33.indexOf("state.session.id !== sessionId", n33Get);
        int n33MazeCheck = n33.indexOf("state.maze.id !== mazeId", n33Get);
        int n33Write = n33.indexOf("state.tour =", n33MazeCheck);
        int n33Ghost = n33.indexOf("summonGhost()", n33MazeCheck);
        assertThat(n33Id).isGreaterThanOrEqualTo(0);
        assertThat(n33Maze).isGreaterThan(n33Id);
        assertThat(n33Maze).isLessThan(n33Get);
        assertThat(n33Get).isGreaterThanOrEqualTo(0);
        assertThat(n33Fog).isGreaterThan(n33Get);
        assertThat(n33Sess).isGreaterThan(n33Fog);
        assertThat(n33MazeCheck).isGreaterThan(n33Sess);
        assertThat(n33Write).isGreaterThan(n33MazeCheck);
        assertThat(n33Ghost).isGreaterThan(n33Write);
        assertThat(n33).doesNotContain("/maze/${");
        assertThat(n33).doesNotContain("state.tour = null");
        assertThat(n33).doesNotContain("tourFor");
        // N34. spectate poll GETs /session/{id} then always
        // adoptSessionView. Generate / Fog / a new #session=
        // mid-flight re-seated the old walk on the maze now on
        // screen. Capture session + maze id before the GET;
        // discard after when fog is on, the session no longer
        // matches, or maze id no longer matches. Must not GET
        // /maze. startFog still must not null tour (N17).
        int n34From = html.indexOf("async function spectate");
        int n34To = html.indexOf("function adoptSessionView");
        assertThat(n34From).isGreaterThanOrEqualTo(0);
        assertThat(n34To).isGreaterThan(n34From);
        String n34 = html.substring(n34From, n34To);
        int n34Poll = n34.indexOf("setInterval");
        int n34Id = n34.indexOf("const sessionId", n34Poll);
        int n34Maze = n34.indexOf("const mazeId", n34Poll);
        int n34Get = n34.indexOf("/session/${sessionId}", n34Poll);
        int n34Fog = n34.indexOf("if (state.fog)", n34Get);
        int n34Sess = n34.indexOf("state.session.id !== sessionId", n34Get);
        int n34MazeCheck = n34.indexOf("state.maze.id !== mazeId", n34Get);
        int n34Write = n34.indexOf("adoptSessionView", n34MazeCheck);
        assertThat(n34Poll).isGreaterThanOrEqualTo(0);
        assertThat(n34Id).isGreaterThan(n34Poll);
        assertThat(n34Maze).isGreaterThan(n34Id);
        assertThat(n34Maze).isLessThan(n34Get);
        assertThat(n34Get).isGreaterThanOrEqualTo(0);
        assertThat(n34Fog).isGreaterThan(n34Get);
        assertThat(n34Sess).isGreaterThan(n34Fog);
        assertThat(n34MazeCheck).isGreaterThan(n34Sess);
        assertThat(n34Write).isGreaterThan(n34MazeCheck);
        assertThat(n34.substring(n34Poll)).doesNotContain("/session/${state.session.id}");
        assertThat(n34.substring(n34Poll)).doesNotContain("/maze/${");
        assertThat(n34.substring(n34Poll)).doesNotContain("tourFor");
        int raceFrom = html.indexOf("async function raceSolvers");
        int raceTo = html.indexOf("function animateRace");
        assertThat(raceFrom).isGreaterThanOrEqualTo(0);
        assertThat(raceTo).isGreaterThan(raceFrom);
        String race = html.substring(raceFrom, raceTo);
        assertThat(race).contains("/maze/${mazeId}/solve");
        assertThat(race.substring(race.indexOf("const mazeId")))
                .doesNotContain("/maze/${state.maze.id}/solve");
        int cmpFrom = html.indexOf("async function compareSolvers");
        int cmpTo = html.indexOf("async function play()", cmpFrom);
        assertThat(cmpFrom).isGreaterThanOrEqualTo(0);
        assertThat(cmpTo).isGreaterThan(cmpFrom);
        String cmp = html.substring(cmpFrom, cmpTo);
        assertThat(cmp).contains("/maze/${mazeId}/solve");
        assertThat(cmp.substring(cmp.indexOf("const mazeId")))
                .doesNotContain("/maze/${state.maze.id}/solve");
        int fogFn = html.indexOf("async function startFog");
        int fogEnd = html.indexOf("async function fogStep");
        assertThat(fogFn).isGreaterThanOrEqualTo(0);
        assertThat(fogEnd).isGreaterThan(fogFn);
        assertThat(html.substring(fogFn, fogEnd)).doesNotContain("state.tour = null");
        int playerFrom = html.indexOf("if (state.session) {",
                html.indexOf("function resubscribe"));
        int playerTo = html.indexOf("/topic/plugins/failures");
        assertThat(playerFrom).isGreaterThanOrEqualTo(0);
        assertThat(playerTo).isGreaterThan(playerFrom);
        String player = html.substring(playerFrom, playerTo);
        int playerId = player.indexOf("sessionId");
        int playerSub = player.indexOf("/player");
        int playerFog = player.indexOf("if (state.fog)", playerSub);
        int playerSession = player.indexOf("state.session.id !== sessionId", playerSub);
        int playerApply = player.indexOf("applyMove");
        assertThat(playerId).isGreaterThanOrEqualTo(0);
        assertThat(playerId).isLessThan(playerSub);
        assertThat(playerFog).isGreaterThan(playerSub);
        assertThat(playerSession).isGreaterThan(playerFog);
        assertThat(playerApply).isGreaterThan(playerSession);
        int declFrom = html.indexOf("function declareWin");
        int declTo = html.indexOf("let statusFlashTimer");
        assertThat(declFrom).isGreaterThanOrEqualTo(0);
        assertThat(declTo).isGreaterThan(declFrom);
        String decl = html.substring(declFrom, declTo);
        assertThat(decl.indexOf("if (state.fog)")).isGreaterThanOrEqualTo(0);
        assertThat(decl.indexOf("if (state.fog)")).isLessThan(decl.indexOf("state.won = who"));
        assertThat(decl.indexOf("if (state.fog)")).isLessThan(decl.indexOf("refreshLeaderboard"));
        int thenFog = decl.indexOf("if (state.fog)", decl.indexOf("tourVerdict"));
        assertThat(thenFog).isGreaterThan(decl.indexOf("tourVerdict"));
        assertThat(decl.indexOf("$(\"status\")", thenFog)).isGreaterThan(thenFog);
        int applyFrom = html.indexOf("function applyMove");
        int applyTo = html.indexOf("async function confirmWin");
        assertThat(applyFrom).isGreaterThanOrEqualTo(0);
        assertThat(applyTo).isGreaterThan(applyFrom);
        assertThat(html.substring(applyFrom, applyTo))
                .contains("if (!state.session) return");
        assertLeaveBeforeWrite(html, "async function loadDaily", "/maze/daily");
        assertLeaveBeforeWrite(html, "async function loadCampaign", "/campaign");
        assertLeaveBeforeWrite(html, "async function playStage", "/maze/${stage.mazeId}");
        assertLeaveBeforeWrite(html, "async function crossbreed", "/maze/breed");
        assertLeaveBeforeWrite(html, "async function solve", "/solve/");
        // Measure / tournament / ASCII fill a sidebar or a <pre>. Leaving dropped
        // watch; a living tick that refreshed ASCII then re-armed Bring to life.
        assertStayWhileWatching(html, "async function measureGrowth", "function renderLab");
        assertStayWhileWatching(html, "async function runTournament", "// ---------- heuristic lens");
        assertStayWhileWatching(html, "async function showAscii", "async function loadAlgorithms");
        // A dump that sent ?solve= minted MazeSolvedEvent on a text/plain read.
        // Living-tick refresh and a spectator click both go through showAscii.
        int asciiFrom = html.indexOf("async function showAscii");
        int asciiTo = html.indexOf("async function loadAlgorithms");
        assertThat(asciiFrom).isGreaterThanOrEqualTo(0);
        assertThat(asciiTo).isGreaterThan(asciiFrom);
        assertThat(html.substring(asciiFrom, asciiTo))
                .contains("apiPlain(`/maze/${mazeId}`)")
                .doesNotContain("?solve=${")
                .doesNotContain("apiPlain(`/maze/${state.maze.id}`)");
        // Size / braid / hotspots already followed the snapshot. Generator and
        // seed stayed on leftovers, so a #maze= success path half-hydrated:
        // pinHash wrote the maze recipe, Generate / Measure still read the form.
        int adoptFrom = html.indexOf("function adoptMaze");
        int adoptTo = html.indexOf("// Snapshot whatever is on the canvas");
        assertThat(adoptFrom).isGreaterThanOrEqualTo(0);
        assertThat(adoptTo).isGreaterThan(adoptFrom);
        String adopt = html.substring(adoptFrom, adoptTo);
        assertThat(adopt)
                .contains("$(\"generator\").value = maze.generatorId")
                .contains("$(\"seed\").value = maze.seed");
        assertThat(adopt.indexOf("if (state.fog)"))
                .isGreaterThanOrEqualTo(0);
        assertThat(adopt.indexOf("if (state.fog)"))
                .isLessThan(adopt.indexOf("state.maze = maze"));
        assertThat(adopt.indexOf("if (state.fog)"))
                .isLessThan(adopt.indexOf("state.fog = null"));
        // loadFromHash was boot-only. pinHash wrote the bar; Back updated the
        // URL and left the canvas on the previous maze. hashchange re-runs the
        // boot hydrate; the same-hash guard stops pinHash's write from looping.
        int hashFrom = html.indexOf("async function loadFromHash");
        int hashTo = html.indexOf("// ---------- spectator mode");
        assertThat(hashFrom).isGreaterThanOrEqualTo(0);
        assertThat(hashTo).isGreaterThan(hashFrom);
        assertThat(html.substring(hashFrom, hashTo))
                .contains("if (hashShowsCurrent()) return")
                .contains("addEventListener(\"hashchange\"")
                .contains("loadFromHash()")
                .contains("leaveCampaign()")
                .contains("leaveMaze()")
                .contains("loadCampaign")
                .contains("parseCampaignToken")
                .contains("named.stage")
                .doesNotContain("await loadCampaign(Number(h.campaign))");
        // Back onto "" or #generator= re-hydrated selects and left the previous
        // maze on the canvas (N10 is maze-to-maze). leaveMaze runs after the
        // maze kinds return, and must not pin (that would fight History).
        int dropFrom = html.indexOf("function leaveMaze");
        assertThat(dropFrom).isGreaterThanOrEqualTo(0);
        assertThat(dropFrom).isLessThan(hashFrom);
        String drop = html.substring(dropFrom, hashFrom);
        assertThat(drop)
                .contains("state.maze = null")
                .contains("state.dailyId = null")
                .contains("state.session = null")
                .contains("drawEmpty")
                .doesNotContain("pinHash()");
        String fromHash = html.substring(hashFrom, hashTo);
        // Leave fog after the same-hash guard and before any hydrate fetch,
        // so a matching #maze= during fog still does not remint (N10).
        int sameHash = fromHash.indexOf("hashShowsCurrent()");
        int leaveFog = fromHash.indexOf("state.fog = null");
        int sessionHydrate = fromHash.indexOf("if (h.session)");
        assertThat(sameHash).isGreaterThanOrEqualTo(0);
        assertThat(leaveFog).isGreaterThan(sameHash);
        assertThat(sessionHydrate).isGreaterThan(leaveFog);
        int mazeKind = fromHash.indexOf("if (h.maze)");
        int dropCall = fromHash.lastIndexOf("leaveMaze()");
        assertThat(mazeKind).isGreaterThanOrEqualTo(0);
        assertThat(dropCall).isGreaterThan(mazeKind);
        assertThat(fromHash.substring(fromHash.indexOf("if (h.session)"), mazeKind))
                .doesNotContain("leaveMaze()");
        // adoptMaze only nulled stageIndex. Back re-hydrated the maze (N10)
        // and left state.campaign / #campaignBox painted, so a stage click
        // still played a campaign maze the bar no longer named.
        int leaveFrom = html.indexOf("function leaveCampaign");
        int leaveTo = html.indexOf("function renderCampaign");
        assertThat(leaveFrom).isGreaterThanOrEqualTo(0);
        assertThat(leaveTo).isGreaterThan(leaveFrom);
        assertThat(html.substring(leaveFrom, leaveTo))
                .contains("state.campaign = null")
                .contains("$(\"campaignBox\")");
        assertThat(adopt).contains("state.stageIndex = null")
                .doesNotContain("state.campaign = null");
        // Generate / Daily / Breed adopt then pin a matching #maze= / #daily.
        // hashShowsCurrent then no-ops, so loadFromHash never leaves. pinHash
        // drops the ladder when the exclusive kind is not campaign; playStage
        // restores stageIndex first so that write stays #campaign=.
        int pinFrom = html.indexOf("function pinHash");
        int pinTo = html.indexOf("function hashShowsCurrent");
        assertThat(pinFrom).isGreaterThanOrEqualTo(0);
        assertThat(pinTo).isGreaterThan(pinFrom);
        assertThat(html.substring(pinFrom, pinTo))
                .contains("leaveCampaign()")
                .contains("p.campaign == null");
        int stageFrom = html.indexOf("async function playStage");
        int stageTo = html.indexOf("async function crossbreed");
        assertThat(stageFrom).isGreaterThanOrEqualTo(0);
        assertThat(stageTo).isGreaterThan(stageFrom);
        String stage = html.substring(stageFrom, stageTo);
        assertThat(stage.indexOf("state.stageIndex = index"))
                .isGreaterThan(stage.indexOf("adoptMaze"));
        assertThat(stage.indexOf("pinHash()"))
                .isGreaterThan(stage.indexOf("state.stageIndex = index"));
        assertThat(stage).doesNotContain("leaveCampaign()");
        // #campaign= named only the seed. loadCampaign always playStage(0), so
        // Back / Forward / paste reminted stage 1. The token now carries :N;
        // a missing stage still hydrates rung 0 so old links keep working.
        int permFrom = html.indexOf("function currentPermalink");
        int permTo = html.indexOf("function pinHash");
        assertThat(permFrom).isGreaterThanOrEqualTo(0);
        assertThat(permTo).isGreaterThan(permFrom);
        assertThat(html.substring(permFrom, permTo))
                .contains("stageIndex")
                .contains("+ \":\" +");
        int campFrom = html.indexOf("async function loadCampaign");
        int campTo = html.indexOf("function leaveCampaign");
        assertThat(campFrom).isGreaterThanOrEqualTo(0);
        assertThat(campTo).isGreaterThan(campFrom);
        assertThat(html.substring(campFrom, campTo))
                .contains("playStage(index)")
                .doesNotContain("await playStage(0)");
        int tokenFrom = html.indexOf("function parseCampaignToken");
        int tokenTo = html.indexOf("function recipeParts");
        assertThat(tokenFrom).isGreaterThanOrEqualTo(0);
        assertThat(tokenTo).isGreaterThan(tokenFrom);
        assertThat(html.substring(tokenFrom, tokenTo))
                .contains("h.campaign")
                .contains("stage: 0");
        assertAdoptThenPin(html, "async function generate", "function adoptMaze");
        assertAdoptThenPin(html, "async function loadDaily", "async function loadCampaign");
        assertAdoptThenPin(html, "async function crossbreed", "function parseHash");
    }

    /** Generate / Daily / Breed adopt a non-campaign maze, then pinHash leaves. */
    private static void assertAdoptThenPin(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end);
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body.indexOf("pinHash()")).isGreaterThan(body.indexOf("adoptMaze"));
        assertThat(body).doesNotContain("leaveCampaign()");
    }

    /** Fog discard (N18) plus maze-id discard after the fetch (N28/N30). */
    private static void assertMazeIdDiscardAfterFetch(String html, String start, String end,
            String write) {
        int from = html.indexOf(start);
        assertThat(from).isGreaterThanOrEqualTo(0);
        int to = html.indexOf(end, from + start.length());
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int id = body.indexOf("mazeId");
        int fetch = body.indexOf("await ");
        int fog = body.indexOf("if (state.fog)", fetch);
        int discard = body.indexOf("state.maze.id !== mazeId", fetch);
        int out = body.indexOf(write, Math.max(fog, discard));
        assertThat(id).isGreaterThanOrEqualTo(0);
        assertThat(id).isLessThan(fetch);
        assertThat(fetch).isGreaterThanOrEqualTo(0);
        assertThat(fog).isGreaterThan(fetch);
        assertThat(discard).isGreaterThan(fog);
        assertThat(out).isGreaterThan(discard);
    }

    /** First {@code if (state.fog)} after the fetch is before {@code write}. */
    private static void assertDiscardAfterFetch(String html, String start, String end,
            String write) {
        int from = html.indexOf(start);
        assertThat(from).isGreaterThanOrEqualTo(0);
        int to = html.indexOf(end, from + start.length());
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int fetch = body.indexOf("await ");
        int fog = body.indexOf("if (state.fog)", fetch);
        int out = body.indexOf(write, fog);
        assertThat(fetch).isGreaterThanOrEqualTo(0);
        assertThat(fog).isGreaterThan(fetch);
        assertThat(out).isGreaterThan(fog);
    }

    /** Leave-fog paths drop the walk before they fetch, not after. */
    private static void assertLeaveFogBeforeFetch(String html, String start, String end,
            String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int drop = body.indexOf("state.fog = null");
        int fetch = body.indexOf(write);
        assertThat(drop).isGreaterThanOrEqualTo(0);
        assertThat(fetch).isGreaterThan(drop);
    }

    /** First {@code leaveSpectate} after {@code start} is before {@code write}. */
    private static void assertLeaveBeforeWrite(String html, String start, String write) {
        int from = html.indexOf(start);
        assertThat(from).isGreaterThanOrEqualTo(0);
        int leave = html.indexOf("leaveSpectate", from);
        int fetch = html.indexOf(write, from);
        assertThat(leave).isGreaterThan(from);
        assertThat(fetch).isGreaterThan(from);
        assertThat(leave).isLessThan(fetch);
    }

    /** Sidebar / text-dump lab reads must not drop watch or refuse. */
    private static void assertStayWhileWatching(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end);
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("leaveSpectate").doesNotContain("refuseSpectatorWrite");
    }
}
