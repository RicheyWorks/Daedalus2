// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The replay surface end to end: {@code ?replay=true} ships the search's expansion order,
 * its absence keeps the response byte-compatible with the pre-replay shape (the field is
 * omitted, not null-valued — existing clients see the exact JSON they always did).
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class SolveReplayTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService gen;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    private JsonNode solve(String mazeId, String solverId, String query) throws Exception {
        byte[] body = client().post()
                .uri("/api/v1/maze/" + mazeId + "/solve/" + solverId + query)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        return MAPPER.readTree(body);
    }

    @Test
    void replayTrueShipsTheExpansionOrder() throws Exception {
        var cached = gen.generate("recursive-backtracker", 10, 14, 3L);
        JsonNode r = solve(cached.metadata().id().toString(), "bfs", "?replay=true");

        assertThat(r.get("success").asBoolean()).isTrue();
        assertThat(r.has("expansions")).isTrue();
        assertThat(r.get("expansions").size())
                .as("BFS expands at least as many cells as the path it found")
                .isGreaterThanOrEqualTo(r.get("path").size() - 1);
        // First expansion is the search origin — the animation's opening frame.
        assertThat(r.get("expansions").get(0).get("row").asInt())
                .isEqualTo(cached.grid().start().row());
        assertThat(r.get("expansions").get(0).get("col").asInt())
                .isEqualTo(cached.grid().start().col());
    }

    @Test
    void withoutReplayTheResponseShapeIsUnchanged() throws Exception {
        var cached = gen.generate("recursive-backtracker", 10, 14, 3L);
        JsonNode r = solve(cached.metadata().id().toString(), "bfs", "");
        assertThat(r.has("expansions"))
                .as("pre-replay clients must see the exact JSON they always did")
                .isFalse();
    }

    @Test
    void offSeamSolversReplayHonestlyEmpty() throws Exception {
        var cached = gen.generate("recursive-backtracker", 10, 14, 3L);
        JsonNode r = solve(cached.metadata().id().toString(), "wall-follower", "?replay=true");
        assertThat(r.has("expansions")).isTrue();
        assertThat(r.get("expansions").size())
                .as("no fake replays for solvers off the graph seam")
                .isZero();
    }
}
