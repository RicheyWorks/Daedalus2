// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Instant;
import java.util.UUID;

public record LeaderboardEntry(
        UUID sessionId,
        String playerName,
        long score,
        long moveCount,
        long elapsedMs,
        String mazeGeneratorId,
        Instant achievedAt
) implements Comparable<LeaderboardEntry> {

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
