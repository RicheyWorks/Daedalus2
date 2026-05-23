// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.GenerateRequest;
import com.daedalus.api.dto.MoveRequest;
import com.daedalus.model.Point;
import com.daedalus.server.service.AlgorithmCatalogService;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.notNullValue;
import static org.mockito.Mockito.mock;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Locks in the {@code @Valid} contract on {@link MazeController}: any request whose body
 * violates the bounds in {@link com.daedalus.api.dto.GenerateRequest} comes back as a 400
 * with a structured RFC 7807 {@code ProblemDetail} body — never a 500.
 *
 * <p>Standalone setup is sufficient for body validation because Spring runs
 * {@code @Valid @RequestBody} resolution unconditionally during argument binding. Type-
 * coercion failures ({@code MethodArgumentTypeMismatchException} for a non-UUID path var)
 * also surface here because they're raised before the controller method is invoked.
 *
 * <p><b>Out of scope for this test:</b> method-level validation of path / query params
 * driven by the class-level {@code @Validated} annotation (e.g. {@code @Min} on
 * {@code @RequestParam int n}, {@code @Pattern} on {@code @PathVariable String solverId}).
 * That path needs Spring's {@code MethodValidationInterceptor} AOP proxy, which standalone
 * MockMvc does not install. Add a {@code @SpringBootTest} integration test if you want to
 * lock those in too — the wiring itself is correct and exercised at runtime.
 */
class MazeControllerValidationTest {

    private MockMvc mvc;
    private ObjectMapper json;

    @BeforeEach
    void setUp() {
        MazeController controller = new MazeController(
                mock(MazeGenerationService.class),
                mock(MazeSolverService.class),
                mock(AlgorithmCatalogService.class),
                mock(GameSessionService.class),
                mock(LeaderboardService.class));
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
        json = new ObjectMapper();
    }

    // ---------- body validation (POST /maze/generate) ----------

    @Test
    void generate_withBlankGeneratorId_returns400_withFieldError() throws Exception {
        String body = json.writeValueAsString(new GenerateRequest("", 10, 10, 1L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title", equalTo("Validation failed")))
                .andExpect(jsonPath("$.fieldErrors.generatorId", notNullValue()));
    }

    @Test
    void generate_withGeneratorIdContainingUppercase_returns400() throws Exception {
        String body = json.writeValueAsString(new GenerateRequest("BinaryTree", 10, 10, 1L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.generatorId",
                        containsString("lowercase")));
    }

    @Test
    void generate_withRowsBelowMinimum_returns400() throws Exception {
        String body = json.writeValueAsString(new GenerateRequest("binary-tree", 1, 10, 1L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.rows", containsString("at least 2")));
    }

    @Test
    void generate_withColsAboveMaximum_returns400() throws Exception {
        String body = json.writeValueAsString(new GenerateRequest("binary-tree", 10, 9999, 1L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.cols", containsString("at most 512")));
    }

    @Test
    void generate_withMultipleViolations_reportsAllFields() throws Exception {
        // generatorId blank + rows too small + cols too large — every field's error
        // should land in the same response so the client can fix all of them at once.
        String body = json.writeValueAsString(new GenerateRequest("", 0, 9999, 1L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.generatorId", notNullValue()))
                .andExpect(jsonPath("$.fieldErrors.rows", notNullValue()))
                .andExpect(jsonPath("$.fieldErrors.cols", notNullValue()));
    }

    @Test
    void generate_withMalformedJson_returns400_malformedRequest() throws Exception {
        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content("{not json"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title", equalTo("Malformed request")));
    }

    // ---------- body validation (POST /session/{id}/move) ----------

    @Test
    void move_withNullTo_returns400_withFieldError() throws Exception {
        // Jackson serializes a record(null) as {"to":null}; @NotNull catches it.
        String body = "{\"to\":null}";

        mvc.perform(post("/api/v1/session/00000000-0000-0000-0000-000000000000/move")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title", equalTo("Validation failed")))
                .andExpect(jsonPath("$.fieldErrors.to", containsString("required")));
    }

    @Test
    void move_withNegativeRow_returns400_withFieldError() throws Exception {
        // @NonNegativeCoordinate catches the negative coord at the API surface so the
        // request never reaches GameSessionService#tryMove.
        String body = json.writeValueAsString(new MoveRequest(new Point(-1, 3)));

        mvc.perform(post("/api/v1/session/00000000-0000-0000-0000-000000000000/move")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.to", containsString("non-negative")));
    }

    @Test
    void move_withNegativeCol_returns400_withFieldError() throws Exception {
        String body = json.writeValueAsString(new MoveRequest(new Point(3, -5)));

        mvc.perform(post("/api/v1/session/00000000-0000-0000-0000-000000000000/move")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.to", containsString("non-negative")));
    }

    // ---------- argument-resolution failures (work in standalone too) ----------

    @Test
    void getMaze_withNonUuidPath_returns400() throws Exception {
        // MethodArgumentTypeMismatchException is raised by Spring's argument binding
        // before the controller method runs, so it fires under standalone setup just
        // as it does in a fully-wired context.
        mvc.perform(get("/api/v1/maze/not-a-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title", equalTo("Invalid parameter")))
                .andExpect(jsonPath("$.fieldErrors.id", containsString("UUID")));
    }

    @Test
    void problemDetail_responseContentType_isProblemJson() throws Exception {
        // RFC 7807 says the canonical media type is application/problem+json. Spring's
        // ProblemDetail handling defaults to that; this test is the regression guard so
        // a future global ContentNegotiation tweak doesn't quietly downgrade it.
        String body = json.writeValueAsString(new GenerateRequest("", 10, 10, 1L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(header().string("Content-Type",
                        containsString("application/problem+json")));
    }
}
