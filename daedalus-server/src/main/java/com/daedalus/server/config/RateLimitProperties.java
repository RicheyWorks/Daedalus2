// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

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
 */
@ConfigurationProperties("daedalus.ratelimit")
public record RateLimitProperties(boolean trustForwardedHeader) {
}
