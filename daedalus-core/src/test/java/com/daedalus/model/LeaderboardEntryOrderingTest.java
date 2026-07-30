// SPDX-License-Identifier: MIT

package com.daedalus.model;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link LeaderboardEntry}'s natural order — best run first, then fewest moves, then fastest.
 *
 * <p>This test exists because of where it was missing. A mutation pass that inverted
 * {@code compareTo} so the leaderboard ranked <em>worst</em>-first left
 * {@code mvn -pl daedalus-core test} completely green: the comparator lives in core, but every
 * test of it lived in the server module. The guarantee was pinned overall, and not at all from
 * the module a developer iterating on core actually runs. A record that defines an ordering
 * should defend that ordering itself.
 */
class LeaderboardEntryOrderingTest {

    private static LeaderboardEntry entry(long score, long moves, long elapsedMs) {
        return new LeaderboardEntry(UUID.randomUUID(), UUID.randomUUID(), "p", score, moves,
                elapsedMs, "recursive-backtracker", Instant.now());
    }

    @Test
    void higherScoreRanksFirst() {
        List<LeaderboardEntry> board = new ArrayList<>(List.of(
                entry(500, 10, 1000), entry(9000, 10, 1000), entry(700, 10, 1000)));
        board.sort(null); // natural order

        assertThat(board).extracting(LeaderboardEntry::score)
                .as("a leaderboard that puts low scores on top is not a leaderboard")
                .containsExactly(9000L, 700L, 500L);
    }

    @Test
    void tiesBreakOnFewerMovesThenFasterTime() {
        LeaderboardEntry manyMoves = entry(1000, 50, 500);
        LeaderboardEntry fewMoves = entry(1000, 20, 900);
        LeaderboardEntry sameMovesSlower = entry(1000, 20, 1500);

        List<LeaderboardEntry> board = new ArrayList<>(
                List.of(sameMovesSlower, manyMoves, fewMoves));
        board.sort(null);

        assertThat(board).containsExactly(fewMoves, sameMovesSlower, manyMoves);
    }

    @Test
    void theOrderingIsConsistentWithItself() {
        LeaderboardEntry a = entry(900, 10, 100);
        LeaderboardEntry b = entry(800, 10, 100);
        assertThat(a.compareTo(b)).isNegative();
        assertThat(b.compareTo(a)).isPositive();
        assertThat(a.compareTo(a)).isZero();
    }
}
