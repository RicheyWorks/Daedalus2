// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every {@code @PerKeyRateLimit} annotation names a template instance the interceptor clones
 * per caller — a name with no configured instance fails at request time, not boot time, which
 * is exactly the kind of yml-drift a test should catch instead of a user. This pins the full
 * set; adding an annotation without its yml instance breaks here first. (Uses the shared
 * cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class RateLimiterTemplatesTest {

    @LocalServerPort
    private int port; // matches the shared context configuration so it is reused

    @Autowired
    private RateLimiterRegistry registry;

    @Test
    void everyAnnotatedBudgetHasAConfiguredTemplate() {
        // Boot's resilience4j auto-config eagerly creates one RateLimiter per configured
        // instance, so presence in the registry IS the proof the yml instance exists —
        // find() never creates, unlike rateLimiter(name).
        assertThat(registry.find("mazeGenerate")).isPresent();
        assertThat(registry.find("mazeSolve")).isPresent();
        assertThat(registry.find("authLogin")).isPresent();
        assertThat(registry.find("sessionOpen"))
                .as("the 2026-07-29 audit's new budget must be configured in every profile "
                        + "that the base yml serves")
                .isPresent();
        assertThat(registry.find("mazeLive"))
                .as("ADR-006's living-maze budget — @PerKeyRateLimit(\"mazeLive\") on "
                        + "POST /maze/{id}/live fails at request time without it")
                .isPresent();
    }
}
