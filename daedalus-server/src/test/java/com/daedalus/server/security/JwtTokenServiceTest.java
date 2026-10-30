// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import com.daedalus.server.config.JwtAuthProperties;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtException;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Round-trips tokens through {@link JwtTokenService} and exercises the failure modes that
 * matter for production: short secrets must reject at construction time, tokens signed by a
 * different secret must reject at decode, and the standard claims ({@code iss}, {@code sub},
 * {@code iat}, {@code exp}) must be populated correctly.
 */
class JwtTokenServiceTest {

    private static final String SECRET_32B = "this-is-a-thirty-two-byte-secret"; // 32 chars / bytes
    private static final String OTHER_SECRET = "a-completely-different-secret-32!";

    private static JwtTokenService serviceWith(String secret, long ttlMinutes) {
        return new JwtTokenService(new JwtAuthProperties(secret, "daedalus-server", ttlMinutes));
    }

    @Test
    void issue_andDecode_roundTrip_carriesStandardClaims() {
        JwtTokenService svc = serviceWith(SECRET_32B, 60);

        Instant before = Instant.now();
        JwtTokenService.IssuedToken issued = svc.issue("admin");
        Instant after = Instant.now();

        Jwt parsed = svc.decoder().decode(issued.token());

        // Read iss as a plain string. Spring's typed Jwt#getIssuer() coerces to java.net.URL
        // and throws if the claim isn't URL-shaped; per RFC 7519 the iss claim is StringOrURI,
        // and "daedalus-server" is the valid string form for a self-signed issuer.
        assertThat(parsed.getClaimAsString("iss")).isEqualTo("daedalus-server");
        assertThat(parsed.getSubject()).isEqualTo("admin");
        assertThat(parsed.getIssuedAt())
                .isAfterOrEqualTo(before.minusSeconds(1))
                .isBeforeOrEqualTo(after.plusSeconds(1));
        // exp ≈ iat + 60 minutes, with a 2-second slack to absorb clock jitter.
        long ttlSeconds = parsed.getExpiresAt().getEpochSecond() - parsed.getIssuedAt().getEpochSecond();
        assertThat(ttlSeconds).isBetween(60L * 60 - 2, 60L * 60 + 2);
    }

    @Test
    void decode_rejectsTokenSignedByDifferentSecret() {
        JwtTokenService issuer = serviceWith(SECRET_32B, 60);
        JwtTokenService verifier = serviceWith(OTHER_SECRET, 60);

        String foreign = issuer.issue("admin").token();

        assertThatThrownBy(() -> verifier.decoder().decode(foreign))
                .isInstanceOf(JwtException.class);
    }

    @Test
    void construction_rejectsShortSecret() {
        // 16 bytes is well below the HS256 minimum of 32. The HMAC key spec itself accepts
        // short keys, but JwtTokenService refuses them up front so the failure surface is at
        // boot rather than first-token-issued.
        assertThatThrownBy(() -> serviceWith("too-short-secret", 60))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("32 bytes");
    }

    @Test
    void issuedToken_expiresAtMatchesTtl() {
        JwtTokenService svc = serviceWith(SECRET_32B, /* ttl */ 5);

        Instant before = Instant.now();
        JwtTokenService.IssuedToken issued = svc.issue("admin");

        // expiresAt should be approximately 5 minutes after the issuer captured `before`.
        // Use a 2-second slack on each side to absorb the small gap between `before` and
        // the actual issuance instant inside JwtTokenService.issue().
        long deltaSeconds = issued.expiresAt().getEpochSecond() - before.getEpochSecond();
        assertThat(deltaSeconds).isBetween(5L * 60 - 2, 5L * 60 + 2);
    }
}
