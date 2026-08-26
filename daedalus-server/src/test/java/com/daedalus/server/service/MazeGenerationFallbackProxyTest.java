// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The reflection test on {@code fallback} never asks the Spring proxy. Self-invocation
 * inside {@code fallback} is intentional (an open breaker must not recurse), but a
 * miswired Resilience4j aspect would 500 instead of degrade. This drives
 * {@code POST /api/v1/maze/generate} through the bean the controller injects.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class MazeGenerationFallbackProxyTest {

    private static final String EXPLODING = "exploding-proxy-it";
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private MazeGenerationService generation;

    @Autowired
    private GeneratorRegistry generators;

    @Autowired
    private CircuitBreakerRegistry breakers;

    @AfterEach
    void dropTheExplodingGeneratorAndCloseTheBreaker() {
        if (generators.find(EXPLODING).isPresent()) {
            generators.unregister(EXPLODING);
        }
        breakers.circuitBreaker("generation").transitionToClosedState();
    }

    @Test
    void generateThroughTheProxyFallsBackToBinaryTree() throws Exception {
        assertThat(AopUtils.isAopProxy(generation))
                .as("the controller's MazeGenerationService is not a Spring proxy, so "
                        + "@CircuitBreaker never runs")
                .isTrue();

        generators.register(new MazeGenerator() {
            @Override public String id() { return EXPLODING; }
            @Override public String displayName() { return "Exploding"; }
            @Override public AlgorithmDescriptor descriptor() {
                return new AlgorithmDescriptor(EXPLODING, "Exploding", "generator",
                        "O(1)", "none", "throws so the generation breaker can degrade");
            }
            @Override public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
                throw new IllegalStateException("generator exploded on purpose");
            }
        });

        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();
        JsonNode body = MAPPER.readTree(client.post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"" + EXPLODING + "\",\"rows\":9,\"cols\":9,\"seed\":3}")
                .exchange()
                .expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());

        assertThat(body.get("generatorId").asText())
                .as("open-breaker / generator failure must 200 the binary-tree recovery, "
                        + "not the requested id and not a 500")
                .isEqualTo("binary-tree");
        assertThat(body.get("rows").asInt()).isEqualTo(9);
        assertThat(body.get("cols").asInt()).isEqualTo(9);
        assertThat(body.get("seed").asLong()).isEqualTo(3L);

        CircuitBreaker breaker = breakers.circuitBreaker("generation");
        assertThat(breaker.getState())
                .as("one recorded failure must not leave the shared test breaker open")
                .isNotEqualTo(CircuitBreaker.State.OPEN);
    }
}
