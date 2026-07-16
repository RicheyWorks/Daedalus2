// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import com.daedalus.server.config.JwtAuthProperties;
import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.stereotype.Service;

import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;

/**
 * Issues and validates HMAC-SHA256 (HS256) JWTs for the Daedalus API.
 *
 * <p>Tokens carry the standard claims:
 * <ul>
 *   <li>{@code iss} — from {@link JwtAuthProperties#issuer()}</li>
 *   <li>{@code sub} — the authenticated user's username</li>
 *   <li>{@code iat} — issue time</li>
 *   <li>{@code exp} — issue time + {@link JwtAuthProperties#ttlMinutes()}</li>
 * </ul>
 *
 * <p>The same secret signs and verifies. Provided as a {@link JwtEncoder} +
 * {@link JwtDecoder} pair so Spring Security's resource-server filter chain can pick up the
 * decoder bean automatically while {@link com.daedalus.server.controller.AuthController} uses
 * the encoder for the login flow.
 */
@Service
public class JwtTokenService {

    private final JwtAuthProperties props;
    private final JwtEncoder encoder;
    private final JwtDecoder decoder;

    public JwtTokenService(JwtAuthProperties props) {
        this.props = props;

        // Decode base64; if the secret isn't valid base64 we fall back to UTF-8 bytes so dev
        // configs that drop in a literal string still work. Production should use a real
        // 256-bit base64 secret.
        byte[] keyBytes = decodeSecretLeniently(props.secret());
        if (keyBytes.length < 32) {
            throw new IllegalStateException(
                    "daedalus.security.jwt.secret resolves to " + keyBytes.length
                            + " bytes; HS256 requires at least 32 bytes (256 bits). "
                            + "Generate one with: openssl rand -base64 32");
        }
        SecretKeySpec key = new SecretKeySpec(keyBytes, "HmacSHA256");

        this.encoder = new NimbusJwtEncoder(new ImmutableSecret<>(key));
        this.decoder = NimbusJwtDecoder.withSecretKey(key)
                .macAlgorithm(org.springframework.security.oauth2.jose.jws.MacAlgorithm.HS256)
                .build();
    }

    /** Issue a fresh signed token for {@code subject}. */
    public IssuedToken issue(String subject) {
        Instant now = Instant.now();
        Instant expiresAt = now.plus(Duration.ofMinutes(props.ttlMinutes()));
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(props.issuer())
                .subject(subject)
                .issuedAt(now)
                .expiresAt(expiresAt)
                .build();
        JwsHeader header = JwsHeader.with(org.springframework.security.oauth2.jose.jws.MacAlgorithm.HS256).build();
        Jwt jwt = encoder.encode(JwtEncoderParameters.from(header, claims));
        return new IssuedToken(jwt.getTokenValue(), expiresAt);
    }

    /** Spring Security resource-server filter consumes this. */
    public JwtDecoder decoder() {
        return decoder;
    }

    /**
     * The base64 decoder throws on non-base64 input. Keep dev ergonomics by falling back to
     * raw UTF-8 bytes — but production should always use a real base64-encoded secret.
     */
    private static byte[] decodeSecretLeniently(String secret) {
        try {
            return Base64.getDecoder().decode(secret);
        } catch (IllegalArgumentException e) {
            return secret.getBytes(StandardCharsets.UTF_8);
        }
    }

    /** Return shape for {@link com.daedalus.api.dto.LoginResponse}. */
    public record IssuedToken(String token, Instant expiresAt) {}
}
