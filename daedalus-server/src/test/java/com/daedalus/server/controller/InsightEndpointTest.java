// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.theory.MazeMetrics;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The insight surface (ADR-006 ideas #8 and #9) at the HTTP seam: analysis reports the
 * graph truths every perfect maze must satisfy (cut size exactly 1 — a spanning tree
 * severs on any route passage), and a ghost exists precisely after a completed run and
 * replays that run's timed steps. (Shared cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class InsightEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService gen;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void aPerfectMazeAnalyzesToExactlyOneChokepoint() throws Exception {
        UUID id = generate(11, 11, 42L);
        MazeGrid grid = gen.find(id).grid();

        JsonNode a = MAPPER.readTree(client().get().uri("/api/v1/maze/" + id + "/analysis")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());

        assertThat(a.get("cutSize").asInt())
                .as("a spanning tree's start↔goal edge connectivity is exactly 1")
                .isEqualTo(1);
        assertThat(a.get("chokepoints")).hasSize(1);
        assertThat(a.get("deadEndCount").asInt()).isGreaterThan(0);
        assertThat(a.get("routeLength").asInt())
                .isEqualTo(MazeMetrics.shortestPath(grid, grid.start(), grid.goal()).size());

        client().get().uri("/api/v1/maze/" + UUID.randomUUID() + "/analysis")
                .exchange().expectStatus().isNotFound();
    }

    @Test
    void aGhostExistsExactlyAfterACompletedRunAndReplaysIt() throws Exception {
        UUID id = generate(7, 7, 5L);
        client().get().uri("/api/v1/maze/" + id + "/ghost")
                .exchange().expectStatus().isNotFound(); // nobody has finished yet

        // Complete a run over plain HTTP, driving the session along the true route.
        MazeGrid grid = gen.find(id).grid();
        JsonNode session = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + id + "/session?player=speedrunner")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        String sessionId = session.get("sessionId").asText();
        List<Point> path = MazeMetrics.shortestPath(grid, grid.start(), grid.goal());
        for (int i = 1; i < path.size(); i++) {
            client().post().uri("/api/v1/session/" + sessionId + "/move")
                    .header("Content-Type", "application/json")
                    .body("{\"to\":{\"row\":" + path.get(i).row()
                            + ",\"col\":" + path.get(i).col() + "}}")
                    .exchange().expectStatus().isOk();
        }

        JsonNode ghost = MAPPER.readTree(client().get().uri("/api/v1/maze/" + id + "/ghost")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(ghost.get("playerName").asText()).isEqualTo("speedrunner");
        assertThat(ghost.get("moves")).hasSize(path.size() - 1);
        JsonNode last = ghost.get("moves").get(path.size() - 2).get("to");
        assertThat(new Point(last.get("row").asInt(), last.get("col").asInt()))
                .as("the recording ends on the goal")
                .isEqualTo(grid.goal());
    }

    private UUID generate(int rows, int cols, long seed) throws Exception {
        JsonNode maze = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"recursive-backtracker\",\"rows\":" + rows
                        + ",\"cols\":" + cols + ",\"seed\":" + seed + "}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        return UUID.fromString(maze.get("id").asText());
    }
}
