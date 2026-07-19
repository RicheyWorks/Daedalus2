// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Expiry;
import com.github.benmanes.caffeine.cache.Ticker;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.time.Duration;

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
 * <h3>Bucket lifetime — bounded, and why evicting is not a bypass</h3>
 *
 * <p>Per-key buckets used to accumulate in the {@link RateLimiterRegistry} and were never
 * evicted, so a caller able to mint distinct keys — many forged subjects, or many source IPs
 * when {@code daedalus.ratelimit.trust-forwarded-header} is on — could grow the registry without
 * limit. Buckets now live in a Caffeine cache bounded by
 * {@code daedalus.ratelimit.max-keys} and expiring on
 * {@code daedalus.ratelimit.idle-ttl}.
 *
 * <p>The subtle part is that eviction can itself <b>defeat</b> a rate limit. Throwing away a
 * bucket that a caller has already drained hands that caller a full budget the moment they
 * return: cycle keys fast enough to force eviction and the limit stops applying. So the
 * effective TTL for each bucket is raised to at least its own
 * {@code limitRefreshPeriod} — past that point the bucket would have refilled anyway, and
 * discarding it is indistinguishable from keeping it. The per-entry {@link Expiry} below is
 * what enforces that; a single cache-wide {@code expireAfterAccess} could not, because
 * different base limiters configure different refresh periods.
 *
 * <p>Size-based eviction keeps the same property in the case that matters. Caffeine evicts
 * approximately least-recently-used, so under a key-flood attack the entries discarded are the
 * attacker's own idle ones rather than an active caller's drained bucket. The memory ceiling is
 * therefore bought without weakening the limit for real traffic.
 */
public class PerKeyRateLimitInterceptor implements HandlerInterceptor {

    private final RateLimiterRegistry registry;
    private final RateLimitKeyResolver keyResolver;
    private final Cache<String, RateLimiter> buckets;

    public PerKeyRateLimitInterceptor(RateLimiterRegistry registry, RateLimitKeyResolver keyResolver) {
        this(registry, keyResolver, 10_000, Duration.ofMinutes(10));
    }

    public PerKeyRateLimitInterceptor(RateLimiterRegistry registry, RateLimitKeyResolver keyResolver,
                                      int maxKeys, Duration idleTtl) {
        this(registry, keyResolver, maxKeys, idleTtl, Ticker.systemTicker());
    }

    /**
     * Time-controllable form, for tests. Expiry is inherently a function of the clock, and a
     * test that sleeps to observe it is both slow and flaky on a loaded CI box; injecting a
     * ticker makes the eviction rules assertable exactly.
     */
    PerKeyRateLimitInterceptor(RateLimiterRegistry registry, RateLimitKeyResolver keyResolver,
                               int maxKeys, Duration idleTtl, Ticker ticker) {
        this.registry = registry;
        this.keyResolver = keyResolver;
        this.buckets = Caffeine.newBuilder()
                .maximumSize(maxKeys)
                .expireAfter(new IdleButNeverBeforeRefill(idleTtl))
                .ticker(ticker)
                .build();
    }

    /**
     * Keeps a bucket for {@code idleTtl}, but never for less than the bucket's own refresh
     * period — otherwise evicting a drained bucket would reset its owner's budget early.
     */
    private static final class IdleButNeverBeforeRefill implements Expiry<String, RateLimiter> {

        private final Duration idleTtl;

        IdleButNeverBeforeRefill(Duration idleTtl) {
            this.idleTtl = idleTtl;
        }

        private long nanos(RateLimiter bucket) {
            Duration refill = bucket.getRateLimiterConfig().getLimitRefreshPeriod();
            return (refill.compareTo(idleTtl) > 0 ? refill : idleTtl).toNanos();
        }

        @Override
        public long expireAfterCreate(String key, RateLimiter bucket, long currentTime) {
            return nanos(bucket);
        }

        @Override
        public long expireAfterUpdate(String key, RateLimiter bucket, long currentTime,
                                      long currentDuration) {
            return nanos(bucket);
        }

        @Override
        public long expireAfterRead(String key, RateLimiter bucket, long currentTime,
                                    long currentDuration) {
            return nanos(bucket);
        }
    }

    /** Live bucket count — for tests and for a future metrics binding. */
    public long trackedKeyCount() {
        buckets.cleanUp();
        return buckets.estimatedSize();
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
        String bucketName = RateLimitNaming.perKey(base, key);

        // Clone the configured base instance's template. rateLimiter(base) returns the
        // YAML-provisioned instance; the per-key bucket is built from its config on first use
        // and returned as-is for every subsequent call with the same key — until it is evicted
        // for idleness or to hold the size ceiling, at which point a fresh one is built.
        //
        // Built standalone rather than through the registry: registry.rateLimiter(name, config)
        // retains the instance forever, which is precisely the leak this cache exists to close.
        RateLimiter bucket = buckets.get(bucketName,
                name -> RateLimiter.of(name, registry.rateLimiter(base).getRateLimiterConfig()));

        RateLimiter.waitForPermission(bucket);
        return true;
    }
}
