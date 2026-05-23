// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Instant;
import java.util.UUID;

/**
 * One playable session of a maze. Mutable — player position changes as the game progresses.
 * Stored in Redis under {@code session:{id}} for resume and replay.
 */
public class GameSession {

    private final UUID id;
    private final UUID mazeId;
    private final String playerName;
    private Point currentPosition;
    private long moveCount;
    private long score;
    private boolean completed;
    private final Instant startedAt;
    private Instant completedAt;

    public GameSession(UUID mazeId, String playerName, Point start) {
        this.id = UUID.randomUUID();
        this.mazeId = mazeId;
        this.playerName = playerName;
        this.currentPosition = start;
        this.startedAt = Instant.now();
    }

    public void move(Point next) {
        this.currentPosition = next;
        this.moveCount++;
    }

    public void complete(long finalScore) {
        this.completed = true;
        this.completedAt = Instant.now();
        this.score = finalScore;
    }

    public UUID id() { return id; }
    public UUID mazeId() { return mazeId; }
    public String playerName() { return playerName; }
    public Point currentPosition() { return currentPosition; }
    public long moveCount() { return moveCount; }
    public long score() { return score; }
    public boolean completed() { return completed; }
    public Instant startedAt() { return startedAt; }
    public Instant completedAt() { return completedAt; }
}
