// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.Hotspot;
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
 * Crossbreeding (ADR-006 idea #5) and the spectator seam (idea #6) at the HTTP boundary.
 * The breeding <em>algorithm</em> is proven in {@code MazeBreederTest}; what matters here
 * is that a bred child is a first-class maze — cached, solvable, playable, breedable
 * again — and that a spectator can read a live session's state without touching it.
 * (Shared cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class BreedAndSpectateEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService gen;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void aBredChildIsAFirstClassSolvableMaze() throws Exception {
        UUID a = generate("recursive-backtracker", 13, 13, 1L);
        UUID b = generate("binary-tree", 13, 13, 2L);

        JsonNode child = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/breed?a=" + a + "&b=" + b + "&seed=99")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        UUID childId = UUID.fromString(child.get("id").asText());

        assertThat(child.get("generatorId").asText()).isEqualTo("crossbreed");
        assertThat(childId).isNotEqualTo(a).isNotEqualTo(b);

        // Cached like any generated maze, and genuinely solvable start→goal.
        MazeGrid grid = gen.find(childId).grid();
        assertThat(grid).isNotNull();
        assertThat(MazeMetrics.shortestPath(grid, grid.start(), grid.goal()))
                .as("a bred maze whose route didn't exist would be a broken deliverable")
                .isNotEmpty();
        client().post().uri("/api/v1/maze/" + childId + "/solve/bfs")
                .exchange().expectStatus().isOk();

        // Deterministic over HTTP, and lineage continues: breed the child with a parent.
        JsonNode again = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/breed?a=" + a + "&b=" + b + "&seed=99")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(again.get("tiles")).isEqualTo(child.get("tiles"));
        client().post().uri("/api/v1/maze/breed?a=" + childId + "&b=" + a)
                .exchange().expectStatus().isOk();
    }

    @Test
    void aBredChildInheritsParentHotspots() throws Exception {
        UUID a = generateWeighted("recursive-backtracker", 11, 11, 5L, 2, 2, 10);
        UUID b = generateWeighted("binary-tree", 11, 11, 6L, 4, 4, 25);

        JsonNode child = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/breed?a=" + a + "&b=" + b + "&seed=7")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(child.get("hotspots")).hasSize(2);
        UUID childId = UUID.fromString(child.get("id").asText());
        MazeGrid grid = gen.find(childId).grid();
        assertThat(grid.weightOf(new Point(2, 2))).isEqualTo(10.0);
        assertThat(grid.weightOf(new Point(4, 4))).isEqualTo(25.0);
    }

    @Test
    void overlappingParentHotspotsKeepTheHigherCost() {
        List<Hotspot> merged = MazeController.mergeParentHotspots(
                List.of(new Hotspot(1, 1, 10), new Hotspot(2, 2, 5)),
                List.of(new Hotspot(1, 1, 25), new Hotspot(3, 3, 8)));
        assertThat(merged).containsExactly(
                new Hotspot(1, 1, 25), new Hotspot(2, 2, 5), new Hotspot(3, 3, 8));
    }

    @Test
    void mismatchedParentsAre400AndUnknownParentsAre404() throws Exception {
        UUID big = generate("recursive-backtracker", 13, 13, 3L);
        UUID small = generate("recursive-backtracker", 7, 7, 4L);

        client().post().uri("/api/v1/maze/breed?a=" + big + "&b=" + small)
                .exchange().expectStatus().isBadRequest();
        client().post().uri("/api/v1/maze/breed?a=" + big + "&b=" + UUID.randomUUID())
                .exchange().expectStatus().isNotFound();
    }

    @Test
    void aSpectatorSeesLivePositionsWithoutTouchingTheSession() throws Exception {
        UUID id = generate("recursive-backtracker", 9, 9, 8L);
        MazeGrid grid = gen.find(id).grid();

        JsonNode session = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + id + "/session?player=runner")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        String sessionId = session.get("sessionId").asText();

        JsonNode before = MAPPER.readTree(client().get().uri("/api/v1/session/" + sessionId)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(before.get("mazeId").asText()).isEqualTo(id.toString());
        assertThat(before.get("player").asText()).isEqualTo("runner");
        assertThat(before.get("completed").asBoolean()).isFalse();
        assertThat(before.get("completedBy").isNull()).isTrue();
        assertThat(before.get("moveCount").asLong()).isZero();
        assertThat(before.get("players").get("runner")).isNotNull();
        assertThat(before.get("trail")).as("no hops before the first move").isEmpty();

        Point step = grid.openNeighbors(grid.start()).get(0);
        client().post().uri("/api/v1/session/" + sessionId + "/move")
                .header("Content-Type", "application/json")
                .body("{\"to\":{\"row\":" + step.row() + ",\"col\":" + step.col() + "}}")
                .exchange().expectStatus().isOk();

        JsonNode after = MAPPER.readTree(client().get().uri("/api/v1/session/" + sessionId)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(after.get("moveCount").asLong())
                .as("the spectator view tracks live play")
                .isEqualTo(1);
        assertThat(after.get("players").get("runner").get("row").asInt()).isEqualTo(step.row());
        assertThat(after.get("players").get("runner").get("col").asInt()).isEqualTo(step.col());
        assertThat(after.get("trail")).as("the snapshot carries the walk, not just the seat")
                .hasSize(1);
        assertThat(after.get("trail").get(0).get("to").get("row").asInt()).isEqualTo(step.row());
        assertThat(after.get("trail").get(0).get("to").get("col").asInt()).isEqualTo(step.col());
        assertThat(after.get("trail").get(0).has("tMs")).isTrue();
        assertThat(after.get("walks").get("runner")).as("the opener's walk is also under walks")
                .hasSize(1);

        // Reading a session must never advance it — the view is a snapshot, not a turn.
        MAPPER.readTree(client().get().uri("/api/v1/session/" + sessionId)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(MAPPER.readTree(client().get().uri("/api/v1/session/" + sessionId)
                .exchange().expectBody().returnResult().getResponseBody())
                .get("moveCount").asLong()).isEqualTo(1);

        client().get().uri("/api/v1/session/" + UUID.randomUUID())
                .exchange().expectStatus().isNotFound();
    }

    private UUID generate(String generator, int rows, int cols, long seed) throws Exception {
        JsonNode maze = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"" + generator + "\",\"rows\":" + rows
                        + ",\"cols\":" + cols + ",\"seed\":" + seed + "}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        return UUID.fromString(maze.get("id").asText());
    }

    private UUID generateWeighted(String generator, int rows, int cols, long seed,
                                  int row, int col, double cost) throws Exception {
        JsonNode maze = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"" + generator + "\",\"rows\":" + rows
                        + ",\"cols\":" + cols + ",\"seed\":" + seed
                        + ",\"hotspots\":[{\"row\":" + row + ",\"col\":" + col
                        + ",\"cost\":" + cost + "}]}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        return UUID.fromString(maze.get("id").asText());
    }
}
