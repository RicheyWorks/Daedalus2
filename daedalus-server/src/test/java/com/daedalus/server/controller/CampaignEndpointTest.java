// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The campaign endpoint, and the claim that matters about it: a campaign is a table of
 * contents over endpoints that already exist. So this test walks a stage the way a client
 * does — take the stage's {@code mazeId}, then load, play, and score it through the ordinary
 * maze API — rather than checking that a JSON shape came back. (Shared cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class CampaignEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    private JsonNode campaign(String query) throws Exception {
        return MAPPER.readTree(client().get().uri("/api/v1/campaign" + query)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
    }

    @Test
    void aCampaignStageIsPlayableThroughTheOrdinaryMazeApi() throws Exception {
        JsonNode c = campaign("?seed=2024");
        JsonNode stage = c.get("stages").get(0);
        UUID mazeId = UUID.fromString(stage.get("mazeId").asText());

        // The stage reports the measurements behind its placement, not just a difficulty word.
        assertThat(stage.get("grade").get("score").asDouble()).isPositive();
        assertThat(stage.get("grade").get("routeLength").asInt()).isPositive();
        assertThat(stage.get("grade").get("label").asText()).isNotBlank();
        assertThat(stage.get("hazards")).isEmpty(); // first rung carries none

        // Load it, play it to the goal, and it lands on that stage's OWN leaderboard —
        // the per-maze partition from the earlier batch, composing for free.
        JsonNode maze = MAPPER.readTree(client().get().uri("/api/v1/maze/" + mazeId)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(maze.get("rows").asInt()).isEqualTo(stage.get("rows").asInt());

        JsonNode route = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + mazeId + "/solve/bfs")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        JsonNode session = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + mazeId + "/session?player=campaigner")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        String sessionId = session.get("sessionId").asText();
        for (int i = 1; i < route.get("path").size(); i++) {
            JsonNode step = route.get("path").get(i);
            client().post().uri("/api/v1/session/" + sessionId + "/move")
                    .header("Content-Type", "application/json")
                    .body("{\"to\":{\"row\":" + step.get("row").asInt()
                            + ",\"col\":" + step.get("col").asInt() + "}}")
                    .exchange().expectStatus().isOk();
        }

        JsonNode board = MAPPER.readTree(client()
                .get().uri("/api/v1/leaderboard?n=5&maze=" + mazeId)
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(board).hasSize(1);
        assertThat(board.get(0).get("playerName").asText()).isEqualTo("campaigner");

        // And the run became this stage's ghost — every stage gets a record holder for free.
        JsonNode ghost = MAPPER.readTree(client().get().uri("/api/v1/maze/" + mazeId + "/ghost")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(ghost.get("playerName").asText()).isEqualTo("campaigner");
    }

    @Test
    void theSameSeedServesTheSameLadderAndTheDefaultIsTodays() throws Exception {
        JsonNode first = campaign("?seed=555");
        JsonNode again = campaign("?seed=555");
        assertThat(again).isEqualTo(first); // ids included: the plan is cached, not replanned

        JsonNode today = campaign("");
        assertThat(today.get("seed").asLong())
                .isEqualTo(java.time.LocalDate.now(java.time.ZoneOffset.UTC).toEpochDay());

        // Later stages declare hazards; the endpoint must not have started them (the stage's
        // maze is still solvable and unmutated — a running erosion ticker would change it).
        JsonNode last = first.get("stages").get(first.get("stages").size() - 1);
        assertThat(last.get("hazards").toString()).contains("living", "traffic");
        client().post().uri("/api/v1/maze/" + last.get("mazeId").asText() + "/solve/bfs")
                .exchange().expectStatus().isOk();
    }
}
