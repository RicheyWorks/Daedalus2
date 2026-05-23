// SPDX-License-Identifier: MIT

package com.daedalus.server.web;

import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Direct unit test of {@link ApiExceptionHandler#onRateLimited}: when Resilience4j throws
 * {@link RequestNotPermitted}, the handler must produce a 429 response with a {@code Retry-After}
 * header and a {@code application/problem+json} body whose {@code limiter} property names the
 * exhausted instance.
 *
 * <p>We test the handler in isolation rather than going through the full AOP / MockMvc /
 * Spring Boot stack because (a) Resilience4j's {@code @RateLimiter} aspect is well-covered
 * upstream and (b) the contract under test here is purely how we map the resulting exception
 * to an HTTP response. Booting Spring just to drive a known-good aspect would be overkill.
 */
class ApiExceptionHandlerRateLimitTest {

    private final ApiExceptionHandler handler = new ApiExceptionHandler();

    @Test
    void onRateLimited_returns429_withRetryAfterHeader_andProblemDetailBody() {
        // The exception is a typed wrapper that pulls its message from the limiter's name,
        // so we don't need an actually-exhausted limiter to construct one — we just need
        // a valid instance with the right name. (Resilience4j 2.x rejects limit=0 at config
        // build time, so the "drain it to zero" approach doesn't work.)
        RateLimiter rl = RateLimiter.of("mazeGenerate",
                RateLimiterConfig.custom()
                        .limitForPeriod(1)
                        .limitRefreshPeriod(Duration.ofSeconds(1))
                        .timeoutDuration(Duration.ZERO)
                        .build());
        RequestNotPermitted ex = RequestNotPermitted.createRequestNotPermitted(rl);

        ResponseEntity<ProblemDetail> response = handler.onRateLimited(ex);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.TOO_MANY_REQUESTS);
        assertThat(response.getHeaders().getFirst(HttpHeaders.RETRY_AFTER)).isEqualTo("1");
        assertThat(response.getHeaders().getContentType())
                .isEqualTo(MediaType.APPLICATION_PROBLEM_JSON);

        ProblemDetail body = response.getBody();
        assertThat(body).isNotNull();
        assertThat(body.getStatus()).isEqualTo(429);
        assertThat(body.getTitle()).isEqualTo("Too many requests");
        assertThat(body.getProperties())
                .containsEntry("limiter", "mazeGenerate")
                .containsEntry("retryAfterSeconds", 1L);
    }

    @Test
    void onRateLimited_namesTheCorrectLimiter_whenAuthLoginIsExhausted() {
        // Sanity check that the limiter-name extraction works for any instance name —
        // not just the one that happens to come first alphabetically.
        RateLimiter rl = RateLimiter.of("authLogin",
                RateLimiterConfig.custom()
                        .limitForPeriod(1)
                        .limitRefreshPeriod(Duration.ofSeconds(1))
                        .timeoutDuration(Duration.ZERO)
                        .build());
        RequestNotPermitted ex = RequestNotPermitted.createRequestNotPermitted(rl);

        ResponseEntity<ProblemDetail> response = handler.onRateLimited(ex);

        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getProperties()).containsEntry("limiter", "authLogin");
    }

    // ---------- registry-aware Retry-After ----------

    @Test
    void onRateLimited_withRegistry_usesActualRefreshPeriodAsRetryAfter() {
        // When Resilience4j Spring Boot autowires a RateLimiterRegistry (the production
        // path), the handler should report the limiter's actual limit-refresh-period as
        // the worst-case Retry-After bound, not the 1-second fallback.
        RateLimiterConfig oneMinute = RateLimiterConfig.custom()
                .limitForPeriod(1)
                .limitRefreshPeriod(Duration.ofMinutes(1))
                .timeoutDuration(Duration.ZERO)
                .build();
        RateLimiterRegistry registry = RateLimiterRegistry.ofDefaults();
        registry.rateLimiter("mazeGenerate", oneMinute);

        ApiExceptionHandler registryAware = new ApiExceptionHandler(registry);
        RequestNotPermitted ex = RequestNotPermitted.createRequestNotPermitted(
                registry.rateLimiter("mazeGenerate"));

        ResponseEntity<ProblemDetail> response = registryAware.onRateLimited(ex);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.TOO_MANY_REQUESTS);
        assertThat(response.getHeaders().getFirst(HttpHeaders.RETRY_AFTER)).isEqualTo("60");
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getProperties())
                .containsEntry("limiter", "mazeGenerate")
                .containsEntry("retryAfterSeconds", 60L);
    }

    @Test
    void onRateLimited_withRegistry_roundsSubSecondRefreshUpToOne() {
        // A 250ms refresh period would truncate to 0 with naive toMillis()/1000; the
        // RFC requires Retry-After >= 1, and our handler floors to 1 to honor that.
        RateLimiterConfig fastBurst = RateLimiterConfig.custom()
                .limitForPeriod(1)
                .limitRefreshPeriod(Duration.ofMillis(250))
                .timeoutDuration(Duration.ZERO)
                .build();
        RateLimiterRegistry registry = RateLimiterRegistry.ofDefaults();
        registry.rateLimiter("mazeGenerate", fastBurst);

        ApiExceptionHandler registryAware = new ApiExceptionHandler(registry);
        RequestNotPermitted ex = RequestNotPermitted.createRequestNotPermitted(
                registry.rateLimiter("mazeGenerate"));

        ResponseEntity<ProblemDetail> response = registryAware.onRateLimited(ex);

        assertThat(response.getHeaders().getFirst(HttpHeaders.RETRY_AFTER)).isEqualTo("1");
        assertThat(response.getBody().getProperties()).containsEntry("retryAfterSeconds", 1L);
    }

    @Test
    void onRateLimited_withRegistry_butLimiterNotRegistered_fallsBackToOne() {
        // Defensive: registry was injected but doesn't know the limiter name on the
        // exception. We don't want one misconfigured limiter to make the 429 itself fail —
        // fall back to the 1s floor so the client at least gets a parseable response.
        RateLimiterRegistry empty = RateLimiterRegistry.ofDefaults();
        ApiExceptionHandler registryAware = new ApiExceptionHandler(empty);

        RateLimiter loose = RateLimiter.of("ghost",
                RateLimiterConfig.custom()
                        .limitForPeriod(1)
                        .limitRefreshPeriod(Duration.ofMinutes(5))
                        .timeoutDuration(Duration.ZERO)
                        .build());
        RequestNotPermitted ex = RequestNotPermitted.createRequestNotPermitted(loose);

        ResponseEntity<ProblemDetail> response = registryAware.onRateLimited(ex);

        assertThat(response.getHeaders().getFirst(HttpHeaders.RETRY_AFTER)).isEqualTo("1");
        assertThat(response.getBody().getProperties())
                .containsEntry("limiter", "ghost")     // name still surfaces from the message
                .containsEntry("retryAfterSeconds", 1L);
    }
}
