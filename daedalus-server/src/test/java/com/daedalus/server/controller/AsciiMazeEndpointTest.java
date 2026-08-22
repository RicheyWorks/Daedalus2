// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.service.MazeGenerationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code GET /maze/{id}} negotiated as {@code text/plain} — the core ASCII visualizer on the
 * product surface. Content negotiation is the wiring under test: the same URL keeps answering
 * JSON to JSON clients (pinned last, in the same test, so a broken produces-clause cannot
 * hide). Uses the shared cached context.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class AsciiMazeEndpointTest {

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService gen;

    @Test
    void theSameUrlServesAsciiToTerminalsAndJsonToClients() {
        var cached = gen.generate("dungeon", 12, 17, 7L);
        String id = cached.metadata().id().toString();
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();

        byte[] dump = client.get().uri("/api/v1/maze/" + id)
                .header("Accept", "text/plain")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        String bare = new String(dump);
        assertThat(bare).contains("#").contains("S").contains("G")
                .as("a dump without ?solve= is the maze, not a route").doesNotContain(".");
        assertThat(bare).as("no JSON leaked into the art").doesNotContain("{");

        byte[] plain = client.get().uri("/api/v1/maze/" + id + "?solve=bfs")
                .header("Accept", "text/plain")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        String art = new String(plain);
        assertThat(art).contains("#").contains("S").contains("G")
                .as("the solve overlay renders as path glyphs").contains(".");
        assertThat(art).as("no JSON leaked into the art").doesNotContain("{");

        byte[] json = client.get().uri("/api/v1/maze/" + id)
                .header("Accept", "application/json")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        assertThat(new String(json)).startsWith("{").contains("\"tiles\"");
    }
}
