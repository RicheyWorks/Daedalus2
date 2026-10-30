// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Dev / non-prod security posture.
 *
 * <p>Active on every profile <em>except</em> {@code prod} — locally, in CI, and when the
 * JavaFX desktop client embeds the server. Every endpoint is {@code permitAll()} so the
 * UI, the test suite, and curl examples all work without an auth handshake.
 *
 * <p>For the production chain (actuator restrictions, Swagger UI disabled, sensitive
 * endpoints require authentication), see {@link ProdSecurityConfig}.
 *
 * <p><b>What's intentionally open here, and why:</b>
 * <ul>
 *   <li>{@code /actuator/**} — readiness probes for the desktop client and dev tooling.</li>
 *   <li>{@code /api/**} — the entire REST surface (currently mounted at {@code /api/v1}).</li>
 *   <li>{@code /ws/**} — STOMP / SockJS upgrade endpoint registered by {@code WebSocketConfig}.</li>
 *   <li>{@code /v3/api-docs/**}, {@code /swagger-ui/**}, {@code /swagger-ui.html} — OpenAPI
 *       spec + Swagger UI from {@code springdoc-openapi-starter-webmvc-ui}.</li>
 * </ul>
 *
 * <p><b>CSRF</b> is disabled because there's no browser session-based form submission;
 * everything is JSON over a stateless API. <b>Sessions</b> are stateless for the same reason.
 */
@Configuration
@EnableWebSecurity
@Profile("!prod")
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .cors(cors -> {})
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // Actuator — health/readiness probes for desktop + dev tooling.
                        .requestMatchers("/actuator/**").permitAll()

                        // The whole REST surface — versioned at /api/v1, glob covers both
                        // current and future versions without requiring this file to change
                        // on every API revision.
                        .requestMatchers("/api/**").permitAll()

                        // WebSocket upgrade endpoint registered by WebSocketConfig.
                        .requestMatchers("/ws/**").permitAll()

                        // OpenAPI spec + Swagger UI from springdoc — open in dev so
                        // contributors can browse the contract without auth.
                        .requestMatchers(
                                "/v3/api-docs",
                                "/v3/api-docs/**",
                                "/v3/api-docs.yaml",
                                "/swagger-ui",
                                "/swagger-ui/**",
                                "/swagger-ui.html"
                        ).permitAll()

                        // Anything else (root, error pages, static resources) — also open
                        // because this profile is the dev / desktop posture.
                        .anyRequest().permitAll()
                );

        return http.build();
    }
}
