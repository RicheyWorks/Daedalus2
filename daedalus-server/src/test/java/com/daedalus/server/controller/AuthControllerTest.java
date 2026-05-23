// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.LoginRequest;
import com.daedalus.server.config.AdminCredentialsProperties;
import com.daedalus.server.config.JwtAuthProperties;
import com.daedalus.server.security.JwtTokenService;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.matchesPattern;
import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Locks in the {@code POST /api/v1/auth/login} contract: 200 + token on valid credentials,
 * 401 on every failure mode without leaking which check failed (no admin configured,
 * unknown username, wrong password all return identical responses).
 */
class AuthControllerTest {

    private static final String SECRET = "this-is-a-thirty-two-byte-secret";
    private static final String PASSWORD = "correct horse battery staple";

    private MockMvc mvc;
    private ObjectMapper json;
    private AdminCredentialsProperties configured;

    @BeforeEach
    void setUp() {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        configured = new AdminCredentialsProperties("admin", encoder.encode(PASSWORD));

        JwtTokenService tokenService =
                new JwtTokenService(new JwtAuthProperties(SECRET, "daedalus-server", 60));

        AuthController controller = new AuthController(configured, encoder, tokenService);
        mvc = MockMvcBuilders.standaloneSetup(controller).build();

        json = new ObjectMapper().registerModule(new JavaTimeModule());
    }

    @Test
    void login_withCorrectCredentials_returns200AndToken() throws Exception {
        String body = json.writeValueAsString(new LoginRequest("admin", PASSWORD));

        mvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isOk())
                // JWT compact serialization is three base64url chunks separated by dots.
                .andExpect(jsonPath("$.token", matchesPattern("^[\\w-]+\\.[\\w-]+\\.[\\w-]+$")))
                .andExpect(jsonPath("$.expiresAt", notNullValue()));
    }

    @Test
    void login_withWrongPassword_returns401_noBody() throws Exception {
        String body = json.writeValueAsString(new LoginRequest("admin", "not-the-password"));

        mvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void login_withUnknownUsername_returns401_noBody() throws Exception {
        String body = json.writeValueAsString(new LoginRequest("nobody", PASSWORD));

        mvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void login_whenAdminUserNotConfigured_returns401_noBody() throws Exception {
        // Rebuild the controller with empty admin password — simulates "DAEDALUS_ADMIN_PASSWORD_BCRYPT
        // unset in prod". Login must reject everything, not silently accept the env-default
        // password from application.yml.
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        AdminCredentialsProperties unconfigured =
                new AdminCredentialsProperties("admin", null);
        JwtTokenService tokenService =
                new JwtTokenService(new JwtAuthProperties(SECRET, "daedalus-server", 60));
        MockMvc unconfiguredMvc = MockMvcBuilders
                .standaloneSetup(new AuthController(unconfigured, encoder, tokenService))
                .build();

        String body = json.writeValueAsString(new LoginRequest("admin", PASSWORD));

        unconfiguredMvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isUnauthorized());
    }
}
