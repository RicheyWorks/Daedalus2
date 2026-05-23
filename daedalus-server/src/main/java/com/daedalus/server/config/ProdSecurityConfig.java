// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.server.security.JwtTokenService;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Production security posture. Active when {@code spring.profiles.active=prod}.
 *
 * <p>Auth shape: <b>self-signed JWT, HMAC-SHA256.</b> A single admin user
 * (env-var-provisioned, bcrypt-hashed password) authenticates against
 * {@code POST /api/v1/auth/login} and receives a token. Subsequent calls to protected
 * endpoints carry that token as {@code Authorization: Bearer <token>}.
 *
 * <p><b>Public (no token required)</b>:
 * <ul>
 *   <li>{@code GET /api/v1/algorithms}, {@code GET /api/v1/maze/&#123;id&#125;},
 *       {@code GET /api/v1/leaderboard} — read-only API surface, intentionally browsable</li>
 *   <li>{@code POST /api/v1/auth/login} — credentials → token; chicken-and-egg otherwise</li>
 *   <li>{@code GET /actuator/health}, {@code /info}, {@code /prometheus} — probes / scrapers</li>
 * </ul>
 *
 * <p><b>Authenticated (token required)</b>:
 * <ul>
 *   <li>All write operations: {@code POST /api/v1/maze/generate},
 *       {@code POST /api/v1/maze/&#123;id&#125;/solve/&#123;solverId&#125;},
 *       {@code POST /api/v1/maze/&#123;id&#125;/session},
 *       {@code POST /api/v1/session/&#123;id&#125;/move}</li>
 *   <li>Plugin introspection: {@code GET /api/v1/plugins/**}</li>
 *   <li>Any {@code /actuator/**} path other than the three above</li>
 *   <li>{@code /ws/**} — WebSocket upgrade carries the bearer token via the {@code Authorization}
 *       header on the upgrade request. SockJS / STOMP clients can pass it via
 *       {@code connectHeaders}. Per-frame STOMP-level auth is left for a future iteration.</li>
 * </ul>
 *
 * <p><b>Denied</b>: {@code /v3/api-docs/**}, {@code /swagger-ui/**}, {@code /swagger-ui.html} —
 * the API contract isn't advertised to drive-by traffic in prod. Generate the spec from a CI
 * build instead and ship it to consumers as a static artefact.
 */
@Configuration
@EnableWebSecurity
@Profile("prod")
public class ProdSecurityConfig {

    private final JwtTokenService tokenService;

    public ProdSecurityConfig(JwtTokenService tokenService) {
        this.tokenService = tokenService;
    }

    @Bean
    public JwtDecoder jwtDecoder() {
        // Spring Security's resource-server filter pulls the JwtDecoder bean. We expose the
        // one our self-signed JwtTokenService already built so issuance and verification stay
        // in lock-step (same key, same algorithm, no JWKS round-trip).
        return tokenService.decoder();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .cors(cors -> {})
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // ---- Actuator ----
                        // Probes + metrics scrapers — public.
                        .requestMatchers(
                                "/actuator/health",
                                "/actuator/health/**",
                                "/actuator/info",
                                "/actuator/prometheus"
                        ).permitAll()
                        // Everything else under /actuator requires a valid token.
                        .requestMatchers("/actuator/**").authenticated()

                        // ---- Auth ----
                        // Login is the only way to obtain a token; must be reachable without one.
                        .requestMatchers(HttpMethod.POST, "/api/v1/auth/login").permitAll()

                        // ---- Public read endpoints ----
                        .requestMatchers(HttpMethod.GET, "/api/v1/algorithms").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/maze/*").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/leaderboard").permitAll()

                        // ---- Protected API surface ----
                        // Write operations.
                        .requestMatchers(HttpMethod.POST, "/api/v1/maze/generate").authenticated()
                        .requestMatchers(HttpMethod.POST, "/api/v1/maze/*/solve/*").authenticated()
                        .requestMatchers(HttpMethod.POST, "/api/v1/maze/*/session").authenticated()
                        .requestMatchers(HttpMethod.POST, "/api/v1/session/*/move").authenticated()

                        // Plugin introspection — operator-facing, not drive-by readable.
                        .requestMatchers("/api/v1/plugins/**").authenticated()

                        // WebSocket upgrade — token rides the Authorization header on the
                        // HTTP upgrade request. STOMP-level per-frame auth is a future step.
                        .requestMatchers("/ws/**").authenticated()

                        // ---- Denied ----
                        // OpenAPI spec + Swagger UI are intentionally NOT advertised in prod.
                        .requestMatchers(
                                "/v3/api-docs/**",
                                "/swagger-ui/**",
                                "/swagger-ui.html"
                        ).denyAll()

                        // Anything we didn't explicitly enumerate must be authenticated rather
                        // than implicitly public — fail closed.
                        .anyRequest().authenticated()
                )
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));

        return http.build();
    }
}
