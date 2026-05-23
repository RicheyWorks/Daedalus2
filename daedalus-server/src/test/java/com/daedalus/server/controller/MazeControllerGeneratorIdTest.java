// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.GenerateRequest;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.server.service.AlgorithmCatalogService;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.equalTo;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Locks in the audit's #1 server fix at the REST surface: when the maze generation service
 * returns a fallback {@code Cached} whose {@code generatorId} differs from what the client
 * requested, {@code POST /api/v1/maze/generate} must surface the *actual* generator id in its
 * response — not parrot the request back.
 */
class MazeControllerGeneratorIdTest {

    private MazeGenerationService gen;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        gen = mock(MazeGenerationService.class);
        MazeController controller = new MazeController(
                gen,
                mock(MazeSolverService.class),
                mock(AlgorithmCatalogService.class),
                mock(GameSessionService.class),
                mock(LeaderboardService.class));
        mvc = MockMvcBuilders.standaloneSetup(controller).build();
    }

    @Test
    void generate_returnsActualGeneratorIdFromMetadata_notRequested() throws Exception {
        // Caller asks for "astar" (or anything that might trip the breaker).
        // The service yields a fallback maze whose metadata says "binary-tree".
        MazeMetadata fallbackMeta = MazeMetadata.of(5, 5, 42L, "binary-tree",
                new Point(0, 0), new Point(4, 4));
        MazeGrid grid = new MazeGrid(5, 5);
        MazeGenerationService.Cached cached =
                new MazeGenerationService.Cached(fallbackMeta, grid, new MazeStats());

        when(gen.generate(anyString(), anyInt(), anyInt(), anyLong())).thenReturn(cached);

        String body = new ObjectMapper().writeValueAsString(
                new GenerateRequest("astar", 5, 5, 42L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.generatorId", equalTo("binary-tree")))
                .andExpect(jsonPath("$.rows", equalTo(5)))
                .andExpect(jsonPath("$.cols", equalTo(5)))
                .andExpect(jsonPath("$.seed", equalTo(42)));
    }
}
