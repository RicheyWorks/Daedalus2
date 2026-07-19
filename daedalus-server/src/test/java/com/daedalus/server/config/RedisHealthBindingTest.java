// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Pins the <em>other half</em> of the Redis health fix.
 *
 * <p>{@code application.yml} sets {@code management.health.redis.enabled} to
 * {@code ${daedalus.redis.enabled:false}} so that a deployment which deliberately runs without
 * Redis doesn't report itself DOWN. The obvious way for that to rot is for someone to
 * "simplify" the placeholder to a literal {@code false} — which would silence Redis
 * monitoring in production, where Redis genuinely is required, and do it silently.
 *
 * <p>This test therefore asserts the binding rather than the disable: flip
 * {@code daedalus.redis.enabled} on and the indicator must come back. Its <em>status</em> is
 * not asserted (no Redis is running in CI, so it will be DOWN) — only that the component is
 * registered and being evaluated.
 *
 * @see com.daedalus.server.ApplicationSmokeTest for the disabled direction
 */
@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {
                "daedalus.redis.enabled=true",
                "management.endpoint.health.show-details=always",
                // Fail fast instead of waiting on a connect timeout — nothing is listening.
                "spring.data.redis.host=127.0.0.1",
                "spring.data.redis.port=63799"
        })
@ActiveProfiles("test")
class RedisHealthBindingTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Test
    void whenRedisEnabled_theHealthIndicatorIsRegisteredAgain() throws Exception {
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port)
                .build();

        // Status will be 503 here precisely *because* the indicator is doing its job against a
        // Redis that isn't there. Read the body regardless of status.
        byte[] raw = client.get().uri("/actuator/health")
                .exchange()
                .expectBody()
                .returnResult()
                .getResponseBody();
        assertThat(raw).isNotNull();

        JsonNode components = MAPPER.readTree(new String(raw, StandardCharsets.UTF_8))
                .path("components");
        assertThat(components.has("redis"))
                .as("management.health.redis.enabled must track daedalus.redis.enabled, "
                        + "not be hard-coded off — otherwise prod loses Redis monitoring")
                .isTrue();
    }
}
