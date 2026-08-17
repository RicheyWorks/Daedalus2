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
        // endpoint, can sign in (prod generate/play are 401 without a token), and can open
        // a fog-of-war walk. If any of those disappear, the UI broke or moved.
        assertThat(html).contains("DAEDALUS").contains("/api/v1").contains("/ws")
                .contains("/auth/login").contains("id=\"login\"").contains("id=\"fog\"")
                .contains("Authorization");
    }
}
