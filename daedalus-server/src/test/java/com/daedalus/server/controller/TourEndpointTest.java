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

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Two first {@code GET /maze/{id}/tour?count=} used to each mint {@code mazeId:k}.
 * Progress then preferred the default count (or the first {@code asMap()} scan),
 * so pickups attached to the wrong coin set. (Shared cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class TourEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService gen;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void twoFirstToursAtDifferentCountsShareOnePlacementAndPickups() throws Exception {
        UUID id = generate(13, 13, 42L);
        MazeGrid grid = gen.find(id).grid();

        JsonNode session = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + id + "/session?player=hunter")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        String sessionId = session.get("sessionId").asText();

        JsonNode first = MAPPER.readTree(client()
                .get().uri("/api/v1/maze/" + id + "/tour?count=8")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        JsonNode later = MAPPER.readTree(client()
                .get().uri("/api/v1/maze/" + id + "/tour?count=5")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());

        List<Point> frozen = points(first.get("waypoints"));
        assertThat(points(later.get("waypoints")))
                .as("a later ?count= must not mint a second coin set")
                .isEqualTo(frozen);
        assertThat(frozen).hasSize(8);

        JsonNode before = MAPPER.readTree(client()
                .get().uri("/api/v1/session/" + sessionId + "/tour")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(before.get("total").asInt()).isEqualTo(8);
        assertThat(points(before.get("waypoints"))).isEqualTo(frozen);

        Point target = frozen.get(0);
        List<Point> route = MazeMetrics.shortestPath(grid, grid.start(), target);
        for (int i = 1; i < route.size(); i++) {
            client().post().uri("/api/v1/session/" + sessionId + "/move")
                    .header("Content-Type", "application/json")
                    .body("{\"to\":{\"row\":" + route.get(i).row()
                            + ",\"col\":" + route.get(i).col() + "}}")
                    .exchange().expectStatus().isOk();
        }

        JsonNode after = MAPPER.readTree(client()
                .get().uri("/api/v1/session/" + sessionId + "/tour")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        long onRoute = frozen.stream().filter(route::contains).count();
        assertThat(after.get("collected").asInt())
                .as("pickups attached to the default set, not the frozen hunt")
                .isEqualTo((int) onRoute);
        assertThat(points(after.get("remaining"))).doesNotContain(target);
        assertThat(after.get("total").asInt()).isEqualTo(8);
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

    private static List<Point> points(JsonNode array) {
        List<Point> out = new ArrayList<>();
        for (JsonNode n : array) {
            out.add(new Point(n.get("row").asInt(), n.get("col").asInt()));
        }
        return out;
    }
}
