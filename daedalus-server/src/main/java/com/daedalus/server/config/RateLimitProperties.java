// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.ConstructorBinding;

import java.time.Duration;

/**
 * Tuning knobs for the per-key rate limiter, bound from {@code daedalus.ratelimit.*}.
 *
 * <p>Picked up automatically by the {@code @ConfigurationPropertiesScan("com.daedalus.server.config")}
 * on {@code DaedalusApp}.
 *
 * @param trustForwardedHeader when {@code true}, {@code RateLimitKeyResolver} keys unauthenticated
 *        callers off the first hop in the {@code X-Forwarded-For} header instead of the socket
 *        {@code remoteAddr}. Enable this <em>only</em> when the app sits behind a trusted reverse
 *        proxy / load balancer that overwrites {@code X-Forwarded-For} — otherwise a client can
 *        spoof the header and hand itself a fresh bucket per forged IP, defeating the limit.
 *        Defaults to {@code false} (trust the socket address); {@code application-prod.yml} turns
 *        it on because that surface runs behind an ingress.
 * @param maxKeys ceiling on how many distinct caller buckets are held at once. Beyond this,
 *        Caffeine evicts the least-recently-used. Bounds the memory a high-cardinality caller can
 *        force the process to allocate — see {@code PerKeyRateLimitInterceptor} for why eviction
 *        is safe rather than a bypass. Defaults to 10 000.
 * @param idleTtl how long an untouched bucket is kept before eviction. The <em>effective</em> TTL
 *        is raised per bucket to at least its own limit-refresh period, because evicting a drained
 *        bucket early would hand its owner a fresh budget. Defaults to 10 minutes.
 */
@ConfigurationProperties("daedalus.ratelimit")
public record RateLimitProperties(boolean trustForwardedHeader, Integer maxKeys, Duration idleTtl) {

    private static final int DEFAULT_MAX_KEYS = 10_000;
    private static final Duration DEFAULT_IDLE_TTL = Duration.ofMinutes(10);

    /**
     * Applies defaults so an absent or partial {@code daedalus.ratelimit} block still binds.
     *
     * <p>{@code @ConstructorBinding} is required here rather than optional: adding the
     * convenience constructor below gave this record two constructors, and Spring's binder
     * will not guess between them — it falls back to looking for a no-arg constructor and the
     * whole application context fails to start. Naming the canonical one resolves it.
     */
    @ConstructorBinding
    public RateLimitProperties {
        if (maxKeys == null || maxKeys < 1) {
            maxKeys = DEFAULT_MAX_KEYS;
        }
        if (idleTtl == null || idleTtl.isNegative() || idleTtl.isZero()) {
            idleTtl = DEFAULT_IDLE_TTL;
        }
    }

    /**
     * The only knob most callers care about; bucket-store sizing takes its defaults.
     * Keeps test and programmatic construction readable now that the record has grown.
     */
    public RateLimitProperties(boolean trustForwardedHeader) {
        this(trustForwardedHeader, null, null);
    }
}
