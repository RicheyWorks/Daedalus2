// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.solver.solvers.BfsSolver;
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
 * The fog-of-war agent API at the HTTP seam (ADR-006 idea #7). Two contracts matter more
 * than any other: <b>the fog is absolute</b> — no agent response ever contains the grid —
 * and <b>a blind walk actually works over plain HTTP</b>, because "anything that can curl
 * can compete" is the feature. (Uses the shared cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class AgentApiEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService gen; // the test may peek at the grid; the agent never does

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void aWholeBlindWalkSucceedsOverHttp_andTheFogIsAbsolute() throws Exception {
        UUID mazeId = generate(9, 9, 21L);
        MazeGrid grid = gen.find(mazeId).grid();
        List<Point> path = new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

        String openBody = new String(client().post().uri("/api/v1/maze/" + mazeId + "/agent")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        JsonNode agent = MAPPER.readTree(openBody);
        assertThat(openBody).as("fog: the grid is never in an agent response")
                .doesNotContain("tiles");
        assertThat(agent.get("position").get("row").asInt()).isEqualTo(grid.start().row());
        String agentId = agent.get("agentId").asText();

        JsonNode view = agent;
        for (int i = 1; i < path.size(); i++) {
            Direction d = MazeGrid.directionBetween(path.get(i - 1), path.get(i));
            byte[] body = client().post()
                    .uri("/api/v1/agent/" + agentId + "/step?direction=" + d)
                    .exchange().expectStatus().isOk()
                    .expectBody().returnResult().getResponseBody();
            String json = new String(body);
            assertThat(json).doesNotContain("tiles"); // fog on every single response
            view = MAPPER.readTree(json);
        }

        assertThat(view.get("arrived").asBoolean())
                .as("a scripted walker reached the goal over nothing but HTTP")
                .isTrue();
        assertThat(view.get("stepsUsed").asInt()).isEqualTo(path.size() - 1);
    }

    @Test
    void wallBumpsAnswer400AndUnknownIdsAnswer404() throws Exception {
        UUID mazeId = generate(7, 7, 5L);
        MazeGrid grid = gen.find(mazeId).grid();

        JsonNode agent = MAPPER.readTree(client().post()
                .uri("/api/v1/maze/" + mazeId + "/agent?steps=10")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        String agentId = agent.get("agentId").asText();

        Direction blocked = null;
        for (Direction d : Direction.values()) {
            if (!grid.cell(grid.start()).isOpen(d)) { blocked = d; break; }
        }
        client().post().uri("/api/v1/agent/" + agentId + "/step?direction=" + blocked)
                .exchange().expectStatus().isBadRequest();
        client().post().uri("/api/v1/agent/" + agentId + "/step?direction=SIDEWAYS")
                .exchange().expectStatus().isBadRequest();
        client().post().uri("/api/v1/agent/" + UUID.randomUUID() + "/step?direction=NORTH")
                .exchange().expectStatus().isNotFound();
        client().get().uri("/api/v1/agent/" + UUID.randomUUID())
                .exchange().expectStatus().isNotFound();
        client().post().uri("/api/v1/maze/" + UUID.randomUUID() + "/agent")
                .exchange().expectStatus().isNotFound();
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
