// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.server.health.PluginSubsystemHealthIndicator;
import com.daedalus.solver.solvers.SolverRegistry;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Full-context smoke test — the only test in the suite that boots the real application on a
 * real port.
 *
 * <h3>Why this exists</h3>
 *
 * <p>Every other server test is a <em>slice</em>: {@code @WebMvcTest} for the controllers,
 * {@code ApplicationContextRunner} for {@code RedisConfig}. Slices are fast and precise, but
 * they share a blind spot — they never assemble the whole context, and they never touch
 * anything a starter contributes for free. The Spring Boot 3 to 4 migration made that
 * concrete: springdoc went from 2.6.0 to 3.0.3, a major version, and the entire suite stayed
 * green without a single test having ever requested {@code /v3/api-docs}. A broken OpenAPI
 * document would have shipped behind 267 passing tests.
 *
 * <p>It earned its keep immediately. The first run failed on {@code /actuator/health}, which
 * answered <b>503</b>: {@code spring-boot-starter-data-redis} is always on the classpath, so
 * Boot contributed a Redis health indicator even with {@code daedalus.redis.enabled=false},
 * and its failed PING dragged the aggregate status to DOWN. Since {@code dev} is the default
 * profile and sets that flag false, <em>anyone who cloned the repo and ran it</em> had an app
 * that reported itself unhealthy while working perfectly — the exact signal a load balancer
 * or Kubernetes readiness probe uses to pull an instance out of rotation. No slice test could
 * have seen it. Fixed in {@code application.yml}; see {@code RedisHealthBindingTest} for the
 * other direction.
 *
 * <h3>Note on the HTTP client</h3>
 *
 * <p>This uses {@link RestTestClient} (Spring Framework 7) rather than the
 * {@code TestRestTemplate} a Boot 3 codebase would reach for: Boot 4 removed
 * {@code TestRestTemplate} from {@code spring-boot-test} entirely. {@code WebTestClient} is
 * the other option but drags in {@code spring-webflux}, which this module deliberately does
 * not depend on.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class ApplicationSmokeTest {

    /**
     * Endpoints whose presence in the generated document is part of the public contract.
     * Deliberately a subset, not an exact-count assertion — adding a new endpoint should not
     * fail this test, but silently losing one of these should.
     */
    private static final List<String> CONTRACT_PATHS = List.of(
            "/api/v1/maze/generate",
            "/api/v1/maze/{id}",
            "/api/v1/maze/{id}/solve/{solverId}",
            "/api/v1/auth/login",
            "/api/v1/plugins");

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private ApplicationContext context;

    private RestTestClient client;

    @BeforeEach
    void bindToRunningServer() {
        client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port)
                .build();
    }

    @Test
    void contextLoads_withTheEngineRegistriesWired() {
        // If component scanning across module boundaries ever breaks (scanBasePackages =
        // "com.daedalus" reaching into daedalus-core), this is what catches it.
        assertThat(context.getBean(GeneratorRegistry.class).all()).isNotEmpty();
        assertThat(context.getBean(SolverRegistry.class).all()).isNotEmpty();
    }

    @Test
    void actuatorHealth_reportsUp() {
        assertThat(readTree(getBody("/actuator/health")).path("status").asText()).isEqualTo("UP");
    }

    @Test
    void pluginHealthIndicatorIsRegistered_andDoesNotDragTheAggregateDown() {
        // A unit test can prove the indicator returns UP; only a booted context proves Spring
        // ever built one. Asserted through the context rather than the endpoint payload,
        // because component detail is hidden by default and a test that tolerates its absence
        // would assert nothing.
        assertThat(context.getBeansOfType(PluginSubsystemHealthIndicator.class))
                .as("the indicator must actually be contributed to actuator health")
                .isNotEmpty();

        // And with it contributing, the aggregate is still UP — the property that keeps a
        // broken optional plugin from pulling the instance out of rotation.
        assertThat(readTree(getBody("/actuator/health")).path("status").asText()).isEqualTo("UP");
    }

    @Test
    void openApiDocument_isServedAndCoversTheContractEndpoints() {
        JsonNode doc = readTree(getBody("/v3/api-docs"));

        // springdoc 3 emits OpenAPI 3.1.0 where 2.x emitted 3.0.x. Assert the major version
        // only: the minor is springdoc's to choose, but a 2.x document would mean something
        // has gone badly wrong.
        assertThat(doc.path("openapi").asText()).startsWith("3.");

        JsonNode paths = doc.path("paths");
        assertThat(paths.isObject()).as("document must contain a paths object").isTrue();

        List<String> documented = new ArrayList<>();
        paths.fieldNames().forEachRemaining(documented::add);
        assertThat(documented)
                .as("generated OpenAPI document must cover the contract endpoints")
                .containsAll(CONTRACT_PATHS);
    }

    @Test
    void swaggerUi_isServed() {
        // The UI is a webjar served by the starter — a separate failure mode from the JSON
        // document, and the one most likely to break on a springdoc major bump.
        client.get().uri("/swagger-ui/index.html").exchange().expectStatus().isOk();
    }

    private String getBody(String uri) {
        byte[] body = client.get().uri(uri)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .returnResult()
                .getResponseBody();
        assertThat(body).as("response body for %s", uri).isNotNull();
        return new String(body, StandardCharsets.UTF_8);
    }

    private static JsonNode readTree(String json) {
        try {
            return MAPPER.readTree(json);
        } catch (Exception e) {
            throw new AssertionError("response was not valid JSON: " + json, e);
        }
    }
}
