// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.LoginRequest;
import com.daedalus.api.dto.LoginResponse;
import com.daedalus.server.config.AdminCredentialsProperties;
import com.daedalus.server.security.JwtTokenService;
import io.github.resilience4j.ratelimiter.annotation.RateLimiter;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Login endpoint. Validates the supplied credentials against the configured admin user
 * (single user, env-var-provisioned, bcrypt-hashed password) and returns a freshly signed
 * JWT on success.
 *
 * <p>Failure cases all return a generic {@code 401 Unauthorized} with no body — the response
 * is identical for "no admin user configured", "username doesn't match", and "password
 * doesn't match" so external probes can't enumerate the difference.
 *
 * <p>This endpoint is mounted in every profile so dev / desktop deploys can issue tokens
 * for testing too. Production-grade lockout (rate limiting, account lockout after N failed
 * attempts) is intentionally out of scope for this portfolio iteration; add it before any
 * deployment that's reachable from untrusted networks.
 */
@RestController
@RequestMapping("/api/v1/auth")
@Tag(name = "Auth", description = "Issue JWTs for the protected API surface.")
public class AuthController {

    private final AdminCredentialsProperties adminCreds;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenService tokenService;

    public AuthController(AdminCredentialsProperties adminCreds,
                          PasswordEncoder passwordEncoder,
                          JwtTokenService tokenService) {
        this.adminCreds = adminCreds;
        this.passwordEncoder = passwordEncoder;
        this.tokenService = tokenService;
    }

    @PostMapping("/login")
    @Operation(summary = "Exchange admin credentials for a JWT.",
            description = "Returns 200 + token on success, 401 on any failure (no body, no leakage "
                    + "about which check failed). The token is valid for "
                    + "daedalus.security.jwt.ttl-minutes (default 60). Use it as "
                    + "Authorization: Bearer <token> on subsequent requests. "
                    + "Rate-limited per the 'authLogin' Resilience4j instance — bursts past the "
                    + "configured limit return 429 with a Retry-After header. Note this is a "
                    + "global limiter; per-IP / per-username throttling is on the backlog.")
    @RateLimiter(name = "authLogin")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest req) {
        if (!adminCreds.isConfigured()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        if (!adminCreds.username().equals(req.username())
                || !passwordEncoder.matches(req.password(), adminCreds.passwordBcrypt())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        JwtTokenService.IssuedToken issued = tokenService.issue(req.username());
        return ResponseEntity.ok(new LoginResponse(issued.token(), issued.expiresAt()));
    }
}
