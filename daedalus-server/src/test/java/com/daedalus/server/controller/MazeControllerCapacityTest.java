// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.GenerateRequest;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.daedalus.server.service.AgentWalkService;
import com.daedalus.server.service.AlgorithmCatalogService;
import com.daedalus.server.service.DailyMazeService;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.LivingMazeService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.server.service.TrafficService;
import com.daedalus.server.service.WaypointService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.solver.SolverBudgetExceededException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.UUID;

import static org.hamcrest.Matchers.equalTo;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Living/traffic capacity and a solver budget used to throw in the service
 * and become an untested 500 if the advice mapping disappeared. These are
 * the HTTP seam: 409 / 422 with a problem type, not a stack trace.
 */
class MazeControllerCapacityTest {

    private MazeGenerationService gen;
    private LivingMazeService living;
    private TrafficService traffic;
    private MazeSolverService solverSvc;
    private UUID mazeId;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 7L, new MazeStats());
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(7, 7));
        MazeMetadata meta = MazeMetadata.of(8, 8, 7L, "recursive-backtracker",
                grid.start(), grid.goal());
        mazeId = meta.id();
        gen = mock(MazeGenerationService.class);
        when(gen.find(any())).thenReturn(new MazeGenerationService.Cached(meta, grid, new MazeStats()));
        living = mock(LivingMazeService.class);
        traffic = mock(TrafficService.class);
        solverSvc = mock(MazeSolverService.class);
        mvc = MockMvcBuilders.standaloneSetup(new MazeController(
                        gen,
                        solverSvc,
                        mock(AlgorithmCatalogService.class),
                        mock(GameSessionService.class),
                        mock(LeaderboardService.class),
                        living,
                        mock(DailyMazeService.class),
                        traffic))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    @Test
    void aFullLivingPoolAnswers409() throws Exception {
        LivingMazeService.CapacityExceededException full =
                mock(LivingMazeService.CapacityExceededException.class);
        when(full.getMessage()).thenReturn("already animating 1 mazes — retry after one settles");
        when(living.start(any(), anyInt(), anyLong())).thenThrow(full);

        mvc.perform(post("/api/v1/maze/" + mazeId + "/live"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.kind", equalTo("living-capacity")))
                .andExpect(jsonPath("$.title", equalTo("Too many living mazes")));
    }

    @Test
    void aFullTrafficPoolAnswers409() throws Exception {
        TrafficService.CapacityExceededException full =
                mock(TrafficService.CapacityExceededException.class);
        when(full.getMessage()).thenReturn("already tracking traffic on 1 mazes — retry after one settles");
        when(traffic.enable(any())).thenThrow(full);

        mvc.perform(post("/api/v1/maze/" + mazeId + "/traffic"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.kind", equalTo("traffic-capacity")))
                .andExpect(jsonPath("$.title", equalTo("Too many tracked mazes")));
    }

    @Test
    void aFullSessionPoolAnswers409() throws Exception {
        GameSessionService sessions = mock(GameSessionService.class);
        GameSessionService.CapacityExceededException full =
                mock(GameSessionService.CapacityExceededException.class);
        when(full.getMessage()).thenReturn("already holding 1 live sessions — retry after one idles out");
        when(sessions.open(any(), any(), any(), any(), any())).thenThrow(full);
        MockMvc sessionMvc = MockMvcBuilders.standaloneSetup(new MazeController(
                        gen,
                        solverSvc,
                        mock(AlgorithmCatalogService.class),
                        sessions,
                        mock(LeaderboardService.class),
                        living,
                        mock(DailyMazeService.class),
                        traffic))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();

        sessionMvc.perform(post("/api/v1/maze/" + mazeId + "/session"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.kind", equalTo("session-capacity")))
                .andExpect(jsonPath("$.title", equalTo("Too many live sessions")));
    }

    @Test
    void aFullAgentPoolAnswers409() throws Exception {
        AgentWalkService agents = mock(AgentWalkService.class);
        AgentWalkService.CapacityExceededException full =
                mock(AgentWalkService.CapacityExceededException.class);
        when(full.getMessage()).thenReturn("already walking 1 agents — retry after one arrives or idles out");
        when(agents.open(any(), any())).thenThrow(full);
        MockMvc agentMvc = MockMvcBuilders.standaloneSetup(new AgentController(agents))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();

        agentMvc.perform(post("/api/v1/maze/" + mazeId + "/agent"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.kind", equalTo("agent-capacity")))
                .andExpect(jsonPath("$.title", equalTo("Too many agent walks")));
    }

    @Test
    void aFullMazeCacheAnswers409() throws Exception {
        MazeGenerationService.CapacityExceededException full =
                mock(MazeGenerationService.CapacityExceededException.class);
        when(full.getMessage()).thenReturn("already holding 1 cached mazes — retry after one idles out");
        when(gen.generate(anyString(), anyInt(), anyInt(), anyLong(), any(), anyDouble()))
                .thenThrow(full);
        String body = new ObjectMapper().writeValueAsString(
                new GenerateRequest("recursive-backtracker", 8, 8, 7L));

        mvc.perform(post("/api/v1/maze/generate")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.kind", equalTo("maze-capacity")))
                .andExpect(jsonPath("$.title", equalTo("Too many cached mazes")));
    }

    @Test
    void aFullTourPoolAnswers409() throws Exception {
        WaypointService waypoints = mock(WaypointService.class);
        WaypointService.CapacityExceededException full =
                mock(WaypointService.CapacityExceededException.class);
        when(full.getMessage()).thenReturn("already holding 1 waypoint tours — retry after one idles out");
        when(waypoints.tourFor(any(), any())).thenThrow(full);
        MockMvc tourMvc = MockMvcBuilders.standaloneSetup(new InsightController(
                        gen,
                        mock(GameSessionService.class),
                        mock(com.daedalus.server.service.GhostService.class),
                        waypoints,
                        mock(com.daedalus.server.service.ComplexityLabService.class),
                        mock(com.daedalus.server.service.FingerprintService.class),
                        mock(com.daedalus.server.service.HardestRouteService.class),
                        mock(com.daedalus.server.service.TopographyService.class),
                        mock(com.daedalus.server.service.TournamentService.class),
                        mock(com.daedalus.server.service.HeuristicLensService.class)))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();

        tourMvc.perform(get("/api/v1/maze/" + mazeId + "/tour"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.kind", equalTo("tour-capacity")))
                .andExpect(jsonPath("$.title", equalTo("Too many waypoint tours")));
    }

    @Test
    void aSolverThatSpendsItsBudgetAnswers422() throws Exception {
        when(solverSvc.solve(any(), any(), any(), any(), any(), anyBoolean()))
                .thenThrow(new SolverBudgetExceededException("ida-star", 50_000));

        mvc.perform(post("/api/v1/maze/" + mazeId + "/solve/ida-star"))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.kind", equalTo("solver-budget")))
                .andExpect(jsonPath("$.solver", equalTo("ida-star")))
                .andExpect(jsonPath("$.nodeBudget", equalTo(50_000)));
    }
}
