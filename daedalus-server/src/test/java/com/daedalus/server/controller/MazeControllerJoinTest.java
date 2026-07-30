// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.MoveRequest;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
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
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.UUID;

import static org.hamcrest.Matchers.equalTo;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * REST posture of the multiplayer join endpoint. Uses a <b>real</b> {@code GameSessionService}
 * (the flag is the subject under test — mocking it would prove nothing) with a mocked maze
 * store, in the standalone-MockMvc style of the other controller slices.
 */
class MazeControllerJoinTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    private MazeGrid grid;
    private MazeGenerationService gen;
    private UUID mazeId;

    @BeforeEach
    void setUp() {
        grid = new RecursiveBacktrackerGenerator().generate(8, 8, 7L, new MazeStats());
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(7, 7));
        MazeMetadata meta = MazeMetadata.of(8, 8, 7L, "recursive-backtracker",
                grid.start(), grid.goal());
        mazeId = meta.id();
        gen = mock(MazeGenerationService.class);
        when(gen.find(any())).thenReturn(new MazeGenerationService.Cached(meta, grid, new MazeStats()));
    }

    private MockMvc mvc(GameSessionService sessions) {
        MazeController controller = new MazeController(
                gen,
                mock(MazeSolverService.class),
                mock(AlgorithmCatalogService.class),
                sessions,
                mock(LeaderboardService.class),
                mock(com.daedalus.server.service.LivingMazeService.class),
                mock(com.daedalus.server.service.DailyMazeService.class));
        return MockMvcBuilders.standaloneSetup(controller).build();
    }

    @Test
    void withTheFlagOffJoinAnswers404AsIfTheEndpointDidNotExist() throws Exception {
        GameSessionService sessions =
                new GameSessionService(event -> { }, mock(LeaderboardService.class), false);
        var s = sessions.open(mazeId, "Alice", grid.start());

        mvc(sessions).perform(post("/api/v1/session/" + s.id() + "/join").param("player", "Bob"))
                .andExpect(status().isNotFound());
    }

    @Test
    void withTheFlagOnJoinAdmitsThePlayerAndMoveAcceptsTheirName() throws Exception {
        GameSessionService sessions =
                new GameSessionService(event -> { }, mock(LeaderboardService.class), true);
        var s = sessions.open(mazeId, "Alice", grid.start());
        MockMvc mvc = mvc(sessions);

        mvc.perform(post("/api/v1/session/" + s.id() + "/join").param("player", "Bob"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId", equalTo(s.id().toString())))
                .andExpect(jsonPath("$.position.row", equalTo(0)))
                .andExpect(jsonPath("$.position.col", equalTo(0)));

        Point bobTo = grid.openNeighbors(grid.start()).get(0);
        mvc.perform(post("/api/v1/session/" + s.id() + "/move")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(new MoveRequest(bobTo, "Bob"))))
                .andExpect(status().isOk())
                .andExpect(content().string("true"));
        // The move landed on Bob, not on the opening player.
        org.assertj.core.api.Assertions.assertThat(s.playerPosition("Bob")).isEqualTo(bobTo);
        org.assertj.core.api.Assertions.assertThat(s.currentPosition()).isEqualTo(grid.start());
    }

    @Test
    void joiningACompletedSessionAnswers409() throws Exception {
        GameSessionService sessions =
                new GameSessionService(event -> { }, mock(LeaderboardService.class), true);
        Point nextToGoal = grid.openNeighbors(grid.goal()).get(0);
        var s = sessions.open(mazeId, "Alice", nextToGoal);
        sessions.tryMove(s.id(), grid, grid.goal());

        mvc(sessions).perform(post("/api/v1/session/" + s.id() + "/join").param("player", "Bob"))
                .andExpect(status().isConflict());
    }
}
