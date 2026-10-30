// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks a controller handler method for <em>per-key</em> rate limiting.
 *
 * <p>Unlike Resilience4j's {@code @RateLimiter}, which is method-scoped (one bucket shared
 * across every caller), this annotation tells {@link PerKeyRateLimitInterceptor} to resolve a
 * caller key off the request (authenticated subject, else client IP — see
 * {@link RateLimitKeyResolver}) and throttle each key independently against its own bucket.
 *
 * <p>The {@link #value()} names a Resilience4j rate-limiter <em>instance</em> configured under
 * {@code resilience4j.ratelimiter.instances.<name>} in the active profile's YAML. That instance
 * supplies the limit / refresh-period / timeout template; per-key buckets are cloned from it on
 * first use. The name must match an existing instance, otherwise a default (effectively
 * unlimited) config is used.
 *
 * <p>When a per-key bucket is exhausted the interceptor throws
 * {@link io.github.resilience4j.ratelimiter.RequestNotPermitted}, which
 * {@code ApiExceptionHandler} translates to {@code 429 Too Many Requests}. The response body's
 * {@code limiter} property reports the base instance name (e.g. {@code mazeGenerate}), never the
 * caller key, so the wire contract is identical to the old global limiter and no client IP or
 * subject leaks into the response.
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface PerKeyRateLimit {

    /**
     * Name of the Resilience4j rate-limiter instance whose config templates the per-key buckets.
     * Must match a {@code resilience4j.ratelimiter.instances.<name>} key.
     */
    String value();
}
