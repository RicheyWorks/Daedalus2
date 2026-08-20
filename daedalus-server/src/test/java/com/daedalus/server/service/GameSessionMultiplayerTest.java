// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.GameSession;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationEventPublisher;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * Multiplayer sessions behind the {@code daedalus.session.multiplayer} flag (BACKLOG stretch
 * goal: "lift the one-player-per-session constraint behind a feature flag").
 *
 * <p>Two contracts matter equally here and each gets pinned: the flag <b>on</b> admits named
 * players with independent positions, and the flag <b>off</b> (the default) leaves every
 * pre-multiplayer behavior byte-for-byte intact — join refused, unknown player names refused,
 * the opening player moving exactly as before.
 */
class GameSessionMultiplayerTest {

    private LeaderboardService leaderboard;
    private List<PlayerMovedEvent> published;
    private MazeGrid grid;

    @BeforeEach
    void setUp() {
        leaderboard = mock(LeaderboardService.class);
        published = new ArrayList<>();
        grid = new RecursiveBacktrackerGenerator().generate(8, 8, 7L, new MazeStats());
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(7, 7));
    }

    private GameSessionService service(boolean multiplayer) {
        ApplicationEventPublisher capture = event -> {
            if (event instanceof PlayerMovedEvent moved) {
                published.add(moved);
            }
        };
        return new GameSessionService(capture, leaderboard, multiplayer);
    }

    // ------------------------------------------------------------------
    // Flag off: the pre-multiplayer world, unchanged
    // ------------------------------------------------------------------

    @Test
    void withTheFlagOffJoinIsRefused() {
        GameSessionService svc = service(false);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        assertThat(svc.join(s.id(), "Bob", grid.start())).isNull();
        assertThat(s.players()).containsOnlyKeys("Alice");
    }

    @Test
    void withTheFlagOffTheOpeningPlayerMovesExactlyAsBefore() {
        GameSessionService svc = service(false);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        Point to = grid.openNeighbors(grid.start()).get(0);

        assertThat(svc.tryMove(s.id(), grid, to)).isTrue();
        assertThat(s.currentPosition()).isEqualTo(to);
        assertThat(s.moveCount()).isEqualTo(1);
        assertThat(published).hasSize(1);
        assertThat(published.get(0).player()).isEqualTo("Alice");
    }

    @Test
    void aPlayerNameThatNeverJoinedCannotBeMovedIntoExistence() {
        GameSessionService svc = service(true);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        Point to = grid.openNeighbors(grid.start()).get(0);

        assertThat(svc.tryMove(s.id(), "Bob", grid, to)).isFalse();
        assertThat(s.players()).containsOnlyKeys("Alice");
        assertThat(published).isEmpty();
    }

    // ------------------------------------------------------------------
    // Flag on: independent players in one session
    // ------------------------------------------------------------------

    @Test
    void joinedPlayersHaveIndependentPositions() {
        GameSessionService svc = service(true);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        assertThat(svc.join(s.id(), "Bob", grid.start())).isSameAs(s);

        Point aliceTo = grid.openNeighbors(grid.start()).get(0);
        assertThat(svc.tryMove(s.id(), "Alice", grid, aliceTo)).isTrue();

        // Bob is still at start — Alice's move must not drag him along.
        assertThat(s.playerPosition("Bob")).isEqualTo(grid.start());
        assertThat(s.playerPosition("Alice")).isEqualTo(aliceTo);
        // And Bob moves from HIS position, not Alice's.
        Point bobTo = grid.openNeighbors(grid.start()).get(0);
        assertThat(svc.tryMove(s.id(), "Bob", grid, bobTo)).isTrue();
        assertThat(s.playerPosition("Bob")).isEqualTo(bobTo);

        assertThat(s.moveCount()).isEqualTo(2);
        assertThat(published).extracting(PlayerMovedEvent::player)
                .containsExactly("Alice", "Bob");
        assertThat(s.walks()).containsOnlyKeys("Alice", "Bob");
        assertThat(s.trail()).extracting(GameSession.TimedMove::to).containsExactly(aliceTo);
        assertThat(s.walks().get("Bob")).extracting(GameSession.TimedMove::to).containsExactly(bobTo);
    }

    @Test
    void rejoiningKeepsThePlayersPositionInsteadOfTeleportingToStart() {
        GameSessionService svc = service(true);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        svc.join(s.id(), "Bob", grid.start());
        Point bobTo = grid.openNeighbors(grid.start()).get(0);
        svc.tryMove(s.id(), "Bob", grid, bobTo);

        // Bob's client reconnects and joins again.
        assertThat(svc.join(s.id(), "Bob", grid.start())).isSameAs(s);
        assertThat(s.playerPosition("Bob")).isEqualTo(bobTo);
    }

    @Test
    void anyPlayerReachingTheGoalCompletesTheSessionExactlyOnce() {
        GameSessionService svc = service(true);
        Point nextToGoal = grid.openNeighbors(grid.goal()).get(0);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        svc.join(s.id(), "Bob", nextToGoal);

        assertThat(svc.tryMove(s.id(), "Bob", grid, grid.goal())).isTrue();
        assertThat(s.completed()).isTrue();
        assertThat(s.completedBy()).isEqualTo("Bob");
        ArgumentCaptor<LeaderboardEntry> submitted = ArgumentCaptor.forClass(LeaderboardEntry.class);
        verify(leaderboard, times(1)).submit(submitted.capture());
        assertThat(submitted.getValue().playerName())
                .as("a joiner finish must not be credited to the opener")
                .isEqualTo("Bob");
        assertThat(submitted.getValue().moveCount()).isEqualTo(1);

        // Completion freezes the whole session, opening player included.
        assertThat(svc.tryMove(s.id(), "Alice",
                grid, grid.openNeighbors(grid.start()).get(0))).isFalse();
        assertThat(svc.join(s.id(), "Carol", grid.start())).isNull();
    }

    @Test
    void joiningAnUnknownSessionIsRefused() {
        GameSessionService svc = service(true);
        assertThat(svc.join(UUID.randomUUID(), "Bob", grid.start())).isNull();
    }

    @Test
    void aFullSessionRefusesANewName() {
        GameSessionService svc = service(true);
        GameSession s = svc.open(UUID.randomUUID(), "Alice", grid.start());
        for (int i = 1; i < GameSession.MAX_PLAYERS; i++) {
            assertThat(svc.join(s.id(), "p" + i, grid.start())).isSameAs(s);
        }
        assertThat(svc.join(s.id(), "overflow", grid.start())).isNull();
        assertThat(s.players()).hasSize(GameSession.MAX_PLAYERS);
        assertThat(svc.join(s.id(), "p1", grid.start())).isSameAs(s);
    }

    @Test
    void anAuthenticatedJoinRecordsTheSubjectOnTheAllowlist() {
        GameSessionService svc = service(true);
        GameSession s = svc.open(UUID.randomUUID(), "recursive-backtracker",
                "Alice", grid.start(), "alice");
        assertThat(svc.join(s.id(), "Bob", grid.start(), "bob")).isSameAs(s);
        assertThat(s.maySubscribe("bob")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
    }
}
