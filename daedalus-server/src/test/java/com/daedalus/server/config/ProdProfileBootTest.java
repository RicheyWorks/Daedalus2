// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Boots the application under the <b>prod</b> profile — the one profile no test had ever
 * assembled (2026-07-29 config audit). Everything else in the suite runs under {@code test},
 * so a prod-only wiring break (a bean that only exists there, a property with no prod value,
 * two security chains colliding) would ship undetected and fail at the worst possible
 * moment: first production start.
 *
 * <p>The required env contract ({@code DAEDALUS_JWT_SECRET},
 * {@code DAEDALUS_ADMIN_PASSWORD_BCRYPT}) is satisfied with test values via properties, and
 * Redis is disabled — prod's default assumes a reachable Redis, which a unit-test JVM does
 * not have; {@code daedalus.redis.enabled} exists precisely for that.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.security.jwt.secret=prod-boot-test-secret-32-bytes-long!!",
        "daedalus.security.admin.password-bcrypt="
                + "$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
        "daedalus.redis.enabled=false",
        "daedalus.plugins.scan-on-startup=false",
})
@ActiveProfiles("prod")
class ProdProfileBootTest {

    @org.springframework.test.context.DynamicPropertySource
    static void isolateWorldStorage(org.springframework.test.context.DynamicPropertyRegistry registry) {
        com.daedalus.server.IsolatedWorldStorage.register(registry);
    }


    @LocalServerPort
    private int port;

    @Autowired
    private ApplicationContext context;

    @Test
    void productionProfileUsesAnEmptyIsolatedWorldDirectory() {
        var world = context.getBean(com.daedalus.server.service.WorldService.class);
        var directory = world.file().toAbsolutePath().getParent();
        assertThat(directory.getFileName().toString()).startsWith("daedalus-prod-test-");
        assertThat(java.nio.file.Files.isDirectory(directory)).isTrue();
        assertThat(context.getBean(com.daedalus.server.service.WorldHub.class).worlds())
                .extracting(com.daedalus.server.service.WorldHub.WorldEntry::id)
                .containsExactly("world-zero");
        assertThat(world.copy("world-zero").chunkCount()).isZero();
    }

    @Test
    void theProdContextAssemblesAndServes() {
        // Context assembly IS the test; the assertions below pin the prod posture on top.
        assertThat(context.containsBean("pluginManager")).isTrue();

        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();

        // Prod's actuator include-list: health is exposed…
        client.get().uri("/actuator/health").exchange().expectStatus().isOk();
        // …and the dev-only algorithms endpoint is not reachable — prod's security chain
        // answers 401 for unexposed actuator paths (auth before existence, which leaks less
        // than a 404 would). The assertion is the posture: never 200.
        client.get().uri("/actuator/algorithms").exchange().expectStatus().isUnauthorized();
    }
}
