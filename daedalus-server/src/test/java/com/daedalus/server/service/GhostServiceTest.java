// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.GameSession;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.SessionCompletedEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * Ghost selection rules (ADR-006 idea #8): completed runs challenge the maze's incumbent
 * ghost and the higher score keeps the seat — so the ghost IS the local record holder, in
 * the same ordering the leaderboard uses. Recordings carry the winner's timed walk.
 */
class GhostServiceTest {

    private GhostService ghosts;
    private GameSessionService sessions;
    private MazeGrid grid;
    private final UUID mazeId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        ghosts = new GhostService(1000, Duration.ofHours(24));
        sessions = new GameSessionService(event -> {
            if (event instanceof SessionCompletedEvent e) {
                ghosts.onCompleted(e); // wire the listener by hand — no Spring context here
            }
        }, mock(LeaderboardService.class), true);
        grid = new RecursiveBacktrackerGenerator().generate(8, 8, 7L, new MazeStats());
    }

    /** Walk the opening player along the grid's real openings until the goal. */
    private GameSession completeARun(String player) {
        var s = sessions.open(mazeId, player, grid.start());
        List<Point> path = com.daedalus.theory.MazeMetrics
                .shortestPath(grid, grid.start(), grid.goal());
        for (int i = 1; i < path.size(); i++) {
            assertThat(sessions.tryMove(s.id(), grid, path.get(i))).isTrue();
        }
        assertThat(s.completed()).isTrue();
        return s;
    }

    @Test
    void aCompletedRunBecomesTheGhostWithItsTimedTrail() {
        assertThat(ghosts.ghostOf(mazeId)).as("no ghost before anyone finishes").isNull();

        var s = completeARun("alice");
        var ghost = ghosts.ghostOf(mazeId);

        assertThat(ghost).isNotNull();
        assertThat(ghost.playerName()).isEqualTo("alice");
        assertThat(ghost.moves()).hasSize((int) s.moveCount());
        assertThat(ghost.moves().get(ghost.moves().size() - 1).to())
                .as("the recording ends on the goal — that is what makes it a ghost")
                .isEqualTo(grid.goal());
        // Timestamps are monotone non-decreasing — replayable as-is.
        long prev = -1;
        for (var m : ghost.moves()) {
            assertThat(m.tMs()).isGreaterThanOrEqualTo(prev);
            prev = m.tMs();
        }
    }

    @Test
    void theHigherScoreKeepsTheSeat() {
        completeARun("first");
        var incumbent = ghosts.ghostOf(mazeId);

        // A second, identical-path run is slower in wall-clock (later completion), so its
        // score is at most the incumbent's; the seat must not change hands on a tie/loss.
        completeARun("second");
        assertThat(ghosts.ghostOf(mazeId).playerName())
                .as("a challenger that doesn't strictly beat the score keeps the incumbent")
                .isEqualTo(incumbent.playerName());
    }

    @Test
    void aJoinerFinishRecordsTheJoinersWalk() {
        var s = sessions.open(mazeId, "opener", grid.start());
        Point nextToGoal = grid.openNeighbors(grid.goal()).get(0);
        sessions.join(s.id(), "joiner", nextToGoal);
        assertThat(sessions.tryMove(s.id(), "joiner", grid, grid.goal())).isTrue();

        var ghost = ghosts.ghostOf(mazeId);
        assertThat(ghost).as("an empty opener trail must not skip the winner's walk").isNotNull();
        assertThat(ghost.playerName()).isEqualTo("joiner");
        assertThat(ghost.moves().get(ghost.moves().size() - 1).to()).isEqualTo(grid.goal());
        assertThat(s.trail()).as("the opener still has no ghost material of their own").isEmpty();
    }

    @Test
    void secondPlayersNeverPolluteTheRecording() {
        var s = sessions.open(mazeId, "primary", grid.start());
        sessions.join(s.id(), "sidekick", grid.start());
        Point firstStep = grid.openNeighbors(grid.start()).get(0);
        sessions.tryMove(s.id(), "sidekick", grid, firstStep);

        assertThat(s.trail())
                .as("only the opening player's steps are ghost material")
                .isEmpty();
    }
}
