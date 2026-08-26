// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.model.GameSession;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.model.MazeStats;
import com.daedalus.server.controller.SessionController;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Which algorithm a recorded run was played on — the one field on {@link LeaderboardEntry} that
 * only the production path fills in.
 *
 * <p>It was the literal string {@code "unknown"}, hard-coded in {@code GameSessionService}, on
 * every run this server has ever recorded. A live probe found it: play a session on a
 * recursive-backtracker maze through to the goal, read the board back, and the entry says
 * {@code "mazeGeneratorId": "unknown"}.
 *
 * <p><b>Why nothing caught it.</b> Six test classes construct {@code LeaderboardEntry} and every
 * one of them passes its own generator id — {@code "recursive-backtracker"} in the partition
 * test, {@code "binary-tree"} in its legacy-shape case. Each is a perfectly good test of the
 * thing it is testing, and collectively they mean the value the *service* writes is the one
 * value the suite never observes. That is the shape to watch for: a field whose only producer is
 * the code under test, asserted everywhere by fixtures that supply it themselves.
 *
 * <p><b>Why it was worse than a wrong string.</b> {@link LeaderboardService#submit} keys a Redis
 * sorted set on this value, so the per-generator partition was not a set per generator — it was
 * one set named {@code …:gen:unknown} holding every run on every algorithm. And nothing read it,
 * which is why no behaviour ever looked wrong. Both halves are fixed together: the id is carried
 * from session open, and {@link LeaderboardService#topByGenerator} is the reader that makes the
 * partition mean something.
 *
 * <p>So these tests go through the service rather than around it. Anything that builds an entry
 * by hand is testing the fixture.
 */
class LeaderboardGeneratorAttributionTest {

    private final GeneratorRegistry registry = new GeneratorRegistry(
            List.of(new RecursiveBacktrackerGenerator(), new PrimsGenerator()));

    /** Plays a session from start to goal and returns the entry the service recorded. */
    private LeaderboardEntry playToTheGoal(String generatorId, String player) {
        LeaderboardService board = new LeaderboardService(null, false, 100);
        GameSessionService sessions = new GameSessionService(event -> { }, board);

        MazeGrid grid = registry.require(generatorId).generate(11, 11, 7L, new MazeStats());
        UUID mazeId = UUID.randomUUID();
        GameSession session =
                sessions.open(mazeId, generatorId, player, grid.start(), null);

        List<Point> route = new BfsSolver()
                .solve(grid, grid.start(), grid.goal(), new MazeStats());
        for (int i = 1; i < route.size(); i++) {
            assertThat(sessions.tryMove(session.id(), player, grid, route.get(i)))
                    .as("step %d of the solver's own route must be a legal move", i)
                    .isTrue();
        }

        List<LeaderboardEntry> entries = board.top(10);
        assertThat(entries)
                .as("reaching the goal is what submits the entry; without one there is "
                        + "nothing to attribute and the rest of this test is vacuous")
                .hasSize(1);
        return entries.get(0);
    }

    @Test
    void aCompletedRunNamesTheAlgorithmItWasActuallyPlayedOn() {
        LeaderboardEntry entry = playToTheGoal("recursive-backtracker", "ariadne");

        assertThat(entry.mazeGeneratorId())
                .as("the entry the service writes, not one a fixture handed it — this is "
                        + "exactly the assertion whose absence let a hard-coded placeholder "
                        + "ship on every run the server has ever recorded")
                .isEqualTo("recursive-backtracker")
                .isNotEqualTo(GameSession.UNKNOWN_GENERATOR);
    }

    @Test
    void twoGeneratorsProduceTwoBoards_notOneSharedBucket() {
        // The consequence that made this more than a cosmetic field: LeaderboardService keys a
        // partition on the id, so a constant collapses every generator into one set. Two runs
        // on two algorithms is the smallest fixture that can tell the two worlds apart.
        LeaderboardService board = new LeaderboardService(null, false, 100);
        GameSessionService sessions = new GameSessionService(event -> { }, board);

        for (String generatorId : List.of("recursive-backtracker", "prims")) {
            MazeGrid grid = registry.require(generatorId).generate(11, 11, 3L, new MazeStats());
            GameSession s = sessions.open(UUID.randomUUID(), generatorId,
                    "player-" + generatorId, grid.start(), null);
            List<Point> route = new BfsSolver()
                    .solve(grid, grid.start(), grid.goal(), new MazeStats());
            for (int i = 1; i < route.size(); i++) {
                sessions.tryMove(s.id(), "player-" + generatorId, grid, route.get(i));
            }
        }

        assertThat(board.topByGenerator(10, "recursive-backtracker"))
                .extracting(LeaderboardEntry::playerName)
                .containsExactly("player-recursive-backtracker");
        assertThat(board.topByGenerator(10, "prims"))
                .extracting(LeaderboardEntry::playerName)
                .containsExactly("player-prims");
        assertThat(board.top(10))
                .as("and the global board still holds both")
                .hasSize(2);
    }

    @Test
    void aRunKeepsItsAttributionEvenIfTheMazeIsGoneByTheEnd() {
        // Why the id is recorded at open rather than looked up at completion. Sessions are
        // allowed to outlive their maze's cache entry — GameSessionService handles that case
        // explicitly elsewhere — so a completion-time lookup would put a placeholder on exactly
        // the long, slow games most worth recording. Nothing here consults a maze cache at all,
        // which is the point: this test would be impossible to write against the other design.
        LeaderboardEntry entry = playToTheGoal("prims", "theseus");

        assertThat(entry.mazeGeneratorId()).isEqualTo("prims");
    }

    @Test
    void theSessionEndpointCarriesTheIdAllTheWayFromTheMazeCache() throws Exception {
        // Everything above opens sessions by calling the service directly, with the generator id
        // in hand — which is exactly the gap that let the original bug live. Mutation proved it:
        // reverting the controller to the four-argument open() left every test in this class
        // green, because none of them went through the controller. So this one does, end to end,
        // with real services: generate a maze over HTTP, open a session over HTTP, and require
        // the session the server actually created to know what built its maze.
        MazeGenerationService gen = new MazeGenerationService(
                registry, event -> { }, new SimpleMeterRegistry());
        LeaderboardService board = new LeaderboardService(null, false, 100);
        GameSessionService sessions = new GameSessionService(event -> { }, board);

        SessionController controller = new SessionController(gen, sessions);
        MockMvc mvc = MockMvcBuilders.standaloneSetup(controller).build();

        UUID mazeId = gen.generate("prims", 11, 11, 5L).metadata().id();
        String body = mvc.perform(post("/api/v1/maze/" + mazeId + "/session?player=ariadne"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        UUID sessionId = UUID.fromString(
                new ObjectMapper().readTree(body).get("sessionId").asText());

        assertThat(sessions.find(sessionId).generatorId())
                .as("the controller has the cached maze in hand when it reads the start cell; "
                        + "if it does not also pass the generator id, every run this session "
                        + "records is attributed to a placeholder")
                .isEqualTo("prims");
    }

    @Test
    void anAbsentGeneratorMeansNoPartition_notAnEmptyBoard() {
        // The other thing mutation caught: topByGenerator(n, null) forwarding to the global
        // board is load-bearing, because the controller routes *every* unpartitioned request
        // through it. Returning an empty list instead would blank the default leaderboard, and
        // the routing test above cannot see it — it mocks this service.
        LeaderboardService board = new LeaderboardService(null, false, 100);
        board.submit(new LeaderboardEntry(UUID.randomUUID(), UUID.randomUUID(), "alice",
                900, 10, 1000, "prims", java.time.Instant.now()));

        assertThat(board.topByGenerator(10, null))
                .as("no generator asked for is the global board, which is what the endpoint "
                        + "serves when nobody passes a partition at all")
                .hasSize(1);
        assertThat(board.topByGenerator(10, "  ")).hasSize(1);
        assertThat(board.topByGenerator(10, "recursive-backtracker"))
                .as("but a generator nobody has a run on is genuinely empty")
                .isEmpty();
    }

    @Test
    void anUnattributedSessionSaysSoInOnePlaceRatherThanEverywhere() {
        // The legacy constructors still exist and still have to answer something. What matters
        // is that the placeholder is now a named constant with one definition, instead of a
        // string literal sitting on the production write path.
        GameSession legacy = new GameSession(UUID.randomUUID(), "anon", new Point(0, 0));

        assertThat(legacy.generatorId()).isEqualTo(GameSession.UNKNOWN_GENERATOR);
        assertThat(new GameSession(UUID.randomUUID(), null, "anon", new Point(0, 0), null)
                .generatorId())
                .as("null is the caller not knowing, which is the same answer, never a null "
                        + "that would key a Redis set named ':gen:null'")
                .isEqualTo(GameSession.UNKNOWN_GENERATOR);
    }
}
