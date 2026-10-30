// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The naming convention shared by {@link PerKeyRateLimitInterceptor} (which composes per-key
 * instance names) and {@code ApiExceptionHandler} (which collapses them back to the base for the
 * 429 body). The round-trip is the contract: {@code baseOf(perKey(base, key)) == base}.
 */
class RateLimitNamingTest {

    @Test
    void perKey_joinsBaseAndKeyWithSeparator() {
        assertThat(RateLimitNaming.perKey("mazeGenerate", "ip:203.0.113.7"))
                .isEqualTo("mazeGenerate::ip:203.0.113.7");
    }

    @Test
    void baseOf_stripsTheKeySuffix() {
        assertThat(RateLimitNaming.baseOf("mazeGenerate::ip:203.0.113.7")).isEqualTo("mazeGenerate");
        assertThat(RateLimitNaming.baseOf("authLogin::sub:admin")).isEqualTo("authLogin");
    }

    @Test
    void baseOf_leavesPlainNamesUnchanged() {
        // Global (pre-per-key) instance names carry no separator and must pass through as-is,
        // so the handler stays correct for both old and new limiter names.
        assertThat(RateLimitNaming.baseOf("mazeGenerate")).isEqualTo("mazeGenerate");
        assertThat(RateLimitNaming.baseOf("ghost")).isEqualTo("ghost");
    }

    @Test
    void baseOf_isNullSafe() {
        assertThat(RateLimitNaming.baseOf(null)).isEqualTo("unknown");
    }

    @Test
    void baseOf_splitsOnFirstSeparator_soAKeyContainingItStillYieldsTheBase() {
        // A pathological key that itself contains "::" must not corrupt base recovery.
        assertThat(RateLimitNaming.baseOf(RateLimitNaming.perKey("mazeSolve", "sub:weird::name")))
                .isEqualTo("mazeSolve");
    }

    @Test
    void roundTrip_baseOfPerKey_returnsBase() {
        String base = "mazeGenerate";
        assertThat(RateLimitNaming.baseOf(RateLimitNaming.perKey(base, "ip:10.0.0.1"))).isEqualTo(base);
    }
}
