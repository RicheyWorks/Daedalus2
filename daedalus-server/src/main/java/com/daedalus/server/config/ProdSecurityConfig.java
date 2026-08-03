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
 *   <li>{@code GET /} and {@code GET /index.html} — the web UI. The README publishes it as
 *       "served at {@code /}" and it was 401 in prod: {@code anyRequest().authenticated()}
 *       covers static resources too, and {@code ProdAuthPostureTest} scans controller mappings,
 *       so no table this project keeps had a row for a file. See the note at the matcher.</li>
 *   <li>{@code GET /api/v1/algorithms}, {@code GET /api/v1/maze/&#123;id&#125;},
 *       {@code GET /api/v1/leaderboard} — read-only API surface, intentionally browsable</li>
 *   <li>{@code POST /api/v1/auth/login} — credentials → token; chicken-and-egg otherwise</li>
 *   <li>{@code GET /actuator/health}, {@code /info}, {@code /prometheus} — probes / scrapers</li>
 *   <li><b>The share-a-link surface</b>: {@code GET /api/v1/session/&#123;id&#125;} (the
 *       {@code #session=} spectator permalink), {@code GET /api/v1/session/&#123;id&#125;/tour},
 *       {@code GET /api/v1/maze/&#123;id&#125;/ghost} (the ghost racer) and
 *       {@code GET /api/v1/agent/&#123;id&#125;} (free re-poll). These are read-only, keyed by an
 *       unguessable UUID, and there is exactly one account in this system — so "authenticated"
 *       here would mean "only the operator", which makes a spectator link that nobody can
 *       spectate. They were closed by the default-deny rule until 2026-07-31, which is to say
 *       these features did not work in prod at all. See {@code ProdAuthPostureTest}.</li>
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

                        // ---- The web UI ----
                        // The other half of the share-a-link surface, and the half that was
                        // missed. Opening the spectator *API* in prod bought nothing while the
                        // page that calls it stayed closed: the link the UI hands out is
                        // `https://host/#session={id}` — origin root plus a fragment — so a
                        // spectator following it got 401 from the static page and never reached
                        // any of the endpoints carefully permitted below. Measured on a prod-
                        // profile boot: /api/v1/session/{id} answered, "/" answered 401.
                        //
                        // Enumerated rather than globbed, and the enumeration is complete: the
                        // UI is one file. A second asset added later will 401 until somebody
                        // lists it, which is the same fail-closed choice as the single-segment
                        // '*' matchers below — a static directory served by "/**" is exactly the
                        // kind of matcher that silently publishes whatever lands in it.
                        //
                        // Nothing is given away by serving it. The page is markup and script
                        // with no embedded credentials, and every capability it offers is still
                        // governed by the rules in this method — a visitor without a token can
                        // browse public mazes and spectate, and generate/solve/session all
                        // answer 401 exactly as they did before.
                        .requestMatchers(HttpMethod.GET, "/", "/index.html").permitAll()

                        // ---- Public read endpoints ----
                        .requestMatchers(HttpMethod.GET, "/api/v1/algorithms").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/maze/*").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/leaderboard").permitAll()

                        // ---- The share-a-link surface ----
                        // Single-segment matchers on purpose: '*' stops at one path segment, so
                        // /session/{id} does not drag in /session/{id}/join, and /agent/{id} does
                        // not drag in /agent/{id}/step. Both of those spend server state and stay
                        // closed. Widening any of these to '**' is the exact slip
                        // ProdAuthPostureTest exists to catch.
                        .requestMatchers(HttpMethod.GET, "/api/v1/session/*").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/session/*/tour").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/maze/*/ghost").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/agent/*").permitAll()

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
