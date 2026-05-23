// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Profile;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Locks in the {@code @Profile} split: {@link SecurityConfig} runs everywhere except
 * {@code prod}, {@link ProdSecurityConfig} runs only when {@code prod} is active. The two
 * are intentionally mutually exclusive — Spring's filter-chain wiring expects exactly one
 * {@code SecurityFilterChain} bean from this package.
 *
 * <p>We assert the annotations directly rather than booting a Spring context, because
 * {@code @EnableWebSecurity} drags in the full {@code HttpSecurity} chain which needs a
 * real Spring Boot environment to wire up. The annotations are the contract; if they're
 * right, Spring will pick the right config at runtime.
 */
class SecurityConfigProfileTest {

    @Test
    void devSecurityConfig_isActiveOnAllProfilesExceptProd() {
        Profile profile = SecurityConfig.class.getAnnotation(Profile.class);
        assertThat(profile)
                .as("SecurityConfig must carry a @Profile annotation so it doesn't collide with ProdSecurityConfig")
                .isNotNull();
        assertThat(profile.value())
                .as("dev / non-prod chain")
                .containsExactly("!prod");
    }

    @Test
    void prodSecurityConfig_isActiveOnlyOnProdProfile() {
        Profile profile = ProdSecurityConfig.class.getAnnotation(Profile.class);
        assertThat(profile)
                .as("ProdSecurityConfig must carry a @Profile annotation")
                .isNotNull();
        assertThat(profile.value())
                .as("prod chain — locked-down posture")
                .containsExactly("prod");
    }

    @Test
    void profileAnnotations_areMutuallyExclusive() {
        // Belt and braces: if the two annotations don't partition the profile space, both
        // SecurityFilterChain beans could activate and Spring would fail at boot.
        String dev = SecurityConfig.class.getAnnotation(Profile.class).value()[0];
        String prod = ProdSecurityConfig.class.getAnnotation(Profile.class).value()[0];

        assertThat(dev).isEqualTo("!prod");
        assertThat(prod).isEqualTo("prod");
    }
}
