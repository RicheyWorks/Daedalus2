// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.server.config.ProdSecurityConfig;
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
        byte[] body = client.get().uri("/index.html").exchange()
                .expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        assertThat(body).isNotNull();
        StringBuilder js = new StringBuilder();
        for (String path : ProdSecurityConfig.STATIC_SCRIPTS) {
            byte[] bytes = client.get().uri(path).exchange()
                    .expectStatus().isOk()
                    .expectBody().returnResult().getResponseBody();
            assertThat(bytes).as("nothing served at %s", path).isNotNull();
            js.append(new String(bytes));
        }
        String html = new String(body) + js;
        // Public surface, not leftover names. Paths, ids, permalink kinds, and
        // refuse copy are what a player or operator sees. Function names belong
        // in sweep/ — a rename there must not fail this boot-and-serve test.
        assertThat(html).contains("DAEDALUS").contains("id=\"gate\"").contains("id=\"gateWell\"")
                .contains("id=\"gateExploreCmd\"").contains("id=\"home\"")
                .contains("gate-brand").contains("gate-veil").contains("Other hosts")
                .contains("gateBreath").contains("gateVeil")
                .contains("/api/v1").contains("/ws")
                .contains("/auth/login").contains("id=\"login\"").contains("id=\"fog\"")
                .contains("id=\"legend\"").contains("id=\"labMetric\"").contains("class=\"rail\"")
                .contains("id=\"compareBox\"").contains("id=\"genInfo\"").contains("id=\"asciiOut\"")
                .contains("class=\"exports\"").contains("EXPORT_RESERVE")
                .contains("Pick a generator and press Generate")
                .contains("Bahnschrift")
                .contains("radial-gradient(80% 70% at 50% 45%")
                .contains("rgba(184, 133, 56")
                .contains("0 0 18px rgba(62, 224, 143")
                .contains("backdrop-filter")
                .contains("floorWarm")
                .contains("wallWarm")
                .contains("shadowBlur")
                .contains("ghost:")
                .contains("ghostDisc")
                .contains("data-key=\"path\"").contains("data-key=\"floor\"")
                .contains("data-key=\"fog\"")
                .contains("Authorization").contains("text/plain").contains("id=\"ascii\"")
                .contains("/plugins").contains("id=\"pluginBox\"")
                .contains("id=\"lbGen\"").contains("generator=")
                .contains("view.walks").contains("#session=").contains("#daily")
                .contains("id=\"braid\"").contains("/topic/plugins/failures")
                .contains("integrity=")
                .contains("fog walk ended")
                .contains("every solver failed")
                .contains("aged out of the cache")
                .contains("classifier is warming")
                .contains("this session already finished")
                .contains("that session is gone")
                .contains("too many mazes are already alive")
                .contains("too many mazes are already tracked")
                .contains("session-capacity").contains("agent-capacity")
                .contains("maze-capacity").contains("tour-capacity")
                .contains("too many sessions are already open")
                .contains("too many fog walks are already open")
                .contains("too many mazes are already cached")
                .contains("too many waypoint hunts are already seated")
                .contains("permalink maze aged out —")
                .contains("that maze is gone")
                .contains("that fog walk is gone")
                .contains("solver-budget")
                .contains("this solver spent its node budget")
                .contains("spectating is read-only")
                .doesNotContain("positions[state.session.primary]")
                .doesNotContain("move(state.session.primary")
                .doesNotContain("move(state.seat || state.session.primary");
    }
}
