// SPDX-License-Identifier: MIT

package com.daedalus.server;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Pins that the static web UI is actually served. The page is plain static
 * content under {@code resources/static}, which Boot serves by convention —
 * and conventions are exactly what starter upgrades silently change.
 *
 * <p><b>This is a boot-and-serve contract, not a leftover-state mirror.</b>
 * Leftover-state and feature regressions belong in {@code sweep/}:
 * {@code api-sweep.py} runs in CI; {@code ui-sweep.js} is the local Playwright
 * pass. Do not add {@code indexOf("async function …")} body pins here.
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
        String[] scripts = {
                "/draw.js", "/api.js", "/share.js", "/fog.js", "/seat.js",
                "/lab.js", "/caption.js", "/mint.js", "/campaign.js",
                "/theory.js", "/live.js", "/session.js", "/fogwalk.js",
                "/app.js",
        };
        byte[] body = client.get().uri("/index.html").exchange()
                .expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        assertThat(body).isNotNull();
        StringBuilder js = new StringBuilder();
        for (String path : scripts) {
            byte[] bytes = client.get().uri(path).exchange()
                    .expectStatus().isOk()
                    .expectBody().returnResult().getResponseBody();
            assertThat(bytes).as("nothing served at %s", path).isNotNull();
            js.append(new String(bytes));
        }
        String html = new String(body) + js;
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
    }
}
