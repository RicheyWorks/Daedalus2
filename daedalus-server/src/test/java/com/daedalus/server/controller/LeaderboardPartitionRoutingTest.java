// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.service.AlgorithmCatalogService;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.server.web.ApiExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Which board {@code GET /api/v1/leaderboard} actually reads.
 *
 * <p>There are now three partitions — global, per maze, per generator — selected by query
 * parameter, and the routing between them is the kind of thing that looks obviously right in
 * the source and is one {@code if} away from silently serving the wrong scoreboard. The
 * per-generator partition in particular spent its whole life written and never read; giving it
 * a reader without pinning which requests reach it would be replacing one quiet mistake with
 * a louder one.
 *
 * <p>{@code maze} wins when both are supplied because it is the more specific of the two: a
 * maze is played with exactly one generator, so a per-maze board is already inside a
 * per-generator board. The opposite precedence would silently widen a daily-challenge request
 * into "every run on that algorithm", which is a different scoreboard that looks plausible.
 */
class LeaderboardPartitionRoutingTest {

    private MockMvc mvc;
    private LeaderboardService board;

    @BeforeEach
    void setUp() {
        board = mock(LeaderboardService.class);
        when(board.top(anyInt())).thenReturn(List.of());
        when(board.top(anyInt(), any())).thenReturn(List.of());
        when(board.topByGenerator(anyInt(), any())).thenReturn(List.of());

        MazeController controller = new MazeController(
                mock(MazeGenerationService.class),
                mock(MazeSolverService.class),
                mock(AlgorithmCatalogService.class),
                mock(GameSessionService.class),
                board,
                mock(com.daedalus.server.service.LivingMazeService.class),
                mock(com.daedalus.server.service.DailyMazeService.class),
                mock(com.daedalus.server.service.TrafficService.class));
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    @Test
    void noPartition_readsTheGlobalBoard() throws Exception {
        mvc.perform(get("/api/v1/leaderboard?n=5")).andExpect(status().isOk());

        // The global read goes through topByGenerator with a null id, which forwards to top(n).
        // Asserting the forwarding here rather than the destination would let the forward be
        // deleted, so this pins that no *partitioned* read happened.
        verify(board, never()).top(anyInt(), any(UUID.class));
        verify(board).topByGenerator(5, null);
    }

    @Test
    void generatorAlone_readsThatAlgorithmsBoard() throws Exception {
        mvc.perform(get("/api/v1/leaderboard?n=5&generator=prims")).andExpect(status().isOk());

        verify(board).topByGenerator(5, "prims");
        verify(board, never()).top(anyInt(), any(UUID.class));
    }

    @Test
    void mazeAlone_readsThatMazesBoard() throws Exception {
        UUID maze = UUID.randomUUID();

        mvc.perform(get("/api/v1/leaderboard?n=5&maze=" + maze)).andExpect(status().isOk());

        verify(board).top(5, maze);
        verify(board, never()).topByGenerator(anyInt(), any());
    }

    @Test
    void bothPartitions_theMoreSpecificOneWins() throws Exception {
        UUID maze = UUID.randomUUID();

        mvc.perform(get("/api/v1/leaderboard?n=5&maze=" + maze + "&generator=prims"))
                .andExpect(status().isOk());

        verify(board).top(5, maze);
        verify(board, never()).topByGenerator(anyInt(), eq("prims"));
    }
}
