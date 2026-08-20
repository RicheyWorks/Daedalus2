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
                .contains("recipeParts").contains("rebuildFromRecipe");
    }
}
