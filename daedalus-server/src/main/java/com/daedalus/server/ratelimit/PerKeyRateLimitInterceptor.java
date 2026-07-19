// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * Enforces {@link PerKeyRateLimit} on annotated controller methods with per-caller buckets.
 *
 * <p>For each request whose handler carries {@link PerKeyRateLimit}, this interceptor:
 * <ol>
 *   <li>resolves a caller key ({@code sub:<subject>} or {@code ip:<addr>}) via
 *       {@link RateLimitKeyResolver};</li>
 *   <li>looks up (creating on first use) a Resilience4j instance named
 *       {@code <base>::<key>}, cloned from the configured base instance's limit / refresh /
 *       timeout template; and</li>
 *   <li>acquires a permit. When the bucket is empty, {@link RateLimiter#waitForPermission}
 *       throws {@link RequestNotPermitted} — the same exception the old method-scoped
 *       {@code @RateLimiter} aspect raised — so {@code ApiExceptionHandler} maps it to
 *       {@code 429 Too Many Requests} unchanged.</li>
 * </ol>
 *
 * <p>Because throttling happens in {@code preHandle} (before the controller body runs), a
 * rejected call never touches the service layer.
 *
 * <p><b>Bucket lifetime.</b> Per-key instances accumulate in the registry — one per distinct
 * subject or IP — and are not evicted. For this service the live key set is small (a handful of
 * authenticated subjects; login is IP-keyed), so unbounded growth is acceptable. A future
 * eviction strategy (e.g. a Caffeine-backed registry or a scheduled purge of idle instances) is
 * noted in BACKLOG.md.
 */
public class PerKeyRateLimitInterceptor implements HandlerInterceptor {

    private final RateLimiterRegistry registry;
    private final RateLimitKeyResolver keyResolver;

    public PerKeyRateLimitInterceptor(RateLimiterRegistry registry, RateLimitKeyResolver keyResolver) {
        this.registry = registry;
        this.keyResolver = keyResolver;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        if (!(handler instanceof HandlerMethod handlerMethod)) {
            // Static resources, error dispatches, etc. — nothing to throttle.
            return true;
        }
        PerKeyRateLimit annotation = handlerMethod.getMethodAnnotation(PerKeyRateLimit.class);
        if (annotation == null) {
            return true;
        }

        String base = annotation.value();
        String key = keyResolver.resolve(request);
        RateLimiter bucket = registry.rateLimiter(
                RateLimitNaming.perKey(base, key),
                // Clone the configured base instance's template. rateLimiter(base) returns the
                // YAML-provisioned instance; the per-key instance is created from its config on
                // first use and returned as-is on every subsequent call for the same key.
                registry.rateLimiter(base).getRateLimiterConfig());

        RateLimiter.waitForPermission(bucket);
        return true;
    }
}
