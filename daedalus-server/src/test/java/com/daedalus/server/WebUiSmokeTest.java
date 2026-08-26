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
 *
 * <p><b>Do not grow this class as a source-shape mirror.</b> A {@code contains} pin
 * here proves a string still exists in {@code index.html}, not that the page still
 * works. Leftover-state and feature regressions belong in {@code sweep/}:
 * {@code api-sweep.py} now runs in CI against a test-profile server;
 * {@code ui-sweep.js} is the local Playwright pass. New UI behavior gets a sweep
 * check, not another substring assertion.
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
        // N39. startFog POSTed /agent then applied after only maze-id.
        // Play on the same maze seats a session; maze id still matches,
        // so a late mint dropped the seat and applyFogView recreated
        // state.fog on the play walk. Capture session id; discard after
        // the POST when the seated session is new. Maze-id discard
        // stays (N26). Same class as N38. startFog still must not
        // null tour (N17). Must not GET /maze.
        int fogSessionId = fog.indexOf("const sessionId");
        int fogSeatDiscard = fog.indexOf("state.session.id !== sessionId");
        int fogSeatDrop = fog.indexOf("state.session = null");
        int fogMintApply = fog.indexOf("applyFogView", fogSeatDiscard);
        assertThat(fogSessionId).isGreaterThanOrEqualTo(0);
        assertThat(fogSessionId).isLessThan(fogMint);
        assertThat(fogSeatDiscard).isGreaterThan(fogMint);
        assertThat(fogSeatDrop).isGreaterThan(fogSeatDiscard);
        assertThat(fogMintApply).isGreaterThan(fogSeatDiscard);
        // Analyze / Compare wrote #compareBox. Fog dropped the overlay
        // objects (N16) and left the sidebar, so a leftover caption still
        // named chokepoints and a leftover compare row could hover-arm a
        // solve path draw() swallowed until Play. Empty after the drop.
        // state.tour stays — same maze, not a GET/mutate under fog.
        assertThat(fog.indexOf("$(\"compareBox\").innerHTML"))
                .isGreaterThan(fog.indexOf("state.session = null"));
        assertThat(fog).doesNotContain("state.tour = null");
        // N95. Fog left leftover Solve stats armed. Play /
        // Hunt / Join rewrite #stats (N92–N94). Fog did not,
        // so leftover solver numbers named the previous walk
        // under the fog walk. Rewrite after the maze-id
        // discard. startFog still must not null tour (N17).
        int n95Stats = fog.indexOf("$(\"stats\").innerHTML =");
        assertThat(n95Stats).isGreaterThan(fogDiscard);
        assertThat(n95Stats).isGreaterThan(fog.indexOf("state.session = null"));
        // N109. Fog left leftover trails armed. Generate /
        // leave-watch / leaveMaze / Play drop leftover crumbs.
        // Fog dropped the seat and leftover ghost (N15) but
        // left leftover trails, so leftover crumbs painted
        // after a living tick ended the fog walk without
        // Play. Drop trails after the maze-id discard.
        // startFog still must not null tour (N17).
        int n109Trails = fog.indexOf("state.trails = {}");
        assertThat(n109Trails).isGreaterThan(fogDiscard);
        assertThat(n109Trails).isGreaterThan(fog.indexOf("state.session = null"));
        // N110. Fog left leftover won armed. Generate /
        // leave-watch / leaveMaze / Play drop leftover won.
        // Fog dropped the seat and leftover trails (N109) but
        // left leftover won, so leftover victory ring painted
        // after a living tick ended the fog walk without
        // Play. Drop won after the maze-id discard.
        // startFog still must not null tour (N17).
        int n110Won = fog.indexOf("state.won = null");
        assertThat(n110Won).isGreaterThan(fogDiscard);
        assertThat(n110Won).isGreaterThan(fog.indexOf("state.session = null"));
        assertThat(n110Won).isGreaterThan(n109Trails);
        // N117. Fog left leftover tourGot armed. Hunt remints
        // collected coins. Fog dropped the seat and leftover
        // won (N110) but left leftover tourGot, so leftover
        // collected coins painted after Play seated a new
        // walk. Drop tourGot after the maze-id discard.
        // startFog still must not null tour (N17).
        int n117FogGot = fog.indexOf("state.tourGot = []");
        assertThat(n117FogGot).isGreaterThan(fogDiscard);
        assertThat(n117FogGot).isGreaterThan(fog.indexOf("state.session = null"));
        assertThat(n117FogGot).isGreaterThan(n110Won);
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
        // N38. refreshLivingMaze GETs /agent then applyFogView after
        // only maze-id stale(). Play on the same maze leaves fog;
        // maze id still matches, so a late GET recreates state.fog
        // on the play walk. Capture agent id; discard after the GET
        // when fog is gone or the agent no longer matches. Same
        // class as N26. Fog path still must not GET /maze. startFog
        // still must not null tour (N17). Living-under-fog stays.
        int fogAgentGet = live.indexOf("await api(`/agent/${");
        int fogAgentId = live.indexOf("agentId");
        int fogWalkDiscard = live.indexOf("state.fog.agentId !== agentId");
        int fogApply = live.indexOf("applyFogView", fogWalkDiscard);
        assertThat(fogAgentGet).isGreaterThanOrEqualTo(0);
        assertThat(fogAgentId).isGreaterThanOrEqualTo(0);
        assertThat(fogAgentId).isLessThan(fogAgentGet);
        assertThat(fogWalkDiscard).isGreaterThan(fogAgentGet);
        assertThat(fogApply).isGreaterThan(fogWalkDiscard);
        assertThat(html.substring(html.indexOf("async function startFog"),
                html.indexOf("async function fogStep"))).doesNotContain("state.tour = null");
        // N42. A seated session's living tick asked GET /maze/{id}/tour
        // (tourFor — auth-required in prod, and it can mint). Spectator
        // hydrate already paints from GET /session/{id}/tour (progressFor
        // rescores Held-Karp, public). The old body 401'd and kept a
        // stale optimum on the watched hunt. Prefer the session read
        // when a seat exists; maze tour is only the no-session fallback.
        int n42Guard = live.indexOf("if (state.session)");
        int n42Sess = live.indexOf("/session/${sessionId}/tour");
        int n42MazeTour = live.indexOf("/maze/${forMaze}/tour");
        assertThat(n42Guard).isGreaterThanOrEqualTo(0);
        assertThat(n42Sess).isGreaterThan(n42Guard);
        assertThat(n42MazeTour).isGreaterThan(n42Sess);
        assertThat(live).contains("p.optimal");
        assertThat(live).contains("p.waypoints");
        assertThat(live.indexOf("state.session.id !== sessionId", n42Sess))
                .isGreaterThan(n42Sess);
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
        // N40. Daily / Breed / Campaign / #maze= hydrate discarded
        // adopt after only fog. Generate mid-flight replaced the
        // canvas, then the late fetch still adoptMaze'd over it.
        // Capture maze id (or none) before the fetch; discard when
        // fog is on OR the canvas id is no longer the one you left.
        // playStage compares the canvas it left, not stage.mazeId —
        // re-clicking the same rung still adopts. Fog discard stays
        // (N21 / N22). Generate stays fog-only — it is the winner.
        assertMazeIdDiscardAfterFetch(html, "async function loadDaily",
                "async function loadCampaign", "adoptMaze");
        assertMazeIdDiscardAfterFetch(html, "async function loadCampaign",
                "function leaveCampaign", "state.campaign");
        assertMazeIdDiscardAfterFetch(html, "async function playStage",
                "async function crossbreed", "adoptMaze");
        assertMazeIdDiscardAfterFetch(html, "async function crossbreed",
                "function parseHash", "adoptMaze");
        int n40StageFrom = html.indexOf("async function playStage");
        int n40StageTo = html.indexOf("async function crossbreed");
        assertThat(n40StageFrom).isGreaterThanOrEqualTo(0);
        assertThat(n40StageTo).isGreaterThan(n40StageFrom);
        String n40Stage = html.substring(n40StageFrom, n40StageTo);
        int n40Canvas = n40Stage.indexOf("const mazeId");
        int n40StageGet = n40Stage.indexOf("await api(`/maze/${stage.mazeId}`)");
        int n40Adopt = n40Stage.indexOf("adoptMaze");
        assertThat(n40Canvas).isGreaterThanOrEqualTo(0);
        assertThat(n40Canvas).isLessThan(n40StageGet);
        assertThat(n40Stage.indexOf("state.maze.id !== mazeId")).isLessThan(n40Adopt);
        assertThat(n40Stage.indexOf("state.maze.id !== stage.mazeId")).isGreaterThan(n40Adopt);
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
        // N40 sibling. #maze= hydrate discarded adopt after only fog.
        int mazeIdCap = mazeHydrate.indexOf("mazeId");
        int mazeIdDiscard = mazeHydrate.indexOf("state.maze.id !== mazeId", mazeGet);
        int mazeRebuild = mazeHydrate.indexOf("rebuildFromRecipe");
        assertThat(mazeIdCap).isGreaterThanOrEqualTo(0);
        assertThat(mazeIdCap).isLessThan(mazeGet);
        assertThat(mazeIdDiscard).isGreaterThan(mazeDiscard);
        assertThat(mazeAdopt).isGreaterThan(mazeIdDiscard);
        assertThat(mazeRebuild).isGreaterThan(mazeIdDiscard);
        assertLeaveFogBeforeFetch(html, "async function spectate",
                "function adoptSessionView", "/session/${sessionId}");
        assertDiscardAfterFetch(html, "async function spectate",
                "function adoptSessionView", "adoptSessionView");
        // N41. #session= / spectate adoptMaze'd the session maze
        // before its fog check and had no maze-id discard. Generate
        // mid-flight replaced the canvas, then the late GET still
        // adopted over it. Capture maze id (or none) before the
        // fetch; skip adoptMaze / adoptSessionView when fog is on
        // or the canvas id is no longer the one you left. Leave
        // fog before the fetch stays (N22). Stay until join lands.
        // Poll discard stays (N34).
        assertMazeIdDiscardAfterFetch(html, "async function spectate",
                "function adoptSessionView", "adoptMaze");
        assertMazeIdDiscardAfterFetch(html, "async function spectate",
                "function adoptSessionView", "adoptSessionView");
        // N23. join() POSTed /join then always wrote the seat. A Fog
        // that started mid-flight hit a nulled state.session or
        // reattached the seat after the walk dropped it. Stay a
        // watcher until join lands (leaveSpectate after the POST);
        // discard the apply when state.fog is set. Not a
        // leave-fog-before-fetch path — that would break spectate.
        // N36. After only fog + session-exists, Generate + Play /
        // a new #session= mid-flight wrote the joiner (seat,
        // leaveSpectate, pin) onto the maze now on screen. Capture
        // session + maze id before the POST; discard after when
        // fog is on, the session no longer matches, or maze id
        // no longer matches. Must not GET /maze. startFog still
        // must not null tour (N17).
        assertMazeIdDiscardAfterFetch(html, "async function join()",
                "async function move(", "state.seat");
        int joinFrom = html.indexOf("async function join()");
        int joinTo = html.indexOf("async function move(");
        assertThat(joinFrom).isGreaterThanOrEqualTo(0);
        assertThat(joinTo).isGreaterThan(joinFrom);
        String join = html.substring(joinFrom, joinTo);
        int joinId = join.indexOf("const sessionId");
        int joinMaze = join.indexOf("const mazeId");
        int joinPost = join.indexOf("/session/${sessionId}/join?");
        int joinDiscard = join.indexOf("if (state.fog)", joinPost);
        int joinSess = join.indexOf("state.session.id !== sessionId", joinPost);
        int joinMazeCheck = join.indexOf("state.maze.id !== mazeId", joinPost);
        int joinSeat = join.indexOf("state.seat");
        assertThat(joinId).isGreaterThanOrEqualTo(0);
        assertThat(joinMaze).isGreaterThan(joinId);
        assertThat(joinMaze).isLessThan(joinPost);
        assertThat(joinPost).isGreaterThanOrEqualTo(0);
        assertThat(joinDiscard).isGreaterThan(joinPost);
        assertThat(joinSess).isGreaterThan(joinDiscard);
        assertThat(joinMazeCheck).isGreaterThan(joinSess);
        assertThat(joinSeat).isGreaterThan(joinMazeCheck);
        assertThat(join.indexOf("pinHash()")).isGreaterThan(joinMazeCheck);
        assertThat(join.indexOf("resubscribe()")).isGreaterThan(joinMazeCheck);
        assertThat(join.indexOf("leaveSpectate")).isGreaterThan(joinPost);
        assertThat(join.indexOf("leaveSpectate()")).isGreaterThan(joinMazeCheck);
        // Join takes the seat before leaveSpectate so N51 keeps
        // the session this tab just joined.
        assertThat(joinSeat).isLessThan(join.indexOf("leaveSpectate()"));
        assertThat(join).doesNotContain("state.fog = null");
        assertThat(join).doesNotContain("/session/${state.session.id}");
        assertThat(join).doesNotContain("/maze/${");
        assertThat(join).doesNotContain("tourFor");
        assertThat(join.indexOf("if (!state.session)", joinPost)).isGreaterThan(joinDiscard);
        // N74. Join left leftover ASCII armed. Open session hides
        // #asciiOut (N68). Join did not, so leftover dump reminted
        // under the seat just taken. Hide after the join POST
        // discard. Join-from-spectate still keeps the hunt — must
        // not null tour. startFog still must not null tour (N17).
        int n74Hide = join.indexOf("$(\"asciiOut\").hidden = true");
        int n74Clear = join.indexOf("$(\"asciiOut\").textContent = \"\"");
        assertThat(n74Hide).isGreaterThan(joinMazeCheck);
        assertThat(n74Hide).isLessThan(joinSeat);
        assertThat(n74Clear).isGreaterThan(n74Hide);
        assertThat(n74Clear).isLessThan(joinSeat);
        assertThat(join).doesNotContain("state.tour = null");
        // N75. Join left sibling theory armed. Open session
        // drops leftover cuts (N66). Join did not, so leftover
        // analysis reminted GET /analysis under the seat just
        // taken. Drop those after the join POST discard.
        // Join-from-spectate still keeps the hunt — must not
        // null tour. startFog still must not null tour (N17).
        int n75An = join.indexOf("state.analysis = null");
        int n75Field = join.indexOf("state.field = null");
        assertThat(n75An).isGreaterThan(joinMazeCheck);
        assertThat(n75An).isLessThan(joinSeat);
        assertThat(n75Field).isGreaterThan(n75An);
        assertThat(n75Field).isLessThan(joinSeat);
        assertThat(join).contains("state.lens = null");
        assertThat(join).contains("state.fingerprint = null");
        // N76. Join left a leftover Solve path armed. Open session
        // drops it (N67). Join did not, so leftover solver route
        // reminted POST /solve under the seat just taken. Drop
        // path after the join POST discard. Join-from-spectate
        // still keeps the hunt — must not null tour. startFog
        // still must not null tour (N17).
        int n76Path = join.indexOf("state.path = null");
        assertThat(n76Path).isGreaterThan(joinMazeCheck);
        assertThat(n76Path).isLessThan(joinSeat);
        // N77. Join left leftover Hardest armed. Open session
        // drops leftover gold when caption is hardest (N58).
        // Join did not, so leftover gold reminted GET
        // /hardest-route under the seat just taken. Drop
        // hardest after the join POST discard. Join-from-spectate
        // still keeps the hunt — must not null tour. startFog
        // still must not null tour (N17).
        int n77Hard = join.indexOf("state.hardest = null");
        assertThat(n77Hard).isGreaterThan(joinMazeCheck);
        assertThat(n77Hard).isLessThan(joinSeat);
        // N79. Join left leftover Race armed. Open session
        // drops leftover arena (N55). Join did not, so leftover
        // lanes painted under the seat just taken. Drop race
        // after the join POST discard. Race stays a recording
        // — do not remint. Join-from-spectate still keeps the
        // hunt — must not null tour. startFog still must not
        // null tour (N17).
        int n79Race = join.indexOf("state.race = null");
        int n79Anim = join.indexOf("animGen++");
        assertThat(n79Race).isGreaterThan(joinMazeCheck);
        assertThat(n79Race).isLessThan(joinSeat);
        assertThat(n79Anim).isGreaterThan(n79Race);
        assertThat(n79Anim).isLessThan(joinSeat);
        // N94. Join left leftover Solve stats armed. Open
        // session rewrites #stats (N92). Hunt rewrites when
        // play() is skipped (N93). Join did not, so leftover
        // solver numbers named the previous walk under the
        // seat just taken. Rewrite after the join POST
        // discard. Join-from-spectate still keeps the hunt —
        // must not null tour. startFog still must not null
        // tour (N17).
        int n94Stats = join.indexOf("$(\"stats\").innerHTML =");
        assertThat(n94Stats).isGreaterThan(joinMazeCheck);
        assertThat(n94Stats).isLessThan(joinSeat);
        // N107. Join-from-spectate left leftover spectate
        // join title armed. Open session rewrites #join
        // (label + title). leaveSpectate rewrites when it
        // drops a watch (N105). Join-from-spectate only
        // rewrote the label, so leftover spectate title
        // named a watch that is gone under the seat just
        // taken. Rewrite title after the seat is taken.
        // Join-from-spectate still keeps the hunt — must
        // not null tour. startFog still must not null tour
        // (N17).
        int n107Text = join.lastIndexOf("$(\"join\").textContent");
        int n107Title = join.indexOf("$(\"join\").title");
        assertThat(n107Text).isGreaterThan(joinSeat);
        assertThat(n107Title).isGreaterThan(n107Text);
        // N86. Join leftover ghost is a stay. The ticker is
        // maze-bound (N37): same session still races the
        // recorded best. Competing writers already drop leftover
        // ghost (N80–N84). Join must not drop it. Must not null
        // tour.
        assertThat(join).doesNotContain("state.ghost = null");
        // N78. Remaining remint stays. Competing writers drop
        // leftover remints. These writers must not null tour:
        // Hunt during theory (N63), Hunt through Play (N50),
        // Join-from-spectate, startFog (N17). Theory writes
        // must not always-null a leftover Solve path (N62).
        assertTourStay(html, "async function analyzeStructure", "function paintAnalysisCaption");
        assertTourStay(html, "async function identifyGenerator", "function paintFingerprintCaption");
        assertTourStay(html, "async function distanceHeatMap", "function paintFieldCaption");
        assertTourStay(html, "async function placeSanctuaries", "function paintSanctuariesCaption");
        assertTourStay(html, "async function heuristicLens", "function paintLensCaption");
        assertTourStay(html, "async function play()", "async function join()");
        assertTourStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertTourStay(html, "async function startTour", "function sameCell");
        assertLeftoverComparePathDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        // N91. Remaining leftover paint stays. Competing writers
        // drop leftover paint. These stays must not be taught
        // away: Hunt during theory, leftover Solve path as a
        // theory route hint (N62), Hunt through Play and
        // Join-from-spectate, Fog keeps tour (N17), Join leftover
        // ghost (N86). Race and ghost stay recordings when you
        // asked for them.
        assertThat(join).doesNotContain("state.ghost = null");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverSolveSearchDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
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
        int winGet = win.indexOf("/session/${sessionId}");
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
        // N37. After only fog + session-exists, Generate + Play
        // mid-flight armed the old recording on the maze now on
        // screen. Capture maze id before the GET; discard after
        // when fog is on, the seat is gone, or maze id no longer
        // matches. Ghost is maze-bound, not seat-bound — no
        // session-id pin. Must not GET /maze. startFog still
        // must not null tour (N17).
        assertMazeIdDiscardAfterFetch(html, "async function summonGhost",
                "async function simulateTraffic", "state.ghost");
        int n37Id = ghost.indexOf("const mazeId");
        int n37Get = ghost.indexOf("/maze/${mazeId}/ghost");
        int n37Fog = ghost.indexOf("if (state.fog)", n37Get);
        int n37Sess = ghost.indexOf("if (!state.session)", n37Get);
        int n37Maze = ghost.indexOf("state.maze.id !== mazeId", n37Get);
        int n37Arm = ghost.indexOf("state.ghost =", n37Maze);
        assertThat(n37Id).isGreaterThanOrEqualTo(0);
        assertThat(n37Id).isLessThan(n37Get);
        assertThat(n37Get).isGreaterThanOrEqualTo(0);
        assertThat(n37Fog).isGreaterThan(n37Get);
        assertThat(n37Sess).isGreaterThan(n37Fog);
        assertThat(n37Maze).isGreaterThan(n37Sess);
        assertThat(n37Arm).isGreaterThan(n37Maze);
        assertThat(ghost.indexOf("setInterval", n37Arm)).isGreaterThan(n37Arm);
        assertThat(ghost).doesNotContain("/maze/${state.maze.id}");
        assertThat(ghost).doesNotContain("tourFor");
        assertThat(ghost).doesNotContain("state.session.id !== sessionId");
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
        // N46. N29 discarded the UI bind after the POST. Generate
        // that already won the canvas still started /live or
        // /traffic on the stage you left — a ticker on a maze
        // the bar no longer names. Gate before the first hazard
        // POST (and before each later one). After-POST discard
        // stays (N29). Not if (state.fog) in the loop.
        int n46Play = n29.indexOf("await play()");
        int n46Gate = n29.indexOf("state.maze.id !== stage.mazeId", n46Play);
        assertThat(n46Play).isGreaterThanOrEqualTo(0);
        assertThat(n46Gate).isGreaterThan(n46Play);
        assertThat(n46Gate).isLessThan(n29Post);
        int n46LoopGate = n29.indexOf("state.maze.id !== stage.mazeId", n29Hazards);
        assertThat(n46LoopGate).isGreaterThan(n29Hazards);
        assertThat(n46LoopGate).isLessThan(n29Post);
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
        // N47. fingerprintWhenReady retried GET /fingerprint for 60s
        // on 503. Generate / Fog left that maze; the wait still
        // minted work against the id you left. identifyGenerator
        // already discards the paint (N30). Abort the loop when fog
        // is on or maze id no longer matches, before the next GET.
        int n47From = html.indexOf("async function fingerprintWhenReady");
        int n47To = html.indexOf("async function identifyGenerator");
        assertThat(n47From).isGreaterThanOrEqualTo(0);
        assertThat(n47To).isGreaterThan(n47From);
        String n47 = html.substring(n47From, n47To);
        int n47Id = n47.indexOf("state.maze.id !== id");
        int n47Get = n47.indexOf("api(`/maze/${id}/fingerprint`)");
        assertThat(n47Id).isGreaterThanOrEqualTo(0);
        assertThat(n47Get).isGreaterThanOrEqualTo(0);
        assertThat(n47Id).isLessThan(n47Get);
        assertThat(n47).contains("state.fog");
        assertThat(n47).contains("return null");
        // N48. flashStatus restores the captured line after 900ms.
        // Generate / Fog / Back / a new Open session already wrote
        // the new status; the leftover restore put the old session
        // or hunt text on a maze that no longer has that seat.
        // Clear the timer before those writers set status. move()
        // still flashes after its fog / seat discard (N27).
        assertStatusFlashClearedBeforeWrite(html, "function adoptMaze",
                "// Snapshot whatever is on the canvas");
        assertStatusFlashClearedBeforeWrite(html, "function leaveMaze",
                "async function loadFromHash");
        assertStatusFlashClearedBeforeWrite(html, "async function play",
                "async function join");
        assertStatusFlashClearedBeforeWrite(html, "async function startFog",
                "async function fogStep");
        // N49. Solve / race rAF kept writing progress after Generate /
        // Fog / Back zeroed path and race. A leftover frame could
        // finish the reveal or raceSummary the maze now on screen.
        // Bump animGen on those leave paths; step returns when gen
        // no longer matches.
        int n49SearchFrom = html.indexOf("function animateSearch");
        int n49SearchTo = html.indexOf("function animatePath");
        assertThat(n49SearchFrom).isGreaterThanOrEqualTo(0);
        assertThat(n49SearchTo).isGreaterThan(n49SearchFrom);
        String n49Search = html.substring(n49SearchFrom, n49SearchTo);
        int n49Gen = n49Search.indexOf("const gen = ++animGen");
        int n49Guard = n49Search.indexOf("if (gen !== animGen) return");
        int n49Prog = n49Search.indexOf("state.pathProgress = Math.max");
        assertThat(n49Gen).isGreaterThanOrEqualTo(0);
        assertThat(n49Guard).isGreaterThan(n49Gen);
        assertThat(n49Guard).isLessThan(n49Prog);
        int n49RaceFrom = html.indexOf("function animateRace");
        int n49RaceTo = html.indexOf("function raceSummary");
        assertThat(n49RaceFrom).isGreaterThanOrEqualTo(0);
        assertThat(n49RaceTo).isGreaterThan(n49RaceFrom);
        String n49Race = html.substring(n49RaceFrom, n49RaceTo);
        assertThat(n49Race.indexOf("const gen = ++animGen")).isGreaterThanOrEqualTo(0);
        assertThat(n49Race.indexOf("if (gen !== animGen) return"))
                .isGreaterThan(n49Race.indexOf("const gen = ++animGen"));
        String n49Adopt = html.substring(html.indexOf("function adoptMaze"),
                html.indexOf("// Snapshot whatever is on the canvas"));
        String n49Leave = html.substring(html.indexOf("function leaveMaze"),
                html.indexOf("async function loadFromHash"));
        String n49Fog = html.substring(html.indexOf("async function startFog"),
                html.indexOf("async function fogStep"));
        assertThat(n49Adopt).contains("animGen++");
        assertThat(n49Leave).contains("animGen++");
        assertThat(n49Fog).contains("animGen++");
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
        // N50. Hunt installed the tour and left Compare / Analyze /
        // Hardest / Lens armed. A leftover compare hover painted a
        // solver path over the Held-Karp corridor; leftover hardest
        // was a second walk that is not the score. Drop those
        // overlays after the maze-id discard, before play(). Fog
        // already drops them. Must not null tour (N17).
        int n50Box = n31.indexOf("$(\"compareBox\").innerHTML = \"\"");
        int n50Hard = n31.indexOf("state.hardest = null");
        int n50Path = n31.indexOf("state.path = null");
        assertThat(n50Box).isGreaterThan(n31Discard);
        assertThat(n50Box).isLessThan(n31Play);
        assertThat(n50Hard).isGreaterThan(n31Discard);
        assertThat(n50Hard).isLessThan(n31Play);
        assertThat(n50Path).isGreaterThan(n31Discard);
        assertThat(n50Path).isLessThan(n31Play);
        assertThat(n31).contains("state.analysis = null");
        assertThat(n31).contains("state.lens = null");
        assertThat(n31).contains("animGen++");
        assertThat(n31).doesNotContain("state.tour = null");
        // N72. Hunt left leftover ASCII armed. play() hides it
        // (N68) only when it seats; a hunt on an existing seat
        // skipped that hide, so leftover dump reminted under
        // the Held-Karp walk. Hide after the maze-id discard,
        // before play(). Must not null tour (N50). startFog
        // still must not null tour (N17).
        int n72Hide = n31.indexOf("$(\"asciiOut\").hidden = true");
        int n72Clear = n31.indexOf("$(\"asciiOut\").textContent = \"\"");
        assertThat(n72Hide).isGreaterThan(n31Discard);
        assertThat(n72Hide).isLessThan(n31Play);
        assertThat(n72Clear).isGreaterThan(n72Hide);
        assertThat(n72Clear).isLessThan(n31Play);
        // N84. Hunt left leftover ghost armed. play() re-summons
        // only when it seats; a hunt on an existing seat skipped
        // that, so leftover recording painted under the Held-Karp
        // walk. Drop it after the maze-id discard, before play().
        // Must not null tour (N50). startFog still must not null
        // tour (N17).
        int n84Clear = n31.indexOf("clearInterval(state.ghostTimer)");
        int n84Timer = n31.indexOf("state.ghostTimer = null");
        int n84Gone = n31.indexOf("state.ghost = null");
        assertThat(n84Clear).isGreaterThan(n31Discard);
        assertThat(n84Clear).isLessThan(n31Play);
        assertThat(n84Timer).isGreaterThan(n84Clear);
        assertThat(n84Timer).isLessThan(n31Play);
        assertThat(n84Gone).isGreaterThan(n84Timer);
        assertThat(n84Gone).isLessThan(n31Play);
        // N93. Hunt left leftover Solve stats armed. play()
        // rewrites #stats (N92) only when it seats; a hunt on
        // an existing seat skipped that, so leftover solver
        // numbers named the previous walk under the Held-Karp
        // coins. Rewrite after the maze-id discard, before
        // play(). Must not null tour (N50). startFog still
        // must not null tour (N17).
        int n93Stats = n31.indexOf("$(\"stats\").innerHTML =");
        assertThat(n93Stats).isGreaterThan(n31Discard);
        assertThat(n93Stats).isLessThan(n31Play);
        // N106. Hunt left leftover Hunt / win status armed.
        // play() rewrites #status (N48) only when it seats;
        // refreshTourStatus remints hunt status only when the
        // tour is feasible. An infeasible hunt skipped both,
        // so leftover "waypoint hunt" or leftover "reached
        // the goal" named the previous walk under the new
        // coins. Rewrite after the maze-id discard, before
        // play(). Must not null tour (N50). startFog still
        // must not null tour (N17).
        int n106Flash = n31.indexOf("clearTimeout(statusFlashTimer)");
        int n106Status = n31.indexOf("$(\"status\").textContent");
        assertThat(n106Flash).isGreaterThan(n31Discard);
        assertThat(n106Flash).isLessThan(n31Play);
        assertThat(n106Status).isGreaterThan(n106Flash);
        assertThat(n106Status).isLessThan(n31Play);
        // N53. Race / Compare left Hunt coins and hardest armed.
        // Leftover tourWalk painted under the arena / a compare
        // hover — not a solver lane. Drop those overlays after
        // the maze-id discard. Hunt already drops leftover theory
        // (N50). startFog still must not null tour (N17).
        int n53RaceFrom = html.indexOf("async function raceSolvers");
        int n53RaceTo = html.indexOf("function animateRace");
        assertThat(n53RaceFrom).isGreaterThanOrEqualTo(0);
        assertThat(n53RaceTo).isGreaterThan(n53RaceFrom);
        String n53Race = html.substring(n53RaceFrom, n53RaceTo);
        int n53RaceDiscard = n53Race.lastIndexOf("state.maze.id !== mazeId");
        int n53RaceTour = n53Race.indexOf("state.tour = null");
        int n53RaceSet = n53Race.indexOf("state.race =");
        assertThat(n53RaceDiscard).isGreaterThanOrEqualTo(0);
        assertThat(n53RaceTour).isGreaterThan(n53RaceDiscard);
        assertThat(n53RaceTour).isLessThan(n53RaceSet);
        assertThat(n53Race).contains("state.hardest = null");
        // N71. Race / Compare left leftover ASCII armed. Generate
        // / Fog / Play / Solve / Hardest hide #asciiOut (N68–N70).
        // Those arena writes did not, so leftover dump reminted
        // the text/plain maze under the lanes / a compare hover.
        // Hide it after the maze-id discard. startFog still must
        // not null tour (N17).
        int n71RaceHide = n53Race.indexOf("$(\"asciiOut\").hidden = true");
        int n71RaceClear = n53Race.indexOf("$(\"asciiOut\").textContent = \"\"");
        assertThat(n71RaceHide).isGreaterThan(n53RaceDiscard);
        assertThat(n71RaceHide).isLessThan(n53RaceSet);
        assertThat(n71RaceClear).isGreaterThan(n71RaceHide);
        assertThat(n71RaceClear).isLessThan(n53RaceSet);
        // N83. Race / Compare left leftover ghost armed. Fog
        // already drops the ticker. Theory / Solve / Hardest
        // already drop it (N80–N82). Those arena writes did
        // not, so leftover recording painted under the lanes /
        // a compare hover. Drop it after the maze-id discard.
        // startFog still must not null tour (N17).
        int n83RaceClear = n53Race.indexOf("clearInterval(state.ghostTimer)");
        int n83RaceTimer = n53Race.indexOf("state.ghostTimer = null");
        int n83RaceGone = n53Race.indexOf("state.ghost = null");
        assertThat(n83RaceClear).isGreaterThan(n53RaceDiscard);
        assertThat(n83RaceClear).isLessThan(n53RaceSet);
        assertThat(n83RaceTimer).isGreaterThan(n83RaceClear);
        assertThat(n83RaceTimer).isLessThan(n53RaceSet);
        assertThat(n83RaceGone).isGreaterThan(n83RaceTimer);
        assertThat(n83RaceGone).isLessThan(n53RaceSet);
        // N89. Race left leftover sidebar armed. Hunt already
        // empties #compareBox (N50). Race did not, so leftover
        // cuts caption or a leftover compare hover painted under
        // the arena. Empty it after the maze-id discard.
        int n89Cap = n53Race.indexOf("state.caption = null");
        int n89Box = n53Race.indexOf("$(\"compareBox\").innerHTML = \"\"");
        assertThat(n89Cap).isGreaterThan(n53RaceDiscard);
        assertThat(n89Cap).isLessThan(n53RaceSet);
        assertThat(n89Box).isGreaterThan(n89Cap);
        assertThat(n89Box).isLessThan(n53RaceSet);
        // N97. Race left leftover Solve stats armed. Play /
        // Hunt / Join / Fog / Hardest rewrite #stats (N92–N96).
        // Race did not, so leftover solver numbers named the
        // previous walk under the arena. Rewrite after the
        // maze-id discard. startFog still must not null tour
        // (N17).
        int n97Stats = n53Race.indexOf("$(\"stats\").innerHTML =");
        assertThat(n97Stats).isGreaterThan(n53RaceDiscard);
        assertThat(n97Stats).isLessThan(n53RaceSet);
        // N103. Race left leftover Hunt status armed. Generate /
        // Fog / Play rewrite #status (N48). Solve / Hardest
        // rewrite after dropping tour (N101 / N102). Race
        // dropped tour (N53) but left leftover hunt text, so
        // leftover "waypoint hunt" named a hunt that is gone
        // under the arena. Rewrite after the maze-id discard.
        // startFog still must not null tour (N17).
        int n103Flash = n53Race.indexOf("clearTimeout(statusFlashTimer)");
        int n103Status = n53Race.indexOf("$(\"status\").textContent");
        assertThat(n103Flash).isGreaterThan(n53RaceDiscard);
        assertThat(n103Flash).isLessThan(n53RaceSet);
        assertThat(n103Status).isGreaterThan(n103Flash);
        assertThat(n103Status).isLessThan(n53RaceSet);
        int n53CmpFrom = html.indexOf("async function compareSolvers");
        int n53CmpTo = html.indexOf("async function play()", n53CmpFrom);
        assertThat(n53CmpFrom).isGreaterThanOrEqualTo(0);
        assertThat(n53CmpTo).isGreaterThan(n53CmpFrom);
        String n53Cmp = html.substring(n53CmpFrom, n53CmpTo);
        int n53CmpDiscard = n53Cmp.lastIndexOf("state.maze.id !== mazeId");
        int n53CmpTour = n53Cmp.indexOf("state.tour = null");
        int n53CmpBox = n53Cmp.lastIndexOf("$(\"compareBox\")");
        assertThat(n53CmpDiscard).isGreaterThanOrEqualTo(0);
        assertThat(n53CmpTour).isGreaterThan(n53CmpDiscard);
        assertThat(n53CmpTour).isLessThan(n53CmpBox);
        assertThat(n53Cmp).contains("state.hardest = null");
        int n71CmpHide = n53Cmp.indexOf("$(\"asciiOut\").hidden = true");
        int n71CmpClear = n53Cmp.indexOf("$(\"asciiOut\").textContent = \"\"");
        assertThat(n71CmpHide).isGreaterThan(n53CmpDiscard);
        assertThat(n71CmpHide).isLessThan(n53CmpBox);
        assertThat(n71CmpClear).isGreaterThan(n71CmpHide);
        assertThat(n71CmpClear).isLessThan(n53CmpBox);
        int n83CmpClear = n53Cmp.indexOf("clearInterval(state.ghostTimer)");
        int n83CmpTimer = n53Cmp.indexOf("state.ghostTimer = null");
        int n83CmpGone = n53Cmp.indexOf("state.ghost = null");
        assertThat(n83CmpClear).isGreaterThan(n53CmpDiscard);
        assertThat(n83CmpClear).isLessThan(n53CmpBox);
        assertThat(n83CmpTimer).isGreaterThan(n83CmpClear);
        assertThat(n83CmpTimer).isLessThan(n53CmpBox);
        assertThat(n83CmpGone).isGreaterThan(n83CmpTimer);
        assertThat(n83CmpGone).isLessThan(n53CmpBox);
        // N88. Compare left leftover Race armed. Play / theory /
        // Solve / Hardest / Join / Hunt already drop leftover
        // arena. Compare did not, so leftover lanes painted
        // under a compare hover. Drop race after the maze-id
        // discard. startFog still must not null tour (N17).
        int n88Race = n53Cmp.indexOf("state.race = null");
        int n88Anim = n53Cmp.indexOf("animGen++");
        assertThat(n88Race).isGreaterThan(n53CmpDiscard);
        assertThat(n88Race).isLessThan(n53CmpBox);
        assertThat(n88Anim).isGreaterThan(n88Race);
        assertThat(n88Anim).isLessThan(n53CmpBox);
        // N90. Compare left leftover Solve path armed. Race
        // already drops leftover path. Compare did not, so
        // leftover solver route painted under the table until a
        // hover. Drop path after the maze-id discard. Hover
        // still arms a preview. startFog still must not null
        // tour (N17).
        int n90Path = n53Cmp.indexOf("state.path = null");
        int n90Exp = n53Cmp.indexOf("state.expansions = []");
        assertThat(n90Path).isGreaterThan(n53CmpDiscard);
        assertThat(n90Path).isLessThan(n53CmpBox);
        assertThat(n90Exp).isGreaterThan(n90Path);
        assertThat(n90Exp).isLessThan(n53CmpBox);
        // N98. Compare left leftover Solve stats armed. Play /
        // Hunt / Join / Fog / Hardest / Race rewrite #stats
        // (N92–N97). Compare did not, so leftover solver
        // numbers named the previous walk under the table.
        // Rewrite after the maze-id discard. Hover still arms
        // a preview. startFog still must not null tour (N17).
        int n98Stats = n53Cmp.indexOf("$(\"stats\").innerHTML =");
        assertThat(n98Stats).isGreaterThan(n53CmpDiscard);
        assertThat(n98Stats).isLessThan(n53CmpBox);
        // N104. Compare left leftover Hunt status armed.
        // Generate / Fog / Play rewrite #status (N48). Solve /
        // Hardest / Race rewrite after dropping tour
        // (N101–N103). Compare dropped tour (N53) but left
        // leftover hunt text, so leftover "waypoint hunt"
        // named a hunt that is gone under the table. Rewrite
        // after the maze-id discard. Hover still arms a
        // preview. startFog still must not null tour (N17).
        int n104Flash = n53Cmp.indexOf("clearTimeout(statusFlashTimer)");
        int n104Status = n53Cmp.indexOf("$(\"status\").textContent");
        assertThat(n104Flash).isGreaterThan(n53CmpDiscard);
        assertThat(n104Flash).isLessThan(n53CmpBox);
        assertThat(n104Status).isGreaterThan(n104Flash);
        assertThat(n104Status).isLessThan(n53CmpBox);
        // N65. Solve left Hunt coins / Hardest / sibling theory
        // armed. Leftover tourWalk / leftover gold painted under
        // the solver path; leftover cuts reminted GET /analysis.
        // Drop those after the maze-id discard. Race / Compare
        // already drop them (N53). Hardest already drops leftover
        // Hunt and sibling theory (N59 / N64). startFog still
        // must not null tour (N17).
        int n65From = html.indexOf("async function solve");
        int n65To = html.indexOf("function animateSearch");
        assertThat(n65From).isGreaterThanOrEqualTo(0);
        assertThat(n65To).isGreaterThan(n65From);
        String n65 = html.substring(n65From, n65To);
        int n65Discard = n65.lastIndexOf("state.maze.id !== mazeId");
        int n65Tour = n65.indexOf("state.tour = null");
        int n65An = n65.indexOf("state.analysis = null");
        int n65Hard = n65.indexOf("state.hardest = null");
        int n65Path = n65.indexOf("state.path = r.path");
        assertThat(n65Discard).isGreaterThanOrEqualTo(0);
        assertThat(n65Tour).isGreaterThan(n65Discard);
        assertThat(n65Tour).isLessThan(n65Path);
        assertThat(n65An).isGreaterThan(n65Tour);
        assertThat(n65An).isLessThan(n65Path);
        assertThat(n65Hard).isGreaterThan(n65An);
        assertThat(n65Hard).isLessThan(n65Path);
        assertThat(n65).contains("state.field = null");
        assertThat(n65).contains("state.lens = null");
        assertThat(n65).contains("state.fingerprint = null");
        assertThat(n65).contains("state.race = null");
        // N69. Solve left leftover ASCII armed. Generate / Fog /
        // Play hide #asciiOut (N68). Solve did not, so leftover
        // dump reminted the text/plain maze under the solver path.
        // Hide it after the maze-id discard. startFog still must
        // not null tour (N17).
        int n69Hide = n65.indexOf("$(\"asciiOut\").hidden = true");
        int n69Clear = n65.indexOf("$(\"asciiOut\").textContent = \"\"");
        assertThat(n69Hide).isGreaterThan(n65Discard);
        assertThat(n69Hide).isLessThan(n65Path);
        assertThat(n69Clear).isGreaterThan(n69Hide);
        assertThat(n69Clear).isLessThan(n65Path);
        // N81. Solve left leftover ghost armed. Fog already
        // drops the ticker. Theory writes already drop it
        // (N80). Solve dropped leftover Race but not ghost,
        // so leftover recording painted under the solver path.
        // Drop it after the maze-id discard.
        int n81Clear = n65.indexOf("clearInterval(state.ghostTimer)");
        int n81Timer = n65.indexOf("state.ghostTimer = null");
        int n81Gone = n65.indexOf("state.ghost = null");
        assertThat(n81Clear).isGreaterThan(n65Discard);
        assertThat(n81Clear).isLessThan(n65Path);
        assertThat(n81Timer).isGreaterThan(n81Clear);
        assertThat(n81Timer).isLessThan(n65Path);
        assertThat(n81Gone).isGreaterThan(n81Timer);
        assertThat(n81Gone).isLessThan(n65Path);
        // N101. Solve left leftover Hunt status armed.
        // Generate / Fog / Play rewrite #status (N48). Solve
        // dropped tour (N65) but left leftover hunt text, so
        // leftover "waypoint hunt" named a hunt that is gone
        // under the solver path. Rewrite after the maze-id
        // discard. startFog still must not null tour (N17).
        int n101Flash = n65.indexOf("clearTimeout(statusFlashTimer)");
        int n101Status = n65.indexOf("$(\"status\").textContent");
        assertThat(n101Flash).isGreaterThan(n65Discard);
        assertThat(n101Flash).isLessThan(n65Path);
        assertThat(n101Status).isGreaterThan(n101Flash);
        assertThat(n101Status).isLessThan(n65Path);
        // N59. Hardest left Hunt coins and Race lanes armed.
        // Leftover tourWalk / leftover arena painted over the
        // cruel route. Drop those after the maze-id discard.
        // Race / Compare already drop leftover Hunt (N53).
        // startFog still must not null tour (N17).
        int n59From = html.indexOf("async function hardestRoute");
        int n59To = html.indexOf("function paintHardestCaption");
        assertThat(n59From).isGreaterThanOrEqualTo(0);
        assertThat(n59To).isGreaterThan(n59From);
        String n59 = html.substring(n59From, n59To);
        int n59Discard = n59.lastIndexOf("state.maze.id !== mazeId");
        int n59Tour = n59.indexOf("state.tour = null");
        int n59Race = n59.indexOf("state.race = null");
        int n59Path = n59.indexOf("state.path = null");
        int n59Set = n59.indexOf("state.hardest = h");
        assertThat(n59Discard).isGreaterThanOrEqualTo(0);
        assertThat(n59Tour).isGreaterThan(n59Discard);
        assertThat(n59Tour).isLessThan(n59Set);
        assertThat(n59Race).isGreaterThan(n59Tour);
        assertThat(n59Race).isLessThan(n59Set);
        assertThat(n59Path).isGreaterThan(n59Race);
        assertThat(n59Path).isLessThan(n59Set);
        assertThat(n59).contains("animGen++");
        // N64. Hardest left sibling theory armed. Leftover cuts
        // reminted GET /analysis under the gold walk. Drop those
        // after the maze-id discard. Theory writes already drop
        // siblings (N63). startFog still must not null tour.
        int n64An = n59.indexOf("state.analysis = null");
        int n64Field = n59.indexOf("state.field = null");
        assertThat(n64An).isGreaterThan(n59Discard);
        assertThat(n64An).isLessThan(n59Set);
        assertThat(n64Field).isGreaterThan(n64An);
        assertThat(n64Field).isLessThan(n59Set);
        assertThat(n59).contains("state.lens = null");
        assertThat(n59).contains("state.fingerprint = null");
        // N70. Hardest left leftover ASCII armed. Generate / Fog /
        // Play / Solve hide #asciiOut (N68 / N69). Hardest did
        // not, so leftover dump reminted the text/plain maze under
        // the gold walk. Hide it after the maze-id discard.
        // startFog still must not null tour (N17).
        int n70Hide = n59.indexOf("$(\"asciiOut\").hidden = true");
        int n70Clear = n59.indexOf("$(\"asciiOut\").textContent = \"\"");
        assertThat(n70Hide).isGreaterThan(n59Discard);
        assertThat(n70Hide).isLessThan(n59Set);
        assertThat(n70Clear).isGreaterThan(n70Hide);
        assertThat(n70Clear).isLessThan(n59Set);
        // N82. Hardest left leftover ghost armed. Fog already
        // drops the ticker. Theory / Solve already drop it
        // (N80 / N81). Hardest dropped leftover Race but not
        // ghost, so leftover recording painted under the gold
        // walk. Drop it after the maze-id discard.
        int n82Clear = n59.indexOf("clearInterval(state.ghostTimer)");
        int n82Timer = n59.indexOf("state.ghostTimer = null");
        int n82Gone = n59.indexOf("state.ghost = null");
        assertThat(n82Clear).isGreaterThan(n59Discard);
        assertThat(n82Clear).isLessThan(n59Set);
        assertThat(n82Timer).isGreaterThan(n82Clear);
        assertThat(n82Timer).isLessThan(n59Set);
        assertThat(n82Gone).isGreaterThan(n82Timer);
        assertThat(n82Gone).isLessThan(n59Set);
        // N96. Hardest left leftover Solve stats armed. Play /
        // Hunt / Join / Fog rewrite #stats (N92–N95). Hardest
        // did not, so leftover solver numbers named the
        // previous walk under the gold walk. Rewrite after
        // the maze-id discard. startFog still must not null
        // tour (N17).
        int n96Stats = n59.indexOf("$(\"stats\").innerHTML =");
        assertThat(n96Stats).isGreaterThan(n59Discard);
        assertThat(n96Stats).isLessThan(n59Set);
        // N102. Hardest left leftover Hunt status armed.
        // Generate / Fog / Play rewrite #status (N48). Solve
        // rewrites after dropping tour (N101). Hardest dropped
        // tour (N59) but left leftover hunt text, so leftover
        // "waypoint hunt" named a hunt that is gone under the
        // gold walk. Rewrite after the maze-id discard.
        // startFog still must not null tour (N17).
        int n102Flash = n59.indexOf("clearTimeout(statusFlashTimer)");
        int n102Status = n59.indexOf("$(\"status\").textContent");
        assertThat(n102Flash).isGreaterThan(n59Discard);
        assertThat(n102Flash).isLessThan(n59Set);
        assertThat(n102Status).isGreaterThan(n102Flash);
        assertThat(n102Status).isLessThan(n59Set);
        // N60. Theory writes left Race lanes armed. Leftover arena
        // painted over the cuts / field / rings / bands / Identify
        // sidebar. Drop race after the maze-id discard. Hunt stays
        // (chokepoints during a hunt are useful). startFog still
        // must not null tour (N17).
        assertLeftoverRaceDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverRaceDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverRaceDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverRaceDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverRaceDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N80. Theory writes left leftover ghost armed. Fog
        // already drops the ticker. Those writes dropped leftover
        // Race (N60) but not ghost, so leftover recording painted
        // under the cuts / field / rings / bands / Identify
        // sidebar. Drop it after the maze-id discard. Hunt and a
        // leftover Solve path stay. startFog still must not null
        // tour (N17).
        assertLeftoverGhostDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverGhostDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverGhostDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverGhostDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverGhostDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N61. Theory writes left Hardest armed. Leftover gold
        // painted over the cuts / field / rings / bands, and a
        // living tick reminted GET /hardest-route. Drop hardest
        // after the maze-id discard. Hunt stays. startFog still
        // must not null tour (N17).
        assertLeftoverHardestDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverHardestDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverHardestDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverHardestDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverHardestDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N62. Theory writes left Compare hover armed. Leftover
        // solver path painted over the theory and a living tick
        // reminted POST /solve. Drop path after the maze-id
        // discard when caption is compare. Do not null a leftover
        // Solve path (route hint). Hunt stays. startFog still
        // must not null tour (N17).
        assertLeftoverComparePathDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverComparePathDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverComparePathDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverComparePathDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverComparePathDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N87. Theory writes left leftover Solve search wash
        // armed. Leftover path stays as a route hint (N62).
        // Leftover expansions painted the wash under the cuts /
        // field / rings / bands / Identify sidebar. Drop the
        // wash after the maze-id discard. Hunt stays. startFog
        // still must not null tour (N17).
        assertLeftoverSolveSearchDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverSolveSearchDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverSolveSearchDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverSolveSearchDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverSolveSearchDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N99. Theory writes left leftover Solve stats armed.
        // Play / Hunt / Join / Fog / Hardest / Race / Compare
        // rewrite #stats (N92–N98). Theory writes did not, so
        // leftover solver numbers named the previous walk under
        // the cuts / field / rings / bands / Identify sidebar.
        // Rewrite after the maze-id discard. Hunt and a leftover
        // Solve path stay. startFog still must not null tour
        // (N17).
        assertLeftoverSolveStatsDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverSolveStatsDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverSolveStatsDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverSolveStatsDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverSolveStatsDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N100. Remaining leftover #stats stays. Competing
        // writers rewrite maze identity (N92–N99). These stays
        // must not be taught away: Solve still appends current
        // walk figures; ASCII / living / ghost / lab do not
        // rewrite #stats; Hunt through Play and Join-from-
        // spectate still keep tour; Fog still keeps tour
        // (N17); leftover Solve path stays as a theory route
        // hint (N62); Join leftover ghost stays (N86).
        assertThat(n65).contains("$(\"stats\").innerHTML +=");
        String n100Ascii = html.substring(html.indexOf("async function showAscii"),
                html.indexOf("async function loadAlgorithms"));
        assertThat(n100Ascii).doesNotContain("$(\"stats\")");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N108. Remaining leftover #status / #join stays.
        // Competing writers rewrite leftover hunt / win /
        // spectate chrome (N48 / N101–N107). These stays
        // must not be taught away: Hunt / session / win
        // lines during theory stay current; ASCII does not
        // rewrite #status; Fog leftover #join text stays
        // (Play already set the seated label; Fog only
        // disables); Hunt through Play and Join-from-
        // spectate still keep tour; Fog still keeps tour
        // (N17); leftover Solve path stays as a theory
        // route hint (N62); Join leftover ghost stays
        // (N86).
        String n108An = html.substring(html.indexOf("async function analyzeStructure"),
                html.indexOf("function paintAnalysisCaption"));
        assertThat(n108An).doesNotContain("$(\"status\")");
        String n108Ascii = html.substring(html.indexOf("async function showAscii"),
                html.indexOf("async function loadAlgorithms"));
        assertThat(n108Ascii).doesNotContain("$(\"status\")");
        String n108Fog = html.substring(html.indexOf("async function startFog"),
                html.indexOf("async function fogStep"));
        assertThat(n108Fog).contains("$(\"join\").disabled = true");
        assertThat(n108Fog).doesNotContain("$(\"join\").textContent");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        assertThat(join).doesNotContain("state.tour = null");
        // N111. Remaining leftover trails / won / leaderboard
        // stays. Competing writers drop leftover crumbs / won
        // (N109 / N110) and remint the board on maze change
        // (adoptMaze / Daily / campaign / leaveMaze /
        // declareWin). These stays must not be taught away:
        // Hunt leftover trails stay — current walk; theory
        // leftover trails stay — current walk; Join leftover
        // opener trails stay — same session; leftover won
        // during Hunt / theory / Join stays — session still
        // won; leftover leaderboard / leftover #lb title stay
        // — same maze; Play / Fog / Hunt / theory / Join do
        // not remint; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62); Join leftover ghost stays (N86).
        assertLeftoverWalkChromeStay(html, "async function startTour", "function sameCell");
        assertLeftoverWalkChromeStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverWalkChromeStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverWalkChromeStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverWalkChromeStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverWalkChromeStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverWalkChromeStay(html, "async function join()", "async function move(");
        String n111Play = html.substring(html.indexOf("async function play()"),
                html.indexOf("async function join()"));
        assertThat(n111Play).doesNotContain("refreshLeaderboard");
        assertThat(fog).doesNotContain("refreshLeaderboard");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N112. Remaining leftover campaign stays. pinHash
        // already drops the ladder when the exclusive kind
        // is not campaign. These stays must not be taught
        // away: Hunt / Play / Fog / theory / Join leftover
        // campaign stay — same maze; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverCampaignStay(html, "async function startTour", "function sameCell");
        assertLeftoverCampaignStay(html, "async function play()", "async function join()");
        assertLeftoverCampaignStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverCampaignStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverCampaignStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverCampaignStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverCampaignStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverCampaignStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverCampaignStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N113. Remaining leftover live / traffic stays.
        // adoptMaze / leaveMaze already drop leftover polls.
        // Living under fog is honest (N19): the poller is
        // maze-bound and re-polls the agent instead of GET
        // /maze. These stays must not be taught away: Hunt /
        // Play / Fog / theory / Join leftover live stay —
        // same maze still erodes; leftover #live / #traffic
        // disabled stay — maze still alive; Hunt through
        // Play and Join-from-spectate still keep tour; Fog
        // still keeps tour (N17); leftover Solve path stays
        // as a theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverLiveStay(html, "async function startTour", "function sameCell");
        assertLeftoverLiveStay(html, "async function play()", "async function join()");
        assertLeftoverLiveStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLiveStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLiveStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLiveStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLiveStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLiveStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLiveStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N114. Remaining leftover form stays. adoptMaze /
        // leaveMaze / applyRecipeToForm already rewrite the
        // recipe on maze change. These stays must not be
        // taught away: Hunt / Play / Fog / theory / Join
        // leftover form stay — same maze recipe; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86).
        assertLeftoverFormStay(html, "async function startTour", "function sameCell");
        assertLeftoverFormStay(html, "async function play()", "async function join()");
        assertLeftoverFormStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverFormStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverFormStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverFormStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverFormStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverFormStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverFormStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N115. Remaining leftover plugin / log / player stays.
        // refreshPlugins remints the roster on login / logout /
        // plugin failure. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover plugin stay
        // — global catalog; leftover log stay — history;
        // leftover #player stay — the name you typed; Hunt
        // through Play and Join-from-spectate still keep tour;
        // Fog still keeps tour (N17); leftover Solve path stays
        // as a theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverCatalogStay(html, "async function startTour", "function sameCell");
        assertLeftoverCatalogStay(html, "async function play()", "async function join()");
        assertLeftoverCatalogStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverCatalogStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverCatalogStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverCatalogStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverCatalogStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverCatalogStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverCatalogStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N116. Remaining leftover lab / tournament / PNG stays.
        // Measure and Run tournament remint those panels when
        // you ask. adoptMaze / leaveMaze already show or hide
        // the snapshot. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover lab stay
        // — the curve you asked for; leftover tournament stay
        // — the sample you asked for; leftover PNG stay —
        // same maze canvas (fog snapshot is the fog walk);
        // Hunt through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86).
        assertLeftoverLabStay(html, "async function startTour", "function sameCell");
        assertLeftoverLabStay(html, "async function play()", "async function join()");
        assertLeftoverLabStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLabStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLabStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLabStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLabStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLabStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLabStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N117 stay. Remaining leftover tourGot during theory /
        // Join stays. Fog / Play drop leftover collected coins
        // when the seat that collected them is gone. These
        // stays must not be taught away: theory leftover
        // tourGot stay — current hunt; Join leftover tourGot
        // stay — same session; Hunt remints empty coins then
        // collects; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17).
        assertLeftoverTourGotStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverTourGotStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverTourGotStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverTourGotStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverTourGotStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverTourGotStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N118. Remaining leftover auth stays. login / logout
        // already remint the token. These stays must not be
        // taught away: Hunt / Play / Fog / theory / Join
        // leftover auth stay — still signed in; leftover
        // #authWho stay — the name you signed in as; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86).
        assertLeftoverAuthStay(html, "async function startTour", "function sameCell");
        assertLeftoverAuthStay(html, "async function play()", "async function join()");
        assertLeftoverAuthStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverAuthStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverAuthStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverAuthStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverAuthStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverAuthStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverAuthStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N119. Remaining leftover daily / breed stays.
        // adoptMaze / playStage / leaveMaze already drop
        // leftover dailyId and leftover breed parent on
        // maze change. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover daily
        // stay — same maze still daily; leftover prevMazeId
        // / leftover #breed stay — breed parent still
        // valid; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62); Join leftover ghost stays (N86).
        assertLeftoverDailyBreedStay(html, "async function startTour", "function sameCell");
        assertLeftoverDailyBreedStay(html, "async function play()", "async function join()");
        assertLeftoverDailyBreedStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverDailyBreedStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverDailyBreedStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverDailyBreedStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverDailyBreedStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverDailyBreedStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverDailyBreedStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N120. Remaining leftover hash on Hunt / theory stays.
        // Play / Fog / Join-from-spectate remint the bar when
        // the exclusive kind changes. These stays must not be
        // taught away: Hunt leftover hash stay — same maze
        // (play() remints #session= only when it seats);
        // theory leftover hash stay — same maze; Hunt through
        // Play still keeps tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62).
        assertLeftoverHashStay(html, "async function startTour", "function sameCell");
        assertLeftoverHashStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverHashStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverHashStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverHashStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverHashStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N121. Remaining leftover harden stays. adoptMaze /
        // leaveMaze / Bring to life already enable or disable
        // #harden. Living under fog is honest (N19). These
        // stays must not be taught away: Hunt / Play / Fog /
        // theory / Join leftover harden stay — same maze
        // still alive; leftover #harden checked stay — you
        // asked for seal; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverHardenStay(html, "async function startTour", "function sameCell");
        assertLeftoverHardenStay(html, "async function play()", "async function join()");
        assertLeftoverHardenStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverHardenStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverHardenStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverHardenStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverHardenStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverHardenStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverHardenStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N122. Remaining leftover picker stays. loadAlgorithms
        // / #generator= hydrate already remint those selects.
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover solver / leftover
        // lensH / leftover rival stay — the picker you
        // asked for; leftover #lbGen stay — the filter you
        // asked for; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverPickerStay(html, "async function startTour", "function sameCell");
        assertLeftoverPickerStay(html, "async function play()", "async function join()");
        assertLeftoverPickerStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPickerStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPickerStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPickerStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPickerStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPickerStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPickerStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N123. applyHotspotsFromMaze reminted spot count and
        // left leftover #hotspotCost from the previous recipe,
        // so Daily / Generate / #maze= of a no-spot maze still
        // billed leftover cost when spots were later asked for.
        // Remint cost from the snapshot (catalog 25 when the
        // maze has none). applyRecipeToForm remints cost even
        // when the permalink omits cost=. Hunt / Play / Fog /
        // theory / Join leftover #hotspotCost stay — same maze
        // recipe (N114). startFog still must not null tour
        // (N17).
        String n123Hs = html.substring(html.indexOf("function applyHotspotsFromMaze"),
                html.indexOf("function applyBraidFromMaze"));
        int n123Count = n123Hs.indexOf("$(\"hotspots\").value = hs.length");
        int n123Cost = n123Hs.indexOf("$(\"hotspotCost\").value = hs.length ? hs[0].cost : 25");
        assertThat(n123Count).isGreaterThanOrEqualTo(0);
        assertThat(n123Cost).isGreaterThan(n123Count);
        assertThat(n123Hs).doesNotContain("if (hs.length && $(\"hotspotCost\")");
        String n123Recipe = html.substring(html.indexOf("function applyRecipeToForm"),
                html.indexOf("async function rebuildFromRecipe"));
        assertThat(n123Recipe).contains("$(\"hotspotCost\").value = h.cost || 25");
        assertThat(n123Recipe).doesNotContain("if ($(\"hotspotCost\") && h.cost)");
        // N124. Remaining leftover sidebar picker stays.
        // loadLabMetrics remints #labMetric. applyBraidFromMaze
        // remints #tourBraid. These stays must not be taught
        // away: Hunt / Play / Fog / theory / Join leftover
        // labMetric stay — the metric you asked for;
        // leftover #tourBraid stay — the sample braid you
        // asked for; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverSidebarStay(html, "async function startTour", "function sameCell");
        assertLeftoverSidebarStay(html, "async function play()", "async function join()");
        assertLeftoverSidebarStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverSidebarStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverSidebarStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverSidebarStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverSidebarStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverSidebarStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverSidebarStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N125. Remaining leftover sessionStart stays. Play
        // remints leftover clock when it seats. Join-from-
        // spectate remints leftover clock. These stays must
        // not be taught away: Hunt leftover sessionStart
        // stay — current walk; Fog leftover sessionStart
        // stay — unused leftover clock (declareWin needs
        // session + ghost); theory leftover sessionStart
        // stay — leftover clock unused; Hunt through Play
        // still keeps tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62).
        assertLeftoverClockStay(html, "async function startTour", "function sameCell");
        assertLeftoverClockStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverClockStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverClockStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverClockStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverClockStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverClockStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N126. Remaining leftover credential stays. login
        // remints leftover #pass. logout remints leftover
        // #user. These stays must not be taught away: Hunt /
        // Play / Fog / theory / Join leftover #user /
        // leftover #pass stay — the name you typed; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86).
        assertLeftoverCredentialStay(html, "async function startTour", "function sameCell");
        assertLeftoverCredentialStay(html, "async function play()", "async function join()");
        assertLeftoverCredentialStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverCredentialStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverCredentialStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverCredentialStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverCredentialStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverCredentialStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverCredentialStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N127. Remaining leftover picker caption stays.
        // updateInfo remints leftover #genInfo / leftover
        // #solInfo when leftover generator / leftover solver
        // changes. These stays must not be taught away: Hunt
        // / Play / Fog / theory / Join leftover #genInfo /
        // leftover #solInfo stay — the picker caption you
        // asked for; Hunt through Play and Join-from-
        // spectate still keep tour; Fog still keeps tour
        // (N17); leftover Solve path stays as a theory
        // route hint (N62); Join leftover ghost stays (N86).
        assertLeftoverInfoStay(html, "async function startTour", "function sameCell");
        assertLeftoverInfoStay(html, "async function play()", "async function join()");
        assertLeftoverInfoStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverInfoStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverInfoStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverInfoStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverInfoStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverInfoStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverInfoStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N128. Remaining leftover campaign box stays.
        // leaveCampaign / renderCampaign remint leftover
        // #campaignBox. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover
        // #campaignBox stay — the ladder you asked for;
        // leftover campaign stay already forbids leaveCampaign
        // (N112); Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62); Join leftover ghost stays (N86).
        assertLeftoverCampaignBoxStay(html, "async function startTour", "function sameCell");
        assertLeftoverCampaignBoxStay(html, "async function play()", "async function join()");
        assertLeftoverCampaignBoxStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverCampaignBoxStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverCampaignBoxStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverCampaignBoxStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverCampaignBoxStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverCampaignBoxStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverCampaignBoxStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N129. Remaining leftover search / path progress stays.
        // Hunt remints leftover searchProgress / leftover
        // pathProgress. Theory remints leftover search wash
        // (N87). Play / Fog / Join remint leftover path /
        // leftover expansions and leave leftover progress, so
        // leftover clock is unused (draw needs leftover path
        // / leftover expansions). These stays must not be
        // taught away: Play / Fog / Join leftover
        // searchProgress / leftover pathProgress stay —
        // unused leftover clock; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86).
        assertLeftoverProgressStay(html, "async function play()", "async function join()");
        assertLeftoverProgressStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverProgressStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N130. Remaining leftover cadence stays. startLivePolling
        // remints leftover liveTickMs. startTrafficPolling remints
        // leftover trafficTickMs. leftover live stay already
        // forbids reminting leftover polls (N113). These stays
        // must not be taught away: Hunt / Play / Fog / theory /
        // Join leftover liveTickMs / leftover trafficTickMs stay
        // — leftover cadence you asked for; reconnect re-arms
        // with leftover cadence when leftover #live is disabled;
        // Hunt through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve path
        // stays as a theory route hint (N62); Join leftover
        // ghost stays (N86).
        assertLeftoverCadenceStay(html, "async function startTour", "function sameCell");
        assertLeftoverCadenceStay(html, "async function play()", "async function join()");
        assertLeftoverCadenceStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverCadenceStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverCadenceStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverCadenceStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverCadenceStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverCadenceStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverCadenceStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N131. Remaining leftover cleared stays. loadCampaign /
        // leaveCampaign remint leftover cleared. leftover
        // campaign stay already forbids leaveCampaign (N112).
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover cleared stay — leftover
        // stages you cleared; leftover campaign stay already
        // forbids dropping leftover ladder (N112); leftover
        // campaign box stay already forbids reminting leftover
        // #campaignBox (N128); Hunt through Play and
        // Join-from-spectate still keep tour; Fog still keeps
        // tour (N17); leftover Solve path stays as a theory
        // route hint (N62); Join leftover ghost stays (N86).
        assertLeftoverClearedStay(html, "async function startTour", "function sameCell");
        assertLeftoverClearedStay(html, "async function play()", "async function join()");
        assertLeftoverClearedStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverClearedStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverClearedStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverClearedStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverClearedStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverClearedStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverClearedStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N132. Remaining leftover Play / Fog button stays.
        // adoptMaze / leaveMaze remint leftover #play /
        // leftover #fog. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover #play
        // stay — same maze still playable; leftover #fog stay
        // — same maze still fogable; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still keeps
        // tour (N17); leftover Solve path stays as a theory
        // route hint (N62); Join leftover ghost stays (N86).
        assertLeftoverWalkButtonStay(html, "async function startTour", "function sameCell");
        assertLeftoverWalkButtonStay(html, "async function play()", "async function join()");
        assertLeftoverWalkButtonStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverWalkButtonStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverWalkButtonStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverWalkButtonStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverWalkButtonStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverWalkButtonStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverWalkButtonStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N133. Remaining leftover algos stays. loadAlgorithms
        // remints leftover algos. leftover picker stay already
        // forbids rewriting leftover solver (N122). leftover
        // picker caption stay already forbids reminting leftover
        // #genInfo / leftover #solInfo (N127). These stays must
        // not be taught away: Hunt / Play / Fog / theory / Join
        // leftover algos stay — leftover catalog you loaded;
        // Hunt through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve path
        // stays as a theory route hint (N62); Join leftover
        // ghost stays (N86).
        assertLeftoverAlgosStay(html, "async function startTour", "function sameCell");
        assertLeftoverAlgosStay(html, "async function play()", "async function join()");
        assertLeftoverAlgosStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverAlgosStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverAlgosStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverAlgosStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverAlgosStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverAlgosStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverAlgosStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N134. Remaining leftover STOMP stays. Play remints
        // leftover session frames when it seats. Fog remints
        // leftover session frames. Join-from-spectate remints
        // leftover session frames. These stays must not be
        // taught away: Hunt leftover STOMP stay — leftover
        // frames still name this maze; theory leftover STOMP
        // stay — leftover frames still name this maze; Hunt
        // through Play still keeps tour; Fog still keeps
        // tour (N17); leftover Solve path stays as a theory
        // route hint (N62).
        assertLeftoverStompStay(html, "async function startTour", "function sameCell");
        assertLeftoverStompStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverStompStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverStompStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverStompStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverStompStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N135. Remaining leftover lbQuery stays. refreshLeaderboard
        // remints leftover lbQuery. leftover walk chrome stay
        // already forbids reminting leftover board (N111). These
        // stays must not be taught away: Hunt / Play / Fog /
        // theory / Join leftover lbQuery stay — leftover last
        // /leaderboard path still names this maze; Hunt through
        // Play and Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86).
        assertLeftoverLbQueryStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbQueryStay(html, "async function play()", "async function join()");
        assertLeftoverLbQueryStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbQueryStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbQueryStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbQueryStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbQueryStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbQueryStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbQueryStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N136. Remaining leftover #asciiOut stays. Generate /
        // Play / Hunt / theory / Join / Fog already hide leftover
        // dump (N68–N74). Living tick remints leftover dump only
        // when the pre is shown. These stays must not be taught
        // away: Hunt / Play / Fog / theory / Join leftover
        // #asciiOut stay — leftover dump stays hidden; Fog
        // leftover dump text unused (hidden); Hunt through Play
        // and Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86).
        assertLeftoverAsciiStay(html, "async function startTour", "function sameCell");
        assertLeftoverAsciiStay(html, "async function play()", "async function join()");
        assertLeftoverAsciiStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverAsciiStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverAsciiStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverAsciiStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverAsciiStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverAsciiStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverAsciiStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N137. Remaining leftover #pngExport stays. leftover
        // lab / tournament / PNG stay already forbids reminting
        // leftover #pngExport in those writers (N116). adoptMaze
        // / leaveMaze remint leftover snapshot. Click remints
        // leftover href from the canvas. These stays must not be
        // taught away: Hunt / Play / Fog / theory / Join leftover
        // #pngExport stay — leftover snapshot stays visible
        // (same maze canvas); Fog leftover snapshot visibility
        // unused (click remints the fog walk); Hunt through Play
        // and Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86).
        assertLeftoverPngExportStay(html, "async function startTour", "function sameCell");
        assertLeftoverPngExportStay(html, "async function play()", "async function join()");
        assertLeftoverPngExportStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPngExportStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPngExportStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPngExportStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPngExportStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPngExportStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPngExportStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N138. Remaining leftover expansions remint stays.
        // Hunt remints leftover expansions after the maze-id
        // discard. Play / Fog / Join remint leftover path /
        // leftover expansions. Theory remints leftover search
        // wash (N87). Distinct from leftover progress clock
        // (N129). These remints must not be taught away: Hunt
        // / Play / Fog / theory / Join leftover expansions
        // remint stay — leftover wash emptied (draw needs
        // leftover expansions); Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86).
        assertLeftoverExpansionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverExpansionsStay(html, "async function play()", "async function join()");
        assertLeftoverExpansionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverExpansionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverExpansionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverExpansionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverExpansionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverExpansionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverExpansionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N139. Remaining leftover sanctuaries remint stays.
        // Hunt / Play / Fog / Join remint leftover rings
        // after the maze-id discard. Theory remints leftover
        // sibling rings (N63). placeSanctuaries remints
        // leftover rings after leftover sibling null. These
        // remints must not be taught away. Must not null
        // tour (N17).
        assertLeftoverSanctuariesStay(html, "async function startTour", "function sameCell");
        assertLeftoverSanctuariesStay(html, "async function play()", "async function join()");
        assertLeftoverSanctuariesStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverSanctuariesStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverSanctuariesStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverSanctuariesStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverSanctuariesStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverSanctuariesStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverSanctuariesStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N140. Remaining leftover plugins describe stays.
        // refreshPlugins remints leftover describe. leftover
        // plugin stay already forbids reminting leftover
        // roster (N115). These stays must not be taught
        // away: Hunt / Play / Fog / theory / Join leftover
        // plugins describe stay — leftover description you
        // already loaded; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverPluginsDescribeStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginsDescribeStay(html, "async function play()", "async function join()");
        assertLeftoverPluginsDescribeStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginsDescribeStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginsDescribeStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginsDescribeStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginsDescribeStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginsDescribeStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginsDescribeStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N141. Remaining leftover walk chrome remint stays.
        // Play remints leftover trails / leftover won after
        // the maze-id discard. Fog remints leftover trails /
        // leftover won (N109 / N110). Join remints leftover
        // joiner crumbs after the maze-id discard. leftover
        // walk chrome stay already forbids reminting leftover
        // trails / leftover won during Hunt / theory (N111).
        // These remints must not be taught away. Must not
        // null tour (N17).
        assertLeftoverWalkChromeRemintStay(html, "async function play()", "async function join()");
        assertLeftoverWalkChromeRemintStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverWalkChromeRemintStay(html, "async function join()", "async function move(");
        assertLeftoverWalkChromeStay(html, "async function startTour", "function sameCell");
        assertLeftoverWalkChromeStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverWalkChromeStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverWalkChromeStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverWalkChromeStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverWalkChromeStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N142. Remaining leftover #lb title stays.
        // refreshLeaderboard remints leftover #lbTitle.
        // leftover walk chrome stay already forbids reminting
        // leftover board (N111). leftover lbQuery stay
        // already forbids reminting leftover path (N135).
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover #lb title stay —
        // leftover heading still names this maze's board;
        // Hunt through Play and Join-from-spectate still
        // keep tour; Fog still keeps tour (N17); leftover
        // Solve path stays as a theory route hint (N62);
        // Join leftover ghost stays (N86). Must not null
        // tour (N17).
        assertLeftoverLbTitleStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbTitleStay(html, "async function play()", "async function join()");
        assertLeftoverLbTitleStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbTitleStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbTitleStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbTitleStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbTitleStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbTitleStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbTitleStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N143. Remaining leftover #lb rows stay.
        // refreshLeaderboard remints leftover #lb rows.
        // leftover walk chrome stay already forbids reminting
        // leftover board (N111). leftover #lb title stay
        // already forbids reminting leftover heading (N142).
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover #lb rows stay —
        // leftover scores still name this maze's board; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour
        // (N17).
        assertLeftoverLbRowsStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbRowsStay(html, "async function play()", "async function join()");
        assertLeftoverLbRowsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbRowsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbRowsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbRowsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbRowsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbRowsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbRowsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N144. Remaining leftover #lbGen disabled stays.
        // refreshLeaderboard remints leftover #lbGen
        // disabled. leftover picker stay already forbids
        // reminting leftover #lbGen value (N122). leftover
        // walk chrome stay already forbids reminting leftover
        // board (N111). These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover #lbGen
        // disabled stay — leftover filter still enabled or
        // still locked to this maze; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86). Must not null tour (N17).
        assertLeftoverLbGenDisabledStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbGenDisabledStay(html, "async function play()", "async function join()");
        assertLeftoverLbGenDisabledStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbGenDisabledStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbGenDisabledStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbGenDisabledStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbGenDisabledStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbGenDisabledStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbGenDisabledStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N145. Remaining leftover #lbGen options stay.
        // loadAlgorithms remints leftover #lbGen options.
        // leftover picker stay already forbids reminting
        // leftover #lbGen value (N122). leftover algos stay
        // already forbids reminting leftover catalog (N133).
        // leftover #lbGen disabled stay already forbids
        // reminting leftover lock (N144). These stays must
        // not be taught away: Hunt / Play / Fog / theory /
        // Join leftover #lbGen options stay — leftover
        // filter roster you loaded; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86). Must not null tour (N17).
        assertLeftoverLbGenOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbGenOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverLbGenOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbGenOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbGenOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbGenOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbGenOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbGenOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbGenOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N146. Remaining leftover #rival options stay.
        // loadAlgorithms remints leftover #rival options.
        // leftover picker stay already forbids reminting
        // leftover rival value (N122). leftover algos stay
        // already forbids reminting leftover catalog (N133).
        // leftover #lbGen options stay already forbids
        // reminting leftover filter roster (N145). These
        // stays must not be taught away: Hunt / Play / Fog /
        // theory / Join leftover #rival options stay —
        // leftover arena roster you loaded; Hunt through
        // Play and Join-from-spectate still keep tour; Fog
        // still keeps tour (N17); leftover Solve path stays
        // as a theory route hint (N62); Join leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverRivalOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverRivalOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverRivalOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverRivalOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverRivalOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverRivalOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverRivalOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverRivalOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverRivalOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N147. Remaining leftover #solver options stay.
        // loadAlgorithms remints leftover #solver options.
        // leftover picker stay already forbids reminting
        // leftover solver value (N122). leftover algos stay
        // already forbids reminting leftover catalog (N133).
        // leftover #rival options stay already forbids
        // reminting leftover arena roster (N146). These
        // stays must not be taught away: Hunt / Play / Fog /
        // theory / Join leftover #solver options stay —
        // leftover solver roster you loaded; Hunt through
        // Play and Join-from-spectate still keep tour; Fog
        // still keeps tour (N17); leftover Solve path stays
        // as a theory route hint (N62); Join leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverSolverOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverSolverOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverSolverOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverSolverOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverSolverOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverSolverOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverSolverOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverSolverOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverSolverOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N148. Remaining leftover #generator options stay.
        // loadAlgorithms remints leftover #generator options.
        // leftover form stay already forbids reminting leftover
        // generator value (N114). leftover algos stay already
        // forbids reminting leftover catalog (N133). leftover
        // #solver options stay already forbids reminting leftover
        // solver roster (N147). These stays must not be taught
        // away: Hunt / Play / Fog / theory / Join leftover
        // #generator options stay — leftover generator roster
        // you loaded; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17); leftover
        // Solve path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour (N17).
        assertLeftoverGeneratorOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverGeneratorOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverGeneratorOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverGeneratorOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverGeneratorOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverGeneratorOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverGeneratorOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverGeneratorOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverGeneratorOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N149. Remaining leftover #lensH options stay.
        // leftover #lensH options ship in the markup.
        // leftover picker stay already forbids reminting
        // leftover #lensH value (N122). leftover #generator
        // options stay already forbids reminting leftover
        // generator roster (N148). These stays must not be
        // taught away: Hunt / Play / Fog / theory / Join
        // leftover #lensH options stay — leftover heuristic
        // roster you loaded; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86). Must not null tour (N17).
        assertLeftoverLensHOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverLensHOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverLensHOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLensHOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLensHOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLensHOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLensHOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLensHOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLensHOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N150. Remaining leftover #labMetric options stay.
        // loadLabMetrics remints leftover #labMetric options.
        // leftover sidebar picker stay already forbids
        // reminting leftover #labMetric value (N124). leftover
        // #lensH options stay already forbids reminting leftover
        // heuristic roster (N149). These stays must not be
        // taught away: Hunt / Play / Fog / theory / Join
        // leftover #labMetric options stay — leftover metric
        // roster you loaded; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86). Must not null tour (N17).
        assertLeftoverLabMetricOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverLabMetricOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverLabMetricOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLabMetricOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLabMetricOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLabMetricOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLabMetricOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLabMetricOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLabMetricOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N151. Remaining leftover #tourBraid options stay.
        // leftover #tourBraid options ship in the markup.
        // syncBraid / applyBraidFromMaze remint leftover
        // sample braid options on braid change or maze adopt.
        // leftover sidebar picker stay already forbids
        // reminting leftover #tourBraid value (N124). leftover
        // #labMetric options stay already forbids reminting
        // leftover metric roster (N150). These stays must not
        // be taught away: Hunt / Play / Fog / theory / Join
        // leftover #tourBraid options stay — leftover sample
        // braid roster you loaded; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost stays
        // (N86). Must not null tour (N17).
        assertLeftoverTourBraidOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverTourBraidOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverTourBraidOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverTourBraidOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverTourBraidOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverTourBraidOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverTourBraidOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverTourBraidOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverTourBraidOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N152. Remaining leftover #braid options stay.
        // leftover #braid options ship in the markup.
        // applyBraidFromMaze / applyRecipeToForm /
        // runTournament remint leftover braid options on
        // maze adopt or tournament. leftover form stay
        // already forbids reminting leftover braid value
        // (N114). leftover #tourBraid options stay already
        // forbids reminting leftover sample braid roster
        // (N151). These stays must not be taught away: Hunt /
        // Play / Fog / theory / Join leftover #braid options
        // stay — leftover braid roster you loaded; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour
        // (N17).
        assertLeftoverBraidOptionsStay(html, "async function startTour", "function sameCell");
        assertLeftoverBraidOptionsStay(html, "async function play()", "async function join()");
        assertLeftoverBraidOptionsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverBraidOptionsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverBraidOptionsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverBraidOptionsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverBraidOptionsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverBraidOptionsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverBraidOptionsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N153. Remaining leftover plugin version stays.
        // refreshPlugins remints leftover version. leftover
        // plugin stay already forbids reminting leftover
        // roster (N115). leftover plugins describe stay
        // already forbids reminting leftover describe (N140).
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover plugin version stay —
        // leftover version you already loaded; Hunt through
        // Play and Join-from-spectate still keep tour; Fog
        // still keeps tour (N17); leftover Solve path stays
        // as a theory route hint (N62); Join leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverPluginVersionStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginVersionStay(html, "async function play()", "async function join()");
        assertLeftoverPluginVersionStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginVersionStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginVersionStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginVersionStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginVersionStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginVersionStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginVersionStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N154. Remaining leftover plugin state stays.
        // refreshPlugins remints leftover plugin state.
        // leftover plugin stay already forbids reminting
        // leftover roster (N115). leftover plugin version
        // stay already forbids reminting leftover version
        // (N153). These stays must not be taught away: Hunt /
        // Play / Fog / theory / Join leftover plugin state
        // stay — leftover boot state you already loaded;
        // Hunt through Play and Join-from-spectate still
        // keep tour; Fog still keeps tour (N17); leftover
        // Solve path stays as a theory route hint (N62);
        // Join leftover ghost stays (N86). Must not null
        // tour (N17).
        assertLeftoverPluginStateStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginStateStay(html, "async function play()", "async function join()");
        assertLeftoverPluginStateStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginStateStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginStateStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginStateStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginStateStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginStateStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginStateStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N155. Remaining leftover plugin error stays.
        // refreshPlugins remints leftover plugin error.
        // leftover plugin stay already forbids reminting
        // leftover roster (N115). leftover plugin state stay
        // already forbids reminting leftover boot state
        // (N154). These stays must not be taught away: Hunt /
        // Play / Fog / theory / Join leftover plugin error
        // stay — leftover failure you already loaded; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour
        // (N17).
        assertLeftoverPluginErrorStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginErrorStay(html, "async function play()", "async function join()");
        assertLeftoverPluginErrorStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginErrorStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginErrorStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginErrorStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginErrorStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginErrorStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginErrorStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N156. Remaining leftover plugin displayName stays.
        // refreshPlugins remints leftover plugin displayName.
        // leftover plugin stay already forbids reminting
        // leftover roster (N115). leftover plugin error stay
        // already forbids reminting leftover failure (N155).
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover plugin displayName
        // stay — leftover name you already loaded; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour
        // (N17).
        assertLeftoverPluginDisplayNameStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginDisplayNameStay(html, "async function play()", "async function join()");
        assertLeftoverPluginDisplayNameStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginDisplayNameStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginDisplayNameStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginDisplayNameStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginDisplayNameStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginDisplayNameStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginDisplayNameStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N157. Remaining leftover plugin id stays.
        // refreshPlugins remints leftover plugin id.
        // leftover plugin stay already forbids reminting
        // leftover roster (N115). leftover plugin
        // displayName stay already forbids reminting leftover
        // name (N156). These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover plugin
        // id stay — leftover id you already loaded; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour
        // (N17).
        assertLeftoverPluginIdStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginIdStay(html, "async function play()", "async function join()");
        assertLeftoverPluginIdStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginIdStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginIdStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginIdStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginIdStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginIdStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginIdStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N158. Remaining leftover plugin manifest stays.
        // refreshPlugins remints leftover plugin manifest.
        // leftover plugin stay already forbids reminting
        // leftover roster (N115). leftover plugin id stay
        // already forbids reminting leftover id (N157).
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover plugin manifest stay
        // — leftover manifest you already loaded; Hunt
        // through Play and Join-from-spectate still keep
        // tour; Fog still keeps tour (N17); leftover Solve
        // path stays as a theory route hint (N62); Join
        // leftover ghost stays (N86). Must not null tour
        // (N17).
        assertLeftoverPluginManifestStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginManifestStay(html, "async function play()", "async function join()");
        assertLeftoverPluginManifestStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginManifestStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginManifestStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginManifestStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginManifestStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginManifestStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginManifestStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N159. Remaining leftover plugin empty copy stays.
        // refreshPlugins remints leftover plugin empty copy.
        // leftover plugin stay already forbids reminting
        // leftover roster (N115). leftover plugin manifest
        // stay already forbids reminting leftover manifest
        // (N158). These stays must not be taught away: Hunt /
        // Play / Fog / theory / Join leftover plugin empty
        // copy stay — leftover empty roster you already
        // loaded; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62); Join leftover ghost stays (N86). Must not
        // null tour (N17).
        assertLeftoverPluginEmptyCopyStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginEmptyCopyStay(html, "async function play()", "async function join()");
        assertLeftoverPluginEmptyCopyStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginEmptyCopyStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginEmptyCopyStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginEmptyCopyStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginEmptyCopyStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginEmptyCopyStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginEmptyCopyStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N160. Remaining leftover plugin unavailable copy
        // stays. refreshPlugins remints leftover plugin
        // unavailable copy. leftover plugin stay already
        // forbids reminting leftover roster (N115). leftover
        // plugin empty copy stay already forbids reminting
        // leftover empty roster (N159). These stays must not
        // be taught away: Hunt / Play / Fog / theory / Join
        // leftover plugin unavailable copy stay — leftover
        // unavailable roster you already loaded; Hunt through
        // Play and Join-from-spectate still keep tour; Fog
        // still keeps tour (N17); leftover Solve path stays
        // as a theory route hint (N62); Join leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverPluginUnavailableCopyStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginUnavailableCopyStay(html, "async function play()", "async function join()");
        assertLeftoverPluginUnavailableCopyStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginUnavailableCopyStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginUnavailableCopyStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginUnavailableCopyStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginUnavailableCopyStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginUnavailableCopyStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginUnavailableCopyStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N161–N164. Remaining leftover leftover-copy family
        // stays. leftover plugin stay already forbids
        // reminting leftover roster (N115). leftover #lb
        // rows stay already forbids reminting leftover
        // board rows (N143). leftover plugin unavailable
        // copy stay already forbids reminting leftover
        // unavailable roster (N160). These stays must not
        // be taught away: Hunt / Play / Fog / theory / Join
        // leftover plugin loading copy stay — leftover
        // loading roster you already loaded; leftover #lb
        // loading copy stay — leftover board loading you
        // already loaded; leftover /plugins fetch stay —
        // leftover catalog fetch you already loaded;
        // leftover plugin list.map stay — leftover roster
        // rows you already loaded; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover Solve path stays as a
        // theory route hint (N62); Join leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverPluginLoadingCopyStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginLoadingCopyStay(html, "async function play()", "async function join()");
        assertLeftoverPluginLoadingCopyStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginLoadingCopyStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginLoadingCopyStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginLoadingCopyStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginLoadingCopyStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginLoadingCopyStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginLoadingCopyStay(html, "async function join()", "async function move(");
        assertLeftoverLbLoadingCopyStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbLoadingCopyStay(html, "async function play()", "async function join()");
        assertLeftoverLbLoadingCopyStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbLoadingCopyStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbLoadingCopyStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbLoadingCopyStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbLoadingCopyStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbLoadingCopyStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbLoadingCopyStay(html, "async function join()", "async function move(");
        assertLeftoverPluginsFetchStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginsFetchStay(html, "async function play()", "async function join()");
        assertLeftoverPluginsFetchStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginsFetchStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginsFetchStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginsFetchStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginsFetchStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginsFetchStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginsFetchStay(html, "async function join()", "async function move(");
        assertLeftoverPluginListMapStay(html, "async function startTour", "function sameCell");
        assertLeftoverPluginListMapStay(html, "async function play()", "async function join()");
        assertLeftoverPluginListMapStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPluginListMapStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPluginListMapStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPluginListMapStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPluginListMapStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPluginListMapStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPluginListMapStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N165–N168. Remaining leftover leftover recipe
        // family stays. leftover form stay already forbids
        // reminting leftover recipe (N114). leftover
        // #hotspotCost stay already N123. These stays must
        // not be taught away: Hunt / Play / Fog / theory /
        // Join leftover #rows stay — leftover height you
        // already asked for; leftover #cols stay — leftover
        // width you already asked for; leftover #seed stay
        // — leftover seed you already asked for; leftover
        // #hotspots stay — leftover spots you already asked
        // for; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17);
        // leftover Solve path stays as a theory route hint
        // (N62); Join leftover ghost stays (N86). Must not
        // null tour (N17).
        assertLeftoverRowsStay(html, "async function startTour", "function sameCell");
        assertLeftoverRowsStay(html, "async function play()", "async function join()");
        assertLeftoverRowsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverRowsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverRowsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverRowsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverRowsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverRowsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverRowsStay(html, "async function join()", "async function move(");
        assertLeftoverColsStay(html, "async function startTour", "function sameCell");
        assertLeftoverColsStay(html, "async function play()", "async function join()");
        assertLeftoverColsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverColsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverColsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverColsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverColsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverColsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverColsStay(html, "async function join()", "async function move(");
        assertLeftoverSeedStay(html, "async function startTour", "function sameCell");
        assertLeftoverSeedStay(html, "async function play()", "async function join()");
        assertLeftoverSeedStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverSeedStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverSeedStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverSeedStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverSeedStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverSeedStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverSeedStay(html, "async function join()", "async function move(");
        assertLeftoverHotspotsStay(html, "async function startTour", "function sameCell");
        assertLeftoverHotspotsStay(html, "async function play()", "async function join()");
        assertLeftoverHotspotsStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverHotspotsStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverHotspotsStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverHotspotsStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverHotspotsStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverHotspotsStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverHotspotsStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N169–N170. Remaining leftover leftover form leftover
        // picker-value family stays. leftover form stay already
        // forbids reminting leftover leftover recipe (N114).
        // leftover leftover picker stay already forbids reminting
        // leftover leftover solver / leftover leftover lensH /
        // leftover leftover rival / leftover leftover #lbGen
        // (N122). leftover leftover #hotspots stay already N168.
        // These stays must not be taught away: Hunt / Play /
        // Fog / theory / Join leftover leftover #generator stay
        // — leftover leftover generator you already asked for;
        // leftover leftover #braid stay — leftover leftover
        // braid you already asked for; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still keeps
        // tour (N17); leftover leftover Solve path stays as a
        // theory route hint (N62); Join leftover leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverGeneratorStay(html, "async function startTour", "function sameCell");
        assertLeftoverGeneratorStay(html, "async function play()", "async function join()");
        assertLeftoverGeneratorStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverGeneratorStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverGeneratorStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverGeneratorStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverGeneratorStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverGeneratorStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverGeneratorStay(html, "async function join()", "async function move(");
        assertLeftoverBraidStay(html, "async function startTour", "function sameCell");
        assertLeftoverBraidStay(html, "async function play()", "async function join()");
        assertLeftoverBraidStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverBraidStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverBraidStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverBraidStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverBraidStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverBraidStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverBraidStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N171–N173. Remaining leftover leftover picker-value
        // family stays. leftover leftover picker stay already
        // forbids reminting leftover leftover solver / leftover
        // leftover lensH / leftover leftover rival / leftover
        // leftover #lbGen (N122). leftover leftover #braid stay
        // already N170. leftover leftover #rival options stay
        // already N146. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover leftover
        // solver stay — leftover leftover solver you already
        // asked for; leftover leftover #lensH stay — leftover
        // leftover heuristic you already asked for; leftover
        // leftover rival stay — leftover leftover rival you
        // already asked for; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still keeps
        // tour (N17); leftover leftover Solve path stays as a
        // theory route hint (N62); Join leftover leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverSolverStay(html, "async function startTour", "function sameCell");
        assertLeftoverSolverStay(html, "async function play()", "async function join()");
        assertLeftoverSolverStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverSolverStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverSolverStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverSolverStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverSolverStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverSolverStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverSolverStay(html, "async function join()", "async function move(");
        assertLeftoverLensHStay(html, "async function startTour", "function sameCell");
        assertLeftoverLensHStay(html, "async function play()", "async function join()");
        assertLeftoverLensHStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLensHStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLensHStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLensHStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLensHStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLensHStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLensHStay(html, "async function join()", "async function move(");
        assertLeftoverRivalStay(html, "async function startTour", "function sameCell");
        assertLeftoverRivalStay(html, "async function play()", "async function join()");
        assertLeftoverRivalStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverRivalStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverRivalStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverRivalStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverRivalStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverRivalStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverRivalStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N174–N176. Remaining leftover leftover #lbGen value
        // and leftover leftover sidebar leftover picker-value
        // family stays. leftover leftover picker stay already
        // forbids reminting leftover leftover #lbGen (N122).
        // leftover leftover sidebar stay already forbids
        // reminting leftover leftover #labMetric / leftover
        // leftover #tourBraid (N124). leftover leftover rival
        // stay already N173. leftover leftover #lbGen disabled
        // stay already N144. These stays must not be taught
        // away: Hunt / Play / Fog / theory / Join leftover
        // leftover #lbGen stay — leftover leftover filter you
        // already asked for; leftover leftover #labMetric stay
        // — leftover leftover metric you already asked for;
        // leftover leftover #tourBraid stay — leftover leftover
        // tour braid you already asked for; Hunt through Play
        // and Join-from-spectate still keep tour; Fog still
        // keeps tour (N17); leftover leftover Solve path stays
        // as a theory route hint (N62); Join leftover leftover
        // ghost stays (N86). Must not null tour (N17).
        assertLeftoverLbGenStay(html, "async function startTour", "function sameCell");
        assertLeftoverLbGenStay(html, "async function play()", "async function join()");
        assertLeftoverLbGenStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLbGenStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLbGenStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLbGenStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLbGenStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLbGenStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLbGenStay(html, "async function join()", "async function move(");
        assertLeftoverLabMetricStay(html, "async function startTour", "function sameCell");
        assertLeftoverLabMetricStay(html, "async function play()", "async function join()");
        assertLeftoverLabMetricStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLabMetricStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLabMetricStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLabMetricStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLabMetricStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLabMetricStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLabMetricStay(html, "async function join()", "async function move(");
        assertLeftoverTourBraidStay(html, "async function startTour", "function sameCell");
        assertLeftoverTourBraidStay(html, "async function play()", "async function join()");
        assertLeftoverTourBraidStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverTourBraidStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverTourBraidStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverTourBraidStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverTourBraidStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverTourBraidStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverTourBraidStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N177–N178. Remaining leftover leftover #hotspotCost
        // and leftover leftover #player family stays. leftover
        // leftover form stay already forbids reminting leftover
        // leftover #hotspotCost (N114 / N123). leftover leftover
        // catalog stay already forbids reminting leftover leftover
        // #player (N115). leftover leftover #tourBraid stay
        // already N176. These stays must not be taught away:
        // Hunt / Play / Fog / theory / Join leftover leftover
        // #hotspotCost stay — leftover leftover cost you already
        // asked for; leftover leftover #player stay — leftover
        // leftover name you already typed; Hunt through Play and
        // Join-from-spectate still keep tour; Fog still keeps
        // tour (N17); leftover leftover Solve path stays as a
        // theory route hint (N62); Join leftover leftover ghost
        // stays (N86). Must not null tour (N17).
        assertLeftoverHotspotCostStay(html, "async function startTour", "function sameCell");
        assertLeftoverHotspotCostStay(html, "async function play()", "async function join()");
        assertLeftoverHotspotCostStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverHotspotCostStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverHotspotCostStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverHotspotCostStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverHotspotCostStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverHotspotCostStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverHotspotCostStay(html, "async function join()", "async function move(");
        assertLeftoverPlayerStay(html, "async function startTour", "function sameCell");
        assertLeftoverPlayerStay(html, "async function play()", "async function join()");
        assertLeftoverPlayerStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPlayerStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPlayerStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPlayerStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPlayerStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPlayerStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPlayerStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N179–N180. Remaining leftover leftover lab leftover
        // leftover snapshot family stays. leftover leftover lab
        // stay already forbids reminting leftover leftover
        // #labOut / leftover leftover #tourBox (N116). leftover
        // leftover #pngExport stay already N137. leftover leftover
        // #player stay already N178. These stays must not be
        // taught away: Hunt / Play / Fog / theory / Join leftover
        // leftover #labOut stay — leftover leftover curve you
        // already asked for; leftover leftover #tourBox stay —
        // leftover leftover sample you already asked for; Hunt
        // through Play and Join-from-spectate still keep tour;
        // Fog still keeps tour (N17); leftover leftover Solve
        // path stays as a theory route hint (N62); Join leftover
        // leftover ghost stays (N86). Must not null tour (N17).
        assertLeftoverLabOutStay(html, "async function startTour", "function sameCell");
        assertLeftoverLabOutStay(html, "async function play()", "async function join()");
        assertLeftoverLabOutStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLabOutStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLabOutStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLabOutStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLabOutStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLabOutStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLabOutStay(html, "async function join()", "async function move(");
        assertLeftoverTourBoxStay(html, "async function startTour", "function sameCell");
        assertLeftoverTourBoxStay(html, "async function play()", "async function join()");
        assertLeftoverTourBoxStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverTourBoxStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverTourBoxStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverTourBoxStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverTourBoxStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverTourBoxStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverTourBoxStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N181–N183. Remaining leftover leftover #log / leftover
        // leftover #user / leftover leftover #pass family stays.
        // leftover leftover catalog stay already forbids reminting
        // leftover leftover log (N115). leftover leftover auth stay
        // already forbids reminting leftover leftover token (N118).
        // leftover leftover #tourBox stay already N180. These stays
        // must not be taught away: Hunt / Play / Fog / theory /
        // Join leftover leftover #log stay — leftover leftover
        // history you already loaded; leftover leftover #user stay
        // — leftover leftover account you already typed; leftover
        // leftover #pass stay — leftover leftover secret you
        // already typed; Hunt through Play and Join-from-spectate
        // still keep tour; Fog still keeps tour (N17); leftover
        // leftover Solve path stays as a theory route hint (N62);
        // Join leftover leftover ghost stays (N86). Must not null
        // tour (N17).
        assertLeftoverLogStay(html, "async function startTour", "function sameCell");
        assertLeftoverLogStay(html, "async function play()", "async function join()");
        assertLeftoverLogStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverLogStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverLogStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverLogStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverLogStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverLogStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverLogStay(html, "async function join()", "async function move(");
        assertLeftoverUserStay(html, "async function startTour", "function sameCell");
        assertLeftoverUserStay(html, "async function play()", "async function join()");
        assertLeftoverUserStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverUserStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverUserStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverUserStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverUserStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverUserStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverUserStay(html, "async function join()", "async function move(");
        assertLeftoverPassStay(html, "async function startTour", "function sameCell");
        assertLeftoverPassStay(html, "async function play()", "async function join()");
        assertLeftoverPassStay(html, "async function startFog()", "async function fogStep");
        assertLeftoverPassStay(html, "async function analyzeStructure",
                "function paintAnalysisCaption");
        assertLeftoverPassStay(html, "async function identifyGenerator",
                "function paintFingerprintCaption");
        assertLeftoverPassStay(html, "async function distanceHeatMap",
                "function paintFieldCaption");
        assertLeftoverPassStay(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption");
        assertLeftoverPassStay(html, "async function heuristicLens",
                "function paintLensCaption");
        assertLeftoverPassStay(html, "async function join()", "async function move(");
        assertTourStay(html, "async function startFog()", "async function fogStep");
        assertThat(join).doesNotContain("state.ghost = null");
        // N63. Theory writes left sibling theory armed. Leftover
        // heat reminted GET /distance-field after Analyze; leftover
        // cuts reminted GET /analysis after Field. Drop sibling
        // remint overlays after the maze-id discard. Hunt and a
        // leftover Solve path stay. startFog still must not null
        // tour (N17).
        assertLeftoverSiblingTheoryDroppedAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a", "state.field = null");
        assertLeftoverSiblingTheoryDroppedAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f",
                "state.analysis = null");
        assertLeftoverSiblingTheoryDroppedAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f", "state.analysis = null");
        assertLeftoverSiblingTheoryDroppedAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s",
                "state.analysis = null");
        assertLeftoverSiblingTheoryDroppedAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l", "state.analysis = null");
        // N73. Theory writes left leftover ASCII armed. Generate /
        // Fog / Play / Solve / Hardest / Race / Hunt hide
        // #asciiOut (N68–N72). Those theory writes did not, so
        // leftover dump reminted the text/plain maze under the
        // cuts / field / rings / bands / Identify sidebar. Hide
        // it after the maze-id discard. Hunt and a leftover
        // Solve path stay. startFog still must not null tour
        // (N17).
        assertLeftoverAsciiHiddenAfterDiscard(html, "async function analyzeStructure",
                "function paintAnalysisCaption", "state.analysis = a");
        assertLeftoverAsciiHiddenAfterDiscard(html, "async function identifyGenerator",
                "function paintFingerprintCaption", "state.fingerprint = f");
        assertLeftoverAsciiHiddenAfterDiscard(html, "async function distanceHeatMap",
                "function paintFieldCaption", "state.field = f");
        assertLeftoverAsciiHiddenAfterDiscard(html, "async function placeSanctuaries",
                "function paintSanctuariesCaption", "state.sanctuaries = s");
        assertLeftoverAsciiHiddenAfterDiscard(html, "async function heuristicLens",
                "function paintLensCaption", "state.lens = l");
        // N51. leaveSpectate only cleared readOnly. Solve / Analyze
        // after a watch kept the opener's session writable, so
        // arrows POSTed /move on a walk this tab only watched.
        // Drop the leftover seat when we were watching and have
        // not taken one. Join sets the seat first and keeps it.
        // null tour (N17). N52 pins #maze= after the drop when the
        // canvas remains so refresh cannot remint a leftover watch.
        int n51From = html.indexOf("function leaveSpectate");
        int n51To = html.indexOf("function armSpectatorWrites");
        assertThat(n51From).isGreaterThanOrEqualTo(0);
        assertThat(n51To).isGreaterThan(n51From);
        String n51 = html.substring(n51From, n51To);
        int n51Watch = n51.indexOf("state.readOnly");
        int n51Drop = n51.indexOf("state.session = null");
        int n51Pin = n51.indexOf("pinHash()");
        int n51Keep = n51.indexOf("if (state.maze)");
        assertThat(n51Watch).isGreaterThanOrEqualTo(0);
        assertThat(n51Drop).isGreaterThan(n51Watch);
        assertThat(n51).contains("state.seat");
        assertThat(n51).contains("resubscribe()");
        assertThat(n51Keep).isGreaterThan(n51Drop);
        assertThat(n51Pin).isGreaterThan(n51Keep);
        // N56. Spectated hunt stayed after the seat drop. Solve /
        // Fog then Play scored a new walk against leftover
        // waypoints; a living tick asked tourFor with no seat.
        // Drop tour with the leftover seat. startFog still must
        // not null tour (N17).
        int n56Tour = n51.indexOf("state.tour = null");
        assertThat(n56Tour).isGreaterThan(n51Drop);
        assertThat(n56Tour).isLessThan(n51Keep);
        // N105. leaveSpectate dropped the leftover seat (N51)
        // and spectated hunt (N56) but left leftover spectate
        // status, so leftover "spectating session… — read-only"
        // named a watch that is gone under Analyze / Identify /
        // heat / sanctuaries / lens. Rewrite after the seat
        // drop. Join-from-spectate sets the seat first and
        // keeps the session — must return before this write.
        // startFog still must not null tour (N17) except this
        // leave-watch path (N56).
        int n105Flash = n51.indexOf("clearTimeout(statusFlashTimer)");
        int n105Status = n51.indexOf("$(\"status\").textContent");
        int n105Keep = n51.indexOf("if (!wasWatching || state.seat) return");
        assertThat(n105Flash).isGreaterThan(n51Drop);
        assertThat(n105Flash).isLessThan(n51Keep);
        assertThat(n105Status).isGreaterThan(n105Flash);
        assertThat(n105Status).isLessThan(n51Keep);
        assertThat(n105Keep).isGreaterThanOrEqualTo(0);
        assertThat(n105Keep).isLessThan(n105Status);
        // N52. leaveMaze must null the maze before leaveSpectate
        // so that pin cannot rewrite History.
        String n52Leave = html.substring(html.indexOf("function leaveMaze"),
                html.indexOf("async function loadFromHash"));
        assertThat(n52Leave.indexOf("state.maze = null"))
                .isLessThan(n52Leave.indexOf("leaveSpectate()"));
        assertThat(n52Leave).doesNotContain("pinHash()");
        // N54. leaveMaze dropped the canvas and left the adopted
        // recipe in the form. Back onto "" / #generator= then
        // Generate rebuilt the maze the bar no longer names.
        // Restore catalog defaults. Do not pin.
        int n54Rows = n52Leave.indexOf("$(\"rows\").value = 21");
        int n54Seed = n52Leave.indexOf("$(\"seed\").value = \"\"");
        int n54Braid = n52Leave.indexOf("$(\"braid\").value = \"0\"");
        int n54Draw = n52Leave.indexOf("drawEmpty");
        assertThat(n54Rows).isGreaterThanOrEqualTo(0);
        assertThat(n54Rows).isLessThan(n54Draw);
        assertThat(n54Seed).isGreaterThan(n54Rows);
        assertThat(n54Seed).isLessThan(n54Draw);
        assertThat(n54Braid).isGreaterThan(n54Seed);
        assertThat(n54Braid).isLessThan(n54Draw);
        assertThat(n52Leave).contains("syncBraid(\"braid\")");
        assertThat(n52Leave).contains("$(\"cols\").value = 31");
        assertThat(n52Leave).contains("$(\"hotspotCost\").value = 25");
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
        // N55. Open session left Race lanes armed. Leftover arena
        // painted over the walk. Drop race after the session POST
        // discard. Hunt calls play() after installing tour — must
        // not null tour (N50). startFog still must not null tour.
        int n55Race = n32.indexOf("state.race = null", n32Maze);
        int n55Seat = n32.indexOf("state.session =", n32Maze);
        assertThat(n55Race).isGreaterThan(n32Maze);
        assertThat(n55Race).isLessThan(n55Seat);
        assertThat(n32).contains("animGen++");
        assertThat(n32).doesNotContain("state.tour = null");
        // N57. Open session left Compare hover armed. Leftover
        // solver path painted over the walk. Empty #compareBox
        // after the session POST discard when caption is compare.
        // N67 drops path for leftover Solve too. Do not null tour.
        int n57Cap = n32.indexOf("caption === \"compare\"", n32Maze);
        int n57Box = n32.indexOf("$(\"compareBox\").innerHTML = \"\"", n32Maze);
        assertThat(n57Cap).isGreaterThan(n32Maze);
        assertThat(n57Cap).isLessThan(n55Seat);
        assertThat(n57Box).isGreaterThan(n57Cap);
        assertThat(n57Box).isLessThan(n55Seat);
        // N85. Open session gated leftover Hardest on caption
        // (N58). Join already drops leftover gold
        // unconditionally (N77). Play did not, so leftover gold
        // painted under the seat when caption had drifted.
        // Drop hardest after the session POST discard. Do not
        // null tour.
        int n85Drop = n32.indexOf("state.hardest = null", n32Maze);
        assertThat(n85Drop).isGreaterThan(n32Maze);
        assertThat(n85Drop).isLessThan(n55Seat);
        assertThat(n85Drop).isLessThan(n57Cap);
        assertThat(n57Box).isGreaterThan(n85Drop);
        // N66. Open session left sibling theory armed. Leftover
        // cuts reminted GET /analysis under the seat. Drop those
        // after the session POST discard. Theory writes already
        // drop siblings (N63). Hardest / Solve already drop them
        // (N64 / N65). Hunt calls play() after installing tour —
        // must not null tour (N50). startFog still must not null
        // tour (N17).
        int n66An = n32.indexOf("state.analysis = null", n32Maze);
        int n66Field = n32.indexOf("state.field = null", n32Maze);
        assertThat(n66An).isGreaterThan(n32Maze);
        assertThat(n66An).isLessThan(n55Seat);
        assertThat(n66Field).isGreaterThan(n66An);
        assertThat(n66Field).isLessThan(n55Seat);
        assertThat(n32).contains("state.lens = null");
        assertThat(n32).contains("state.fingerprint = null");
        // N67. Open session left a leftover Solve path armed.
        // N57 only dropped Compare hover. Leftover solver route
        // painted over the seat and a living tick reminted POST
        // /solve. Drop path after the session POST discard. Hunt
        // calls play() after installing tour — must not null tour
        // (N50). startFog still must not null tour (N17).
        int n67Path = n32.indexOf("state.path = null", n32Maze);
        assertThat(n67Path).isGreaterThan(n32Maze);
        assertThat(n67Path).isLessThan(n55Seat);
        assertThat(n67Path).isLessThan(n57Cap);
        // N68. Open session left leftover ASCII armed. Generate
        // and Fog hide #asciiOut. Play did not, so leftover dump
        // reminted the text/plain maze under the seat. Hide it
        // after the session POST discard. Hunt calls play() after
        // installing tour — must not null tour (N50). startFog
        // still must not null tour (N17).
        int n68Hide = n32.indexOf("$(\"asciiOut\").hidden = true", n32Maze);
        int n68Clear = n32.indexOf("$(\"asciiOut\").textContent = \"\"", n32Maze);
        assertThat(n68Hide).isGreaterThan(n32Maze);
        assertThat(n68Hide).isLessThan(n55Seat);
        assertThat(n68Clear).isGreaterThan(n68Hide);
        assertThat(n68Clear).isLessThan(n55Seat);
        // N92. Open session left leftover Solve stats armed.
        // Generate rewrites #stats. Play did not, so leftover
        // solver numbers named the previous walk under the seat.
        // Rewrite maze identity after the session POST discard.
        // Hunt calls play() after installing tour — must not
        // null tour (N50). startFog still must not null tour
        // (N17).
        int n92Stats = n32.indexOf("$(\"stats\").innerHTML =", n32Maze);
        assertThat(n92Stats).isGreaterThan(n32Maze);
        assertThat(n92Stats).isLessThan(n55Seat);
        // N117. Open session left leftover tourGot armed.
        // Hunt remints collected coins. Play reminted trails
        // / won but left leftover tourGot, so leftover
        // collected coins painted on the new seat until the
        // first move reminted. Drop tourGot after the
        // session POST discard. Hunt calls play() after
        // installing tour — must not null tour (N50).
        // startFog still must not null tour (N17).
        int n117PlayGot = n32.indexOf("state.tourGot = []", n32Maze);
        assertThat(n117PlayGot).isGreaterThan(n32Maze);
        assertThat(n117PlayGot).isLessThan(n55Seat);
        assertThat(n32).doesNotContain("state.tour = null");
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
        // N43. Spectate arms the 1s GET /session poll only when STOMP
        // is absent. A broker that connects later used to leave that
        // poll running, so a late snapshot rewound a hop the /player
        // frame already applied. After the GET (and before
        // adoptSessionView) discard when state.stomp is set, and drop
        // the interval. connectStomp clears the leftover poll too.
        // Fog / session / maze discard stays (N34). Must not GET /maze.
        int n43Stomp = n34.indexOf("if (state.stomp)", n34Get);
        int n43Clear = n34.indexOf("clearInterval(state.spectatePoll)", n43Stomp);
        int n43Write = n34.indexOf("adoptSessionView", n43Stomp);
        assertThat(n43Stomp).isGreaterThan(n34Get);
        assertThat(n43Clear).isGreaterThan(n43Stomp);
        assertThat(n43Write).isGreaterThan(n43Clear);
        int n43ConnectFrom = html.indexOf("function connectStomp");
        int n43ConnectTo = html.indexOf("function resubscribe");
        assertThat(n43ConnectFrom).isGreaterThanOrEqualTo(0);
        assertThat(n43ConnectTo).isGreaterThan(n43ConnectFrom);
        String n43Connect = html.substring(n43ConnectFrom, n43ConnectTo);
        int n43Assign = n43Connect.indexOf("state.stomp = client");
        int n43Drop = n43Connect.indexOf("clearInterval(state.spectatePoll)", n43Assign);
        int n43Resub = n43Connect.indexOf("resubscribe()", n43Drop);
        assertThat(n43Assign).isGreaterThanOrEqualTo(0);
        assertThat(n43Drop).isGreaterThan(n43Assign);
        assertThat(n43Resub).isGreaterThan(n43Drop);
        // N44. Living / traffic polls armed because STOMP was absent
        // used to keep GET /maze after CONNECT. A snapshot that left
        // before the next tick wrote the older grid over the frame
        // that already landed. Pollers stop when state.stomp is set;
        // a poll-initiated refresh discards after the GET; connectStomp
        // clears those leftover intervals too. Fog / maze-id discard
        // stays (N28 / N38). Must not GET /maze on the fog path.
        int n44LiveFrom = html.indexOf("function startLivePolling");
        int n44LiveTo = html.indexOf("async function onMutation");
        assertThat(n44LiveFrom).isGreaterThanOrEqualTo(0);
        assertThat(n44LiveTo).isGreaterThan(n44LiveFrom);
        String n44Live = html.substring(n44LiveFrom, n44LiveTo);
        int n44LiveStomp = n44Live.indexOf("state.stomp");
        int n44LiveRefresh = n44Live.indexOf("refreshLivingMaze(true)");
        assertThat(n44LiveStomp).isGreaterThanOrEqualTo(0);
        assertThat(n44LiveStomp).isLessThan(n44LiveRefresh);
        int n44TrafStomp = traf.indexOf("state.stomp");
        int n44TrafRefresh = traf.indexOf("refreshLivingMaze(true)");
        assertThat(n44TrafStomp).isGreaterThanOrEqualTo(0);
        assertThat(n44TrafStomp).isLessThan(n44TrafRefresh);
        int n44Poll = live.indexOf("fromPoll && state.stomp");
        int n44Assign = live.indexOf("state.maze = maze");
        assertThat(n44Poll).isGreaterThanOrEqualTo(0);
        assertThat(n44Poll).isLessThan(n44Assign);
        int n44DropLive = n43Connect.indexOf("clearInterval(state.livePoll)", n43Assign);
        int n44DropTraf = n43Connect.indexOf("clearInterval(state.trafficPoll)", n43Assign);
        assertThat(n44DropLive).isGreaterThan(n43Assign);
        assertThat(n44DropTraf).isGreaterThan(n43Assign);
        assertThat(n43Resub).isGreaterThan(n44DropLive);
        assertThat(n43Resub).isGreaterThan(n44DropTraf);
        // N45. CONNECT drops the STOMP-less polls (N43 / N44). A
        // later disconnect used to leave them dead, so a living /
        // traffic / watched maze froze until the next CONNECT.
        // After state.stomp = null, re-arm the same polls. Do not
        // POST /live (no second ticker). Fog / maze-id discard stays.
        int n45Lost = n43Connect.indexOf("STOMP connection lost");
        int n45Err = n43Connect.lastIndexOf("state.stomp = null", n45Lost);
        int n45Arm = n43Connect.indexOf("armStompFallbacks()", n45Lost);
        assertThat(n45Lost).isGreaterThanOrEqualTo(0);
        assertThat(n45Err).isGreaterThanOrEqualTo(0);
        assertThat(n45Err).isLessThan(n45Lost);
        assertThat(n45Arm).isGreaterThan(n45Lost);
        int n45From = html.indexOf("function armStompFallbacks");
        int n45To = html.indexOf("function resubscribe");
        assertThat(n45From).isGreaterThanOrEqualTo(0);
        assertThat(n45To).isGreaterThan(n45From);
        String n45 = html.substring(n45From, n45To);
        assertThat(n45).contains("startSpectatePolling()");
        assertThat(n45).contains("startLivePolling(");
        assertThat(n45).contains("startTrafficPolling(");
        assertThat(n45).doesNotContain("/live");
        assertThat(n45).doesNotContain("method: \"POST\"");
        // N35. confirmWin / refreshTourStatus GET /session/{id} after
        // only a fog + session-exists check. Generate + a new Play
        // mid-flight painted hunt status or declareWin (leaderboard,
        // campaign) on the maze now on screen. Capture session + maze
        // id before the GET; discard after when fog is on, the session
        // no longer matches, or maze id no longer matches. N24 fog
        // discard stays. tourVerdict sibling too. Must not GET /maze.
        // startFog still must not null tour (N17).
        assertMazeIdDiscardAfterFetch(html, "async function confirmWin",
                "function declareWin", "declareWin");
        assertMazeIdDiscardAfterFetch(html, "async function refreshTourStatus",
                "async function tourVerdict", "$(\"status\")");
        assertMazeIdDiscardAfterFetch(html, "async function tourVerdict",
                "async function analyzeStructure", "p.complete");
        int n35WinFrom = html.indexOf("async function confirmWin");
        int n35WinTo = html.indexOf("function declareWin");
        assertThat(n35WinFrom).isGreaterThanOrEqualTo(0);
        assertThat(n35WinTo).isGreaterThan(n35WinFrom);
        String n35Win = html.substring(n35WinFrom, n35WinTo);
        int n35WinId = n35Win.indexOf("const sessionId");
        int n35WinMaze = n35Win.indexOf("const mazeId");
        int n35WinGet = n35Win.indexOf("/session/${sessionId}");
        int n35WinFog = n35Win.indexOf("if (state.fog)", n35WinGet);
        int n35WinSess = n35Win.indexOf("state.session.id !== sessionId", n35WinGet);
        int n35WinMazeCheck = n35Win.indexOf("state.maze.id !== mazeId", n35WinGet);
        int n35WinWrite = n35Win.indexOf("declareWin", n35WinMazeCheck);
        assertThat(n35WinId).isGreaterThanOrEqualTo(0);
        assertThat(n35WinMaze).isGreaterThan(n35WinId);
        assertThat(n35WinMaze).isLessThan(n35WinGet);
        assertThat(n35WinGet).isGreaterThanOrEqualTo(0);
        assertThat(n35WinFog).isGreaterThan(n35WinGet);
        assertThat(n35WinSess).isGreaterThan(n35WinFog);
        assertThat(n35WinMazeCheck).isGreaterThan(n35WinSess);
        assertThat(n35WinWrite).isGreaterThan(n35WinMazeCheck);
        assertThat(n35Win).doesNotContain("/session/${state.session.id}");
        assertThat(n35Win).doesNotContain("/maze/${");
        int n35HuntFrom = html.indexOf("async function refreshTourStatus");
        int n35HuntTo = html.indexOf("async function tourVerdict");
        assertThat(n35HuntFrom).isGreaterThanOrEqualTo(0);
        assertThat(n35HuntTo).isGreaterThan(n35HuntFrom);
        String n35Hunt = html.substring(n35HuntFrom, n35HuntTo);
        int n35HuntId = n35Hunt.indexOf("const sessionId");
        int n35HuntMaze = n35Hunt.indexOf("const mazeId");
        int n35HuntGet = n35Hunt.indexOf("/session/${sessionId}/tour");
        int n35HuntFog = n35Hunt.indexOf("if (state.fog)", n35HuntGet);
        int n35HuntSess = n35Hunt.indexOf("state.session.id !== sessionId", n35HuntGet);
        int n35HuntMazeCheck = n35Hunt.indexOf("state.maze.id !== mazeId", n35HuntGet);
        int n35HuntWrite = n35Hunt.indexOf("$(\"status\")", n35HuntMazeCheck);
        assertThat(n35HuntId).isGreaterThanOrEqualTo(0);
        assertThat(n35HuntMaze).isGreaterThan(n35HuntId);
        assertThat(n35HuntMaze).isLessThan(n35HuntGet);
        assertThat(n35HuntGet).isGreaterThanOrEqualTo(0);
        assertThat(n35HuntFog).isGreaterThan(n35HuntGet);
        assertThat(n35HuntSess).isGreaterThan(n35HuntFog);
        assertThat(n35HuntMazeCheck).isGreaterThan(n35HuntSess);
        assertThat(n35HuntWrite).isGreaterThan(n35HuntMazeCheck);
        assertThat(n35Hunt).doesNotContain("/session/${state.session.id}");
        assertThat(n35Hunt).doesNotContain("/maze/${");
        assertThat(n35Hunt).doesNotContain("tourFor");
        int n35TvFrom = html.indexOf("async function tourVerdict");
        int n35TvTo = html.indexOf("async function analyzeStructure");
        assertThat(n35TvFrom).isGreaterThanOrEqualTo(0);
        assertThat(n35TvTo).isGreaterThan(n35TvFrom);
        String n35Tv = html.substring(n35TvFrom, n35TvTo);
        int n35TvId = n35Tv.indexOf("const sessionId");
        int n35TvMaze = n35Tv.indexOf("const mazeId");
        int n35TvAwait = n35Tv.indexOf("await refreshTourStatus()");
        int n35TvFog = n35Tv.indexOf("if (state.fog)", n35TvAwait);
        int n35TvSess = n35Tv.indexOf("state.session.id !== sessionId", n35TvAwait);
        int n35TvMazeCheck = n35Tv.indexOf("state.maze.id !== mazeId", n35TvAwait);
        assertThat(n35TvId).isGreaterThanOrEqualTo(0);
        assertThat(n35TvMaze).isGreaterThan(n35TvId);
        assertThat(n35TvMaze).isLessThan(n35TvAwait);
        assertThat(n35TvAwait).isGreaterThanOrEqualTo(0);
        assertThat(n35TvFog).isGreaterThan(n35TvAwait);
        assertThat(n35TvSess).isGreaterThan(n35TvFog);
        assertThat(n35TvMazeCheck).isGreaterThan(n35TvSess);
        assertThat(n35Tv).doesNotContain("/maze/${");
        assertThat(n35Tv).doesNotContain("tourFor");
        int n35DeclFrom = html.indexOf("function declareWin");
        int n35DeclTo = html.indexOf("let statusFlashTimer");
        assertThat(n35DeclFrom).isGreaterThanOrEqualTo(0);
        assertThat(n35DeclTo).isGreaterThan(n35DeclFrom);
        String n35Decl = html.substring(n35DeclFrom, n35DeclTo);
        int n35DeclTv = n35Decl.indexOf("tourVerdict");
        int n35DeclMaze = n35Decl.indexOf("state.maze.id !== mazeId", n35DeclTv);
        assertThat(n35Decl.indexOf("const mazeId")).isGreaterThanOrEqualTo(0);
        assertThat(n35Decl.indexOf("const mazeId")).isLessThan(n35Decl.indexOf("state.won ="));
        assertThat(n35DeclTv).isGreaterThanOrEqualTo(0);
        assertThat(n35DeclMaze).isGreaterThan(n35DeclTv);
        assertThat(n35Decl.indexOf("$(\"status\")", n35DeclMaze)).isGreaterThan(n35DeclMaze);
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

    /**
     * Leftover Race after a theory write (N60). Drop race after the
     * maze-id discard, before the overlay write. Must not null tour.
     */
    private static void assertLeftoverRaceDroppedAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int race = body.indexOf("state.race = null");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(race).isGreaterThan(discard);
        assertThat(race).isLessThan(out);
        assertThat(body).contains("animGen++");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover ghost after a theory write (N80). Drop the ticker
     * after the maze-id discard, before the overlay write. Must
     * not null tour.
     */
    private static void assertLeftoverGhostDroppedAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int clear = body.indexOf("clearInterval(state.ghostTimer)");
        int timer = body.indexOf("state.ghostTimer = null");
        int gone = body.indexOf("state.ghost = null");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(clear).isGreaterThan(discard);
        assertThat(clear).isLessThan(out);
        assertThat(timer).isGreaterThan(clear);
        assertThat(timer).isLessThan(out);
        assertThat(gone).isGreaterThan(timer);
        assertThat(gone).isLessThan(out);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover Hardest after a theory write (N61). Drop hardest after
     * the maze-id discard, before the overlay write. Must not null tour.
     */
    private static void assertLeftoverHardestDroppedAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int hard = body.indexOf("state.hardest = null");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(hard).isGreaterThan(discard);
        assertThat(hard).isLessThan(out);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover Compare hover after a theory write (N62). Drop path
     * after the maze-id discard when caption is compare, before the
     * overlay write. Must not null tour. Must not always-null path
     * (Solve hint stays).
     */
    private static void assertLeftoverComparePathDroppedAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int cap = body.indexOf("caption === \"compare\"");
        int path = body.indexOf("state.path = null");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(cap).isGreaterThan(discard);
        assertThat(cap).isLessThan(out);
        assertThat(path).isGreaterThan(cap);
        assertThat(path).isLessThan(out);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover Solve search wash after a theory write (N87).
     * Drop expansions after the maze-id discard, before the
     * overlay write. Leftover path stays unless caption is
     * compare (N62). Must not null tour.
     */
    private static void assertLeftoverSolveSearchDroppedAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int wash = body.indexOf("state.expansions = []");
        int cap = body.indexOf("caption === \"compare\"");
        int path = body.indexOf("state.path = null");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(wash).isGreaterThan(discard);
        assertThat(wash).isLessThan(out);
        assertThat(wash).isLessThan(cap);
        assertThat(path).isGreaterThan(cap);
        assertThat(path).isLessThan(out);
        assertThat(body).contains("state.searchProgress = 1");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover Solve stats after a theory write (N99).
     * Rewrite maze identity after the maze-id discard,
     * before the overlay write. Leftover path stays
     * unless caption is compare (N62). Must not null tour.
     */
    private static void assertLeftoverSolveStatsDroppedAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int stats = body.indexOf("$(\"stats\").innerHTML =");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(stats).isGreaterThan(discard);
        assertThat(stats).isLessThan(out);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover sibling theory after a theory write (N63). Drop the
     * remint overlay after the maze-id discard, before the write.
     * Must not null tour.
     */
    private static void assertLeftoverSiblingTheoryDroppedAfterDiscard(String html, String start,
            String end, String write, String drop) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int gone = body.indexOf(drop);
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(gone).isGreaterThan(discard);
        assertThat(gone).isLessThan(out);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover trails / won / leaderboard stay (N111). Same
     * session still walks those crumbs, still won, still
     * names this maze's board. Must not drop them. Must not
     * remint the board. Must not null tour.
     */
    private static void assertLeftoverWalkChromeStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.trails = {}");
        assertThat(body).doesNotContain("state.won = null");
        assertThat(body).doesNotContain("refreshLeaderboard");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover campaign stay (N112). Same maze still owns
     * the ladder. Must not leaveCampaign. Must not null tour.
     */
    private static void assertLeftoverCampaignStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("leaveCampaign()");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover live / traffic stay (N113). Same maze still
     * erodes. Living under fog is honest (N19). Must not
     * drop or remint the poller. Must not rewrite #live /
     * #traffic. Must not null tour.
     */
    private static void assertLeftoverLiveStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("clearInterval(state.livePoll)");
        assertThat(body).doesNotContain("clearInterval(state.trafficPoll)");
        assertThat(body).doesNotContain("startLivePolling");
        assertThat(body).doesNotContain("startTrafficPolling");
        assertThat(body).doesNotContain("$(\"live\")");
        assertThat(body).doesNotContain("$(\"traffic\")");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover form stay (N114 / N123). Same maze still owns
     * the recipe. Must not rewrite rows / cols / seed /
     * generator / braid / hotspots / hotspotCost. Must not
     * null tour.
     */
    private static void assertLeftoverFormStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"rows\").value =");
        assertThat(body).doesNotContain("$(\"cols\").value =");
        assertThat(body).doesNotContain("$(\"seed\").value =");
        assertThat(body).doesNotContain("$(\"generator\").value =");
        assertThat(body).doesNotContain("$(\"braid\").value =");
        assertThat(body).doesNotContain("$(\"hotspots\").value =");
        assertThat(body).doesNotContain("$(\"hotspotCost\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin / log / player stay (N115). Plugins are
     * a global catalog. Log is history. #player is the name
     * you typed. Must not remint the roster. Must not clear
     * the log. Must not rewrite the name. Must not null tour.
     */
    private static void assertLeftoverCatalogStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("pluginBox");
        assertThat(body).doesNotContain("$(\"log\").innerHTML");
        assertThat(body).doesNotContain("$(\"log\").textContent");
        assertThat(body).doesNotContain("$(\"player\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover lab / tournament / PNG stay (N116). The curve
     * and the sample are what you asked for. The snapshot is
     * the maze still on the canvas. Must not rewrite #labOut
     * / #tourBox / #pngExport. Must not null tour.
     */
    private static void assertLeftoverLabStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("labOut");
        assertThat(body).doesNotContain("tourBox");
        assertThat(body).doesNotContain("pngExport");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover tourGot stay (N117). Same hunt still owns
     * those collected coins. Must not empty tourGot. Must
     * not null tour.
     */
    private static void assertLeftoverTourGotStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.tourGot = []");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover auth stay (N118). Still signed in. Must not
     * logout. Must not rewrite the token or #authWho. Must
     * not null tour.
     */
    private static void assertLeftoverAuthStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("logout()");
        assertThat(body).doesNotContain("state.token =");
        assertThat(body).doesNotContain("state.user =");
        assertThat(body).doesNotContain("TOKEN_KEY");
        assertThat(body).doesNotContain("authWho");
        assertThat(body).doesNotContain("sessionStorage");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover daily / breed stay (N119). Same maze still
     * daily. Breed parent still valid. Must not drop
     * dailyId or prevMazeId. Must not disable #breed. Must
     * not null tour.
     */
    private static void assertLeftoverDailyBreedStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.dailyId = null");
        assertThat(body).doesNotContain("state.prevMazeId = null");
        assertThat(body).doesNotContain("$(\"breed\").disabled");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover hash stay on Hunt / theory (N120). Same maze
     * still owns the bar. Play / Fog / Join remint when the
     * exclusive kind changes. Must not pinHash. Must not
     * null tour.
     */
    private static void assertLeftoverHashStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("pinHash()");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover harden stay (N121). Same maze still alive.
     * Living under fog is honest (N19). Must not rewrite
     * #harden. Must not null tour.
     */
    private static void assertLeftoverHardenStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"harden\")");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover picker stay (N122). The solver, heuristic,
     * rival, and leaderboard filter are what you asked for.
     * Must not rewrite those selects. Must not null tour.
     */
    private static void assertLeftoverPickerStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"solver\").value =");
        assertThat(body).doesNotContain("$(\"lensH\").value =");
        assertThat(body).doesNotContain("$(\"rival\").value =");
        assertThat(body).doesNotContain("$(\"lbGen\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover sidebar picker stay (N124). The lab metric
     * and tournament braid are what you asked for. Must not
     * rewrite those selects. Must not null tour.
     */
    private static void assertLeftoverSidebarStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"labMetric\").value =");
        assertThat(body).doesNotContain("$(\"tourBraid\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover sessionStart stay (N125). Hunt leftover
     * clock is this walk. Fog leftover clock is unused
     * (declareWin needs session + ghost). Must not remint
     * sessionStart. Must not null tour.
     */
    private static void assertLeftoverClockStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.sessionStart =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover credential stay (N126). The name you typed
     * still owns #user / leftover #pass. Must not rewrite
     * those inputs. Must not null tour.
     */
    private static void assertLeftoverCredentialStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"user\").value =");
        assertThat(body).doesNotContain("$(\"pass\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover picker caption stay (N127). leftover #genInfo
     * / leftover #solInfo still name leftover generator /
     * leftover solver. Must not remint updateInfo. Must not
     * null tour.
     */
    private static void assertLeftoverInfoStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("updateInfo");
        assertThat(body).doesNotContain("genInfo");
        assertThat(body).doesNotContain("solInfo");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover campaign box stay (N128). leftover #campaignBox
     * still names leftover ladder. Must not remint
     * renderCampaign. Must not rewrite campaignBox. Must not
     * null tour.
     */
    private static void assertLeftoverCampaignBoxStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("renderCampaign");
        assertThat(body).doesNotContain("campaignBox");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover search / path progress stay (N129). Play /
     * Fog / Join remint leftover path / leftover expansions
     * and leave leftover progress unused. Must not remint
     * searchProgress / pathProgress. Must not null tour.
     */
    private static void assertLeftoverProgressStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.searchProgress");
        assertThat(body).doesNotContain("state.pathProgress");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover cadence stay (N130). leftover liveTickMs /
     * leftover trafficTickMs still name leftover cadence
     * you asked for. Must not remint leftover cadence.
     * Must not null tour.
     */
    private static void assertLeftoverCadenceStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.liveTickMs");
        assertThat(body).doesNotContain("state.trafficTickMs");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover cleared stay (N131). leftover stages you
     * cleared still name leftover ladder. Must not remint
     * leftover cleared. Must not null tour.
     */
    private static void assertLeftoverClearedStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.cleared");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover Play / Fog button stay (N132). Same maze still
     * playable / still fogable. Must not rewrite leftover
     * #play / leftover #fog. Must not null tour.
     */
    private static void assertLeftoverWalkButtonStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"play\")");
        assertThat(body).doesNotContain("$(\"fog\")");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover algos stay (N133). leftover catalog you loaded
     * still names leftover generator / leftover solver.
     * Must not remint leftover algos. Must not null tour.
     */
    private static void assertLeftoverAlgosStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.algos");
        assertThat(body).doesNotContain("loadAlgorithms");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover STOMP stay (N134). leftover frames still
     * name this maze. Must not remint leftover subs.
     * Must not null tour.
     */
    private static void assertLeftoverStompStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("resubscribe");
        assertThat(body).doesNotContain("connectStomp");
        assertThat(body).doesNotContain("state.subs");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover lbQuery stay (N135). leftover last
     * /leaderboard path still names this maze. Must not
     * remint leftover lbQuery. Must not null tour.
     */
    private static void assertLeftoverLbQueryStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("state.lbQuery");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #pngExport stay (N137). leftover snapshot
     * stays visible. Fog leftover snapshot visibility
     * unused (click remints the fog walk). Must not remint
     * leftover snapshot visibility. Must not remint leftover
     * href. Must not null tour.
     */
    private static void assertLeftoverPngExportStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"pngExport\")");
        assertThat(body).doesNotContain("toDataURL");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover expansions remint stay (N138). Hunt / Play /
     * Fog / theory / Join remint leftover wash after the
     * maze-id discard. Theory remint already N87. Distinct
     * from leftover progress clock (N129). Must not null
     * tour.
     */
    private static void assertLeftoverExpansionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int wash = body.indexOf("state.expansions = []");
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(wash).isGreaterThan(discard);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover sanctuaries remint stay (N139). Hunt / Play /
     * Fog / theory / Join remint leftover rings after the
     * maze-id discard. Theory remint already N63. Must not
     * null tour.
     */
    private static void assertLeftoverSanctuariesStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int rings = body.indexOf("state.sanctuaries =");
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(rings).isGreaterThan(discard);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugins describe stay (N140). leftover
     * description you already loaded. leftover plugin stay
     * already forbids reminting leftover roster (N115).
     * Must not remint leftover describe. Must not null tour.
     */
    private static void assertLeftoverPluginsDescribeStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("m.description");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover walk chrome remint stay (N141). Play / Fog
     * remint leftover crumbs after the maze-id discard.
     * Join remints leftover joiner crumbs. leftover walk
     * chrome stay already N111. Must not null tour.
     */
    private static void assertLeftoverWalkChromeRemintStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int crumbs = body.indexOf("state.trails");
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(crumbs).isGreaterThan(discard);
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #lb title stay (N142). leftover heading still
     * names this maze's board. leftover walk chrome stay
     * already forbids reminting leftover board (N111).
     * leftover lbQuery stay already N135. Must not remint
     * leftover #lbTitle. Must not null tour.
     */
    private static void assertLeftoverLbTitleStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("lbTitle");
        assertThat(body).doesNotContain("refreshLeaderboard");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #lb rows stay (N143). leftover scores still
     * name this maze's board. leftover walk chrome stay
     * already forbids reminting leftover board (N111).
     * leftover #lb title stay already N142. Must not remint
     * leftover #lb rows. Must not null tour.
     */
    private static void assertLeftoverLbRowsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"lb\").innerHTML");
        assertThat(body).doesNotContain("$(\"lb\").textContent");
        assertThat(body).doesNotContain("refreshLeaderboard");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #lbGen disabled stay (N144). leftover filter
     * still enabled or still locked to this maze. leftover
     * picker stay already forbids reminting leftover
     * #lbGen value (N122). Must not remint leftover
     * #lbGen disabled. Must not null tour.
     */
    private static void assertLeftoverLbGenDisabledStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"lbGen\").disabled");
        assertThat(body).doesNotContain("refreshLeaderboard");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #lbGen options stay (N145). leftover filter
     * roster you loaded. leftover picker stay already
     * forbids reminting leftover #lbGen value (N122).
     * leftover algos stay already N133. Must not remint
     * leftover #lbGen options. Must not null tour.
     */
    private static void assertLeftoverLbGenOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("lbGen.innerHTML");
        assertThat(body).doesNotContain("lbGen.appendChild");
        assertThat(body).doesNotContain("loadAlgorithms");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #rival options stay (N146). leftover arena
     * roster you loaded. leftover picker stay already
     * forbids reminting leftover rival value (N122).
     * leftover algos stay already N133. Must not remint
     * leftover #rival options. Must not null tour.
     */
    private static void assertLeftoverRivalOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("rival.innerHTML");
        assertThat(body).doesNotContain("rival.appendChild");
        assertThat(body).doesNotContain("loadAlgorithms");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #solver options stay (N147). leftover solver
     * roster you loaded. leftover picker stay already
     * forbids reminting leftover solver value (N122).
     * leftover algos stay already N133. Must not remint
     * leftover #solver options. Must not null tour.
     */
    private static void assertLeftoverSolverOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("[\"solver\", all.solvers]");
        assertThat(body).doesNotContain("loadAlgorithms");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #generator options stay (N148). leftover
     * generator roster you loaded. leftover form stay
     * already forbids reminting leftover generator value
     * (N114). leftover algos stay already N133. Must not
     * remint leftover #generator options. Must not null tour.
     */
    private static void assertLeftoverGeneratorOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("[\"generator\", all.generators]");
        assertThat(body).doesNotContain("loadAlgorithms");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #lensH options stay (N149). leftover
     * heuristic roster you loaded. leftover picker stay
     * already forbids reminting leftover #lensH value
     * (N122). Must not remint leftover #lensH options.
     * Must not null tour.
     */
    private static void assertLeftoverLensHOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"lensH\").innerHTML");
        assertThat(body).doesNotContain("lensH.innerHTML");
        assertThat(body).doesNotContain("lensH.appendChild");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #labMetric options stay (N150). leftover
     * metric roster you loaded. leftover sidebar picker
     * stay already forbids reminting leftover #labMetric
     * value (N124). Must not remint leftover #labMetric
     * options. Must not null tour.
     */
    private static void assertLeftoverLabMetricOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("loadLabMetrics");
        assertThat(body).doesNotContain("const sel = $(\"labMetric\")");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #tourBraid options stay (N151). leftover
     * sample braid roster you loaded. leftover sidebar
     * picker stay already forbids reminting leftover
     * #tourBraid value (N124). Must not remint leftover
     * #tourBraid options. Must not null tour.
     */
    private static void assertLeftoverTourBraidOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("syncBraid");
        assertThat(body).doesNotContain("applyBraidFromMaze");
        assertThat(body).doesNotContain("tourBraid.appendChild");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #braid options stay (N152). leftover braid
     * roster you loaded. leftover form stay already forbids
     * reminting leftover braid value (N114). leftover
     * #tourBraid options stay already N151. Must not remint
     * leftover #braid options. Must not null tour.
     */
    private static void assertLeftoverBraidOptionsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"braid\").appendChild");
        assertThat(body).doesNotContain("applyBraidFromMaze");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin version stay (N153). leftover version
     * you already loaded. leftover plugin stay already
     * forbids reminting leftover roster (N115). leftover
     * plugins describe stay already N140. Must not remint
     * leftover version. Must not null tour.
     */
    private static void assertLeftoverPluginVersionStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("m.version");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin state stay (N154). leftover boot
     * state you already loaded. leftover plugin stay
     * already forbids reminting leftover roster (N115).
     * leftover plugin version stay already N153. Must not
     * remint leftover plugin state. Must not null tour.
     */
    private static void assertLeftoverPluginStateStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("p.state");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin error stay (N155). leftover failure
     * you already loaded. leftover plugin stay already
     * forbids reminting leftover roster (N115). leftover
     * plugin state stay already N154. Must not remint
     * leftover plugin error. Must not null tour.
     */
    private static void assertLeftoverPluginErrorStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("p.error");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin displayName stay (N156). leftover
     * name you already loaded. leftover plugin stay already
     * forbids reminting leftover roster (N115). leftover
     * plugin error stay already N155. Must not remint
     * leftover plugin displayName. Must not null tour.
     */
    private static void assertLeftoverPluginDisplayNameStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("m.displayName");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin id stay (N157). leftover id you
     * already loaded. leftover plugin stay already forbids
     * reminting leftover roster (N115). leftover plugin
     * displayName stay already N156. Must not remint leftover
     * plugin id. Must not null tour.
     */
    private static void assertLeftoverPluginIdStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("p.id");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin manifest stay (N158). leftover
     * manifest you already loaded. leftover plugin stay
     * already forbids reminting leftover roster (N115).
     * leftover plugin id stay already N157. Must not remint
     * leftover plugin manifest. Must not null tour.
     */
    private static void assertLeftoverPluginManifestStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("p.manifest");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin empty copy stay (N159). leftover
     * empty roster you already loaded. leftover plugin stay
     * already forbids reminting leftover roster (N115).
     * leftover plugin manifest stay already N158. Must not
     * remint leftover plugin empty copy. Must not null tour.
     */
    private static void assertLeftoverPluginEmptyCopyStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("no external plugins loaded");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin unavailable copy stay (N160). leftover
     * unavailable roster you already loaded. leftover plugin
     * stay already forbids reminting leftover roster (N115).
     * leftover plugin empty copy stay already N159. Must not
     * remint leftover plugin unavailable copy. Must not null
     * tour.
     */
    private static void assertLeftoverPluginUnavailableCopyStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("plugins unavailable");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin loading copy stay (N161). leftover
     * loading roster you already loaded. leftover plugin
     * stay already forbids reminting leftover roster (N115).
     * leftover plugin unavailable copy stay already N160.
     * Must not remint leftover plugin loading copy. Must not
     * null tour.
     */
    private static void assertLeftoverPluginLoadingCopyStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("loading…");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #lb loading copy stay (N162). leftover board
     * loading you already loaded. leftover #lb rows stay
     * already forbids reminting leftover board rows (N143).
     * leftover plugin loading copy stay already N161. Must
     * not remint leftover #lb loading copy. Must not null
     * tour.
     */
    private static void assertLeftoverLbLoadingCopyStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("loading…");
        assertThat(body).doesNotContain("refreshLeaderboard");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover /plugins fetch stay (N163). leftover catalog
     * fetch you already loaded. leftover plugin stay already
     * forbids reminting leftover roster (N115). leftover #lb
     * loading copy stay already N162. Must not remint leftover
     * /plugins fetch. Must not match leftover plugin failure
     * topic. Must not null tour.
     */
    private static void assertLeftoverPluginsFetchStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("api(\"/plugins\")");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover plugin list.map stay (N164). leftover roster
     * rows you already loaded. leftover plugin stay already
     * forbids reminting leftover roster (N115). leftover
     * /plugins fetch stay already N163. Must not remint
     * leftover plugin rows. Must not null tour.
     */
    private static void assertLeftoverPluginListMapStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("list.map");
        assertThat(body).doesNotContain("refreshPlugins");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #rows stay (N165). leftover height you
     * already asked for. leftover form stay already forbids
     * reminting leftover recipe (N114). Must not remint
     * leftover #rows. Must not null tour.
     */
    private static void assertLeftoverRowsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"rows\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #cols stay (N166). leftover width you already
     * asked for. leftover form stay already forbids reminting
     * leftover recipe (N114). leftover #rows stay already
     * N165. Must not remint leftover #cols. Must not null
     * tour.
     */
    private static void assertLeftoverColsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"cols\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #seed stay (N167). leftover seed you already
     * asked for. leftover form stay already forbids reminting
     * leftover recipe (N114). leftover #cols stay already
     * N166. Must not remint leftover #seed. Must not null
     * tour.
     */
    private static void assertLeftoverSeedStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"seed\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #hotspots stay (N168). leftover spots you
     * already asked for. leftover form stay already forbids
     * reminting leftover recipe (N114). leftover #seed stay
     * already N167. leftover #hotspotCost stay already N123.
     * Must not remint leftover #hotspots. Must not null tour.
     */
    private static void assertLeftoverHotspotsStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"hotspots\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #generator stay (N169). leftover
     * leftover generator you already asked for. leftover
     * leftover form stay already forbids reminting leftover
     * leftover recipe (N114). leftover leftover #hotspots
     * stay already N168. Must not remint leftover leftover
     * #generator. Must not null tour.
     */
    private static void assertLeftoverGeneratorStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"generator\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #braid stay (N170). leftover leftover
     * braid you already asked for. leftover leftover form stay
     * already forbids reminting leftover leftover recipe
     * (N114). leftover leftover #generator stay already N169.
     * Must not remint leftover leftover #braid. Must not null
     * tour.
     */
    private static void assertLeftoverBraidStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"braid\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover solver stay (N171). leftover leftover
     * solver you already asked for. leftover leftover picker
     * stay already forbids reminting leftover leftover solver
     * (N122). leftover leftover #braid stay already N170.
     * Must not remint leftover leftover solver. Must not null
     * tour.
     */
    private static void assertLeftoverSolverStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"solver\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #lensH stay (N172). leftover leftover
     * heuristic you already asked for. leftover leftover
     * picker stay already forbids reminting leftover leftover
     * #lensH (N122). leftover leftover solver stay already
     * N171. Must not remint leftover leftover #lensH. Must
     * not null tour.
     */
    private static void assertLeftoverLensHStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"lensH\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover rival stay (N173). leftover leftover
     * rival you already asked for. leftover leftover picker
     * stay already forbids reminting leftover leftover rival
     * (N122). leftover leftover #lensH stay already N172.
     * leftover leftover #rival options stay already N146.
     * Must not remint leftover leftover rival. Must not null
     * tour.
     */
    private static void assertLeftoverRivalStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"rival\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #lbGen stay (N174). leftover leftover
     * filter you already asked for. leftover leftover picker
     * stay already forbids reminting leftover leftover #lbGen
     * (N122). leftover leftover rival stay already N173.
     * leftover leftover #lbGen disabled stay already N144.
     * Must not remint leftover leftover #lbGen. Must not null
     * tour.
     */
    private static void assertLeftoverLbGenStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"lbGen\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #labMetric stay (N175). leftover
     * leftover metric you already asked for. leftover leftover
     * sidebar stay already forbids reminting leftover leftover
     * #labMetric (N124). leftover leftover #lbGen stay already
     * N174. Must not remint leftover leftover #labMetric. Must
     * not null tour.
     */
    private static void assertLeftoverLabMetricStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"labMetric\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #tourBraid stay (N176). leftover
     * leftover tour braid you already asked for. leftover
     * leftover sidebar stay already forbids reminting leftover
     * leftover #tourBraid (N124). leftover leftover #labMetric
     * stay already N175. Must not remint leftover leftover
     * #tourBraid. Must not null tour.
     */
    private static void assertLeftoverTourBraidStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"tourBraid\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #hotspotCost stay (N177). leftover
     * leftover cost you already asked for. leftover leftover
     * form stay already forbids reminting leftover leftover
     * #hotspotCost (N114 / N123). leftover leftover #tourBraid
     * stay already N176. Must not remint leftover leftover
     * #hotspotCost. Must not null tour.
     */
    private static void assertLeftoverHotspotCostStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"hotspotCost\").value =");
        assertThat(body).doesNotContain("applyRecipeToForm");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #player stay (N178). leftover leftover
     * name you already typed. leftover leftover catalog stay
     * already forbids reminting leftover leftover #player
     * (N115). leftover leftover #hotspotCost stay already
     * N177. Must not remint leftover leftover #player. Must
     * not null tour.
     */
    private static void assertLeftoverPlayerStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"player\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #labOut stay (N179). leftover leftover
     * curve you already asked for. leftover leftover lab stay
     * already forbids reminting leftover leftover #labOut
     * (N116). leftover leftover #player stay already N178.
     * Must not remint leftover leftover #labOut. Must not null
     * tour.
     */
    private static void assertLeftoverLabOutStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("labOut");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #tourBox stay (N180). leftover leftover
     * sample you already asked for. leftover leftover lab stay
     * already forbids reminting leftover leftover #tourBox
     * (N116). leftover leftover #labOut stay already N179.
     * Must not remint leftover leftover #tourBox. Must not null
     * tour.
     */
    private static void assertLeftoverTourBoxStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("tourBox");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #log stay (N181). leftover leftover
     * history you already loaded. leftover leftover catalog stay
     * already forbids reminting leftover leftover log (N115).
     * leftover leftover #tourBox stay already N180. Must not
     * remint leftover leftover #log. Must not null tour.
     */
    private static void assertLeftoverLogStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"log\").innerHTML");
        assertThat(body).doesNotContain("$(\"log\").textContent");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #user stay (N182). leftover leftover
     * account you already typed. leftover leftover auth stay
     * already forbids reminting leftover leftover token (N118).
     * leftover leftover #log stay already N181. Must not remint
     * leftover leftover #user. Must not null tour.
     */
    private static void assertLeftoverUserStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"user\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover leftover #pass stay (N183). leftover leftover
     * secret you already typed. leftover leftover auth stay
     * already forbids reminting leftover leftover token (N118).
     * leftover leftover #user stay already N182. Must not remint
     * leftover leftover #pass. Must not null tour.
     */
    private static void assertLeftoverPassStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("$(\"pass\").value =");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /**
     * Leftover #asciiOut stay (N136). leftover dump stays
     * hidden. Must not unhide leftover dump. Must not remint
     * leftover dump. Must not null tour.
     */
    private static void assertLeftoverAsciiStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        assertThat(body).doesNotContain("hidden = false");
        assertThat(body).doesNotContain("showAscii");
        assertThat(body).doesNotContain("state.tour = null");
    }

    /** Remint stay (N78). Writer must not null tour. */
    private static void assertTourStay(String html, String start, String end) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        assertThat(html.substring(from, to)).doesNotContain("state.tour = null");
    }

    /**
     * Leftover ASCII after a theory write (N73). Hide #asciiOut
     * after the maze-id discard, before the overlay write. Must
     * not null tour.
     */
    private static void assertLeftoverAsciiHiddenAfterDiscard(String html, String start,
            String end, String write) {
        int from = html.indexOf(start);
        int to = html.indexOf(end, from + start.length());
        assertThat(from).isGreaterThanOrEqualTo(0);
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int discard = body.lastIndexOf("state.maze.id !== mazeId");
        int hide = body.indexOf("$(\"asciiOut\").hidden = true");
        int clear = body.indexOf("$(\"asciiOut\").textContent = \"\"");
        int out = body.indexOf(write);
        assertThat(discard).isGreaterThanOrEqualTo(0);
        assertThat(hide).isGreaterThan(discard);
        assertThat(hide).isLessThan(out);
        assertThat(clear).isGreaterThan(hide);
        assertThat(clear).isLessThan(out);
        assertThat(body).doesNotContain("state.tour = null");
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

    /** Leftover flash restore must not overwrite the new status (N48). */
    private static void assertStatusFlashClearedBeforeWrite(String html, String start,
            String end) {
        int from = html.indexOf(start);
        assertThat(from).isGreaterThanOrEqualTo(0);
        int to = html.indexOf(end, from + start.length());
        assertThat(to).isGreaterThan(from);
        String body = html.substring(from, to);
        int clear = body.indexOf("clearTimeout(statusFlashTimer)");
        int write = body.indexOf("$(\"status\").textContent");
        assertThat(clear).isGreaterThanOrEqualTo(0);
        assertThat(write).isGreaterThanOrEqualTo(0);
        assertThat(clear).isLessThan(write);
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
