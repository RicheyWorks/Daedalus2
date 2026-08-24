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
                .contains("apiPlain(`/maze/${state.maze.id}`)")
                .doesNotContain("?solve=${");
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
                .contains("loadCampaign");
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
