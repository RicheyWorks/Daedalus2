// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.LeaderboardEntry;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Per-maze leaderboard partitioning (ADR-006 idea #4's second half): the daily challenge's
 * board is "entries whose mazeId is today's maze", so scores from other mazes must never
 * leak in — a run on an easy 5×5 has no business outranking daily runs. Pre-partition
 * entries (mazeId null) stay on the global board and appear on no maze's board.
 */
class LeaderboardPartitionTest {

    private final LeaderboardService svc = new LeaderboardService(null, false, 100);

    private static LeaderboardEntry entry(UUID mazeId, String player, long score) {
        return new LeaderboardEntry(UUID.randomUUID(), mazeId, player, score,
                10, 1000, "recursive-backtracker", Instant.now());
    }

    @Test
    void aMazesBoardContainsOnlyItsOwnRuns() {
        UUID daily = UUID.randomUUID();
        UUID other = UUID.randomUUID();
        svc.submit(entry(daily, "alice", 500));
        svc.submit(entry(other, "bob", 9000));   // higher score, different maze
        svc.submit(entry(daily, "carol", 700));
        svc.submit(new LeaderboardEntry(UUID.randomUUID(), "dave", 8000, 5, 500,
                "binary-tree", Instant.now()));   // legacy shape: no maze partition

        var board = svc.top(10, daily);

        assertThat(board).extracting(LeaderboardEntry::playerName)
                .as("bob's easier maze and dave's legacy entry must not leak into the "
                        + "daily board, however high they scored")
                .containsExactly("carol", "alice");
        assertThat(svc.top(10, null))
                .as("null partition = the global board, unchanged")
                .hasSize(4);
        assertThat(svc.top(10, UUID.randomUUID())).isEmpty();
    }
}
