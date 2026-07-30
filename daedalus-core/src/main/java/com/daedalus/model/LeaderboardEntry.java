// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Instant;
import java.util.UUID;

/**
 * @param mazeId the maze this run was played on — the partition key for per-maze boards
 *               (the daily challenge's board is "entries where mazeId = today's maze");
 *               {@code null} on entries recorded before 1.2's daily-leaderboard work
 */
public record LeaderboardEntry(
        UUID sessionId,
        UUID mazeId,
        String playerName,
        long score,
        long moveCount,
        long elapsedMs,
        String mazeGeneratorId,
        Instant achievedAt
) implements Comparable<LeaderboardEntry> {

    /** Pre-1.2 shape (no maze partition), kept for source compatibility. */
    public LeaderboardEntry(UUID sessionId, String playerName, long score, long moveCount,
                            long elapsedMs, String mazeGeneratorId, Instant achievedAt) {
        this(sessionId, null, playerName, score, moveCount, elapsedMs, mazeGeneratorId,
                achievedAt);
    }

    @Override
    public int compareTo(LeaderboardEntry other) {
        // Higher score first, then fewer moves, then faster.
        int byScore = Long.compare(other.score, this.score);
        if (byScore != 0) return byScore;
        int byMoves = Long.compare(this.moveCount, other.moveCount);
        if (byMoves != 0) return byMoves;
        return Long.compare(this.elapsedMs, other.elapsedMs);
    }
}
