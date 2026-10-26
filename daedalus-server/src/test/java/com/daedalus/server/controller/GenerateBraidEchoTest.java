// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Generate-time braid must survive the HTTP round-trip. The page used to
 * label Daily and a {@code #maze=} permalink from the leftover select;
 * {@code GET /maze/{id}} is what a permalink actually has.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class GenerateBraidEchoTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void generateEchoesBraidAndGetRepeatsIt_zeroOmitsTheField() throws Exception {
        JsonNode tree = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"recursive-backtracker\",\"rows\":11,\"cols\":11,"
                        + "\"seed\":7}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(tree.has("braid"))
                .as("zero must be omitted or every old client sees a new field of 0")
                .isFalse();

        JsonNode braided = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"recursive-backtracker\",\"rows\":11,\"cols\":11,"
                        + "\"seed\":7,\"braid\":0.8}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(braided.get("braid").asDouble()).isEqualTo(0.8);

        JsonNode fetched = MAPPER.readTree(client().get()
                .uri("/api/v1/maze/" + braided.get("id").asText())
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(fetched.get("braid").asDouble())
                .as("a permalink GET is the only fact #maze= has")
                .isEqualTo(0.8);
        assertThat(fetched.get("tiles").toString()).isEqualTo(braided.get("tiles").toString());

        client().post().uri("/api/v1/maze/" + braided.get("id").asText() + "/live?ticks=2")
                .exchange().expectStatus().isOk();
        JsonNode afterLive = MAPPER.readTree(client().get()
                .uri("/api/v1/maze/" + braided.get("id").asText())
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(afterLive.get("braid").asDouble())
                .as("a living tick must not forget how the maze was born")
                .isEqualTo(0.8);
    }
}
