// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.LoginRequest;
import com.daedalus.server.config.AdminCredentialsProperties;
import com.daedalus.server.config.JwtAuthProperties;
import com.daedalus.server.security.JwtTokenService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Locks in the {@code @Valid} contract on {@link AuthController}: blank credentials are now
 * rejected with a structured 400 before the password-matching code ever runs. (Wrong-but-
 * present credentials still go through to the bcrypt check and surface as the original 401
 * — see {@link AuthControllerTest} for that path.)
 */
class AuthControllerValidationTest {

    private static final String SECRET = "this-is-a-thirty-two-byte-secret";

    private MockMvc mvc;
    private ObjectMapper json;

    @BeforeEach
    void setUp() {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
        AdminCredentialsProperties creds =
                new AdminCredentialsProperties("admin", encoder.encode("password"));
        JwtTokenService tokenService =
                new JwtTokenService(new JwtAuthProperties(SECRET, "daedalus-server", 60));

        AuthController controller = new AuthController(creds, encoder, tokenService);
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
        json = new ObjectMapper().registerModule(new JavaTimeModule());
    }

    @Test
    void login_withBlankUsername_returns400_notUnauthorized() throws Exception {
        String body = json.writeValueAsString(new LoginRequest("", "password"));

        mvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title", equalTo("Validation failed")))
                .andExpect(jsonPath("$.fieldErrors.username", notNullValue()));
    }

    @Test
    void login_withBlankPassword_returns400_notUnauthorized() throws Exception {
        String body = json.writeValueAsString(new LoginRequest("admin", ""));

        mvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.password", notNullValue()));
    }

    @Test
    void login_withNullBody_returns400_malformed() throws Exception {
        // Sending no body at all -> Spring throws HttpMessageNotReadableException -> our advice
        // surfaces it as a 400 with the "Malformed request" title.
        mvc.perform(post("/api/v1/auth/login")
                        .contentType("application/json"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title", equalTo("Malformed request")));
    }
}
