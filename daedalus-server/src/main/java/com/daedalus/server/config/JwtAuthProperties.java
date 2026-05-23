// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * JWT signing + verification settings, bound from {@code daedalus.security.jwt.*}.
 *
 * <p>The secret must be at least 32 bytes (256 bits) when decoded — the HS256 algorithm
 * Spring Security uses for HMAC enforces that minimum. Smaller secrets crash the boot.
 *
 * <p>This is a self-hosted issuer pattern: the same secret signs and verifies tokens, so
 * rotating it invalidates every existing session. For the portfolio scope that's fine; in
 * a multi-instance deployment, store the secret in a shared secret manager (Vault, AWS
 * Secrets Manager, etc.) and rotate via blue/green.
 *
 * @param secret    base64-encoded HMAC key, ≥ 32 bytes when decoded
 * @param issuer    {@code iss} claim — surfaces in token introspection / debug logs
 * @param ttl       token lifetime in minutes (default 60)
 */
@ConfigurationProperties("daedalus.security.jwt")
public record JwtAuthProperties(String secret, String issuer, long ttlMinutes) {

    public JwtAuthProperties {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                    "daedalus.security.jwt.secret is required. Set DAEDALUS_JWT_SECRET in your "
                            + "environment. The value must be a base64-encoded byte string of "
                            + "at least 32 bytes (256 bits) for HS256.");
        }
        if (issuer == null || issuer.isBlank()) {
            issuer = "daedalus-server";
        }
        if (ttlMinutes <= 0) {
            ttlMinutes = 60;
        }
    }
}
