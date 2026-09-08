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
                .contains("rgba(245, 193, 74, .05)")
                .contains("rgba(184, 133, 56, 0.28)")
                .contains("/api/v1").contains("/ws")
                .contains("/auth/login").contains("id=\"login\"").contains("id=\"fog\"")
                .contains("id=\"legend\"").contains("id=\"labMetric\"").contains("class=\"rail\"")
                .contains("id=\"compareBox\"").contains("id=\"genInfo\"").contains("id=\"asciiOut\"")
                .contains("class=\"exports\"").contains("EXPORT_RESERVE")
                .contains("Pick a generator and press Generate")
                .contains("Bahnschrift")
                .contains("radial-gradient(80% 70% at 50% 45%")
                .contains("inset 0 0 48px rgba(0, 0, 0, .35)")
                .contains("rgba(184, 133, 56")
                .contains("0 0 18px rgba(62, 224, 143")
                .contains("animation: gateBreath 4.5s ease-in-out infinite")
                .contains("board-panel")
                .contains("0 0 0 1px rgba(16, 11, 8, 0.85)")
                .contains("inset 3px 0 0 rgba(184, 133, 56")
                .contains("inset 3px 0 0 rgba(184, 133, 56, 0.55)")
                .contains("0 0 12px rgba(184, 133, 56")
                .contains("outline: 2px solid rgba(184, 133, 56")
                .contains("border: 1px solid rgba(184, 133, 56, 0.28)")
                .contains("border: 1px solid rgba(184, 133, 56, 0.32)")
                .contains("border: 1px solid rgba(184, 133, 56, 0.36)")
                .contains("button.accent")
                .contains("border-color: var(--gold)")
                .contains("backdrop-filter")
                .contains("floorWarm")
                .contains("wallWarm")
                .contains("0.22 * edge")
                .contains("mixHex(COLORS.floorHi, COLORS.floorDim, 0.22 * edge)")
                .contains("mixHex(COLORS.wall, COLORS.unseen, 0.28 * edge)")
                .contains("FOG_FRONTIER")
                .contains("fogFrontier")
                .contains("FOG_FRONTIER_BREATH_MS")
                .contains("0.92 + 0.16")
                .contains("core + geom.cell * (0.18 + 0.05")
                .contains("geom.cell * (0.28 + 0.04")
                .contains("ENDPOINT_BREATH_MS")
                .contains("0.55 + 0.06")
                .contains("shadowBlur")
                .contains("EMPTY_BREATH_MS")
                .contains("0.36 + 0.10")
                .contains("0.08 + 0.04")
                .contains("0.04 + 0.03")
                .contains("prefers-reduced-motion")
                .contains("stageRimBreath")
                .contains("#151c26 0%")
                .contains("boardRimBreath")
                .contains("panelRimBreath")
                .contains("headerRimBreath")
                .contains("legendFadeBreath")
                .contains("ghost:")
                .contains("ghostDisc")
                .contains("ageFade")
                .contains("0.35 + 0.65")
                .contains("0.55 + 0.45")
                .contains("\"ribbon\"")
                .contains("g.globalAlpha = 0.26")
                .contains("0.32, true")
                .contains("GHOST_BREATH_MS")
                .contains("0.18 + 0.08")
                .contains("WAYPOINT_BREATH_MS")
                .contains("0.14 + 0.05")
                .contains("0.10 + 0.10")
                .contains("0.72 + 0.28")
                .contains("PATH_HEAD_BREATH_MS")
                .contains("0.5 + 0.05")
                .contains("SANCTUARY_BREATH_MS")
                .contains("0.48 + 0.05")
                .contains("HOTSPOT_BREATH_MS")
                .contains("0.28 + 0.04")
                .contains("FIELD_BREATH_MS")
                .contains("0.88 + 0.24")
                .contains("0.85 + 0.30")
                .contains("LENS_BREATH_MS")
                .contains("0.88 + 0.24 * lensWave")
                .contains("0.85 + 0.30 * lensWave")
                .contains("CUTS_BREATH_MS")
                .contains("0.18 + 0.05")
                .contains("PLAYER_BREATH_MS")
                .contains("function walker")
                .contains("walkHead(scene.hardest.path, 1)")
                .contains("walkHead(scene.tourPath, 1)")
                .contains("endpoint(g, geom, {row: 0, col: 0}")
                .contains("VICTORY_BREATH_MS")
                .contains("0.85 + 0.08")
                .contains("rgba(245, 193, 74, \" + (0.04 + 0.03")
                .contains("data-key=\"path\"").contains("data-key=\"floor\"")
                .contains("data-key=\"fog\"")
                .contains("rgba(245, 193, 74, .35)")
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
