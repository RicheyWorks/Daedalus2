// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Instant;
import java.util.Comparator;
import java.util.Objects;
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
        // Higher score first, then fewer moves, then faster. Identity last —
        // ConcurrentSkipListSet treats compareTo == 0 as the same member, so
        // two sessions that tied on the score tuple used to collapse into one row.
        int byScore = Long.compare(other.score, this.score);
        if (byScore != 0) return byScore;
        int byMoves = Long.compare(this.moveCount, other.moveCount);
        if (byMoves != 0) return byMoves;
        int byTime = Long.compare(this.elapsedMs, other.elapsedMs);
        if (byTime != 0) return byTime;
        int bySession = Objects.compare(sessionId, other.sessionId, nullsLast());
        if (bySession != 0) return bySession;
        int byMaze = Objects.compare(mazeId, other.mazeId, nullsLast());
        if (byMaze != 0) return byMaze;
        int byName = Objects.compare(playerName, other.playerName, nullsLast());
        if (byName != 0) return byName;
        int byGen = Objects.compare(mazeGeneratorId, other.mazeGeneratorId, nullsLast());
        if (byGen != 0) return byGen;
        return Objects.compare(achievedAt, other.achievedAt, nullsLast());
    }

    private static <T extends Comparable<T>> Comparator<T> nullsLast() {
        return Comparator.nullsLast(Comparator.naturalOrder());
    }
}
