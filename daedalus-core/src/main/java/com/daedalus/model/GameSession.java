// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * One playable session of a maze. Mutable — player position changes as the game progresses.
 * Stored in Redis under {@code session:{id}} for resume and replay.
 */
public class GameSession {

    /**
     * One recorded step of the opening player, stamped relative to session start — the raw
     * material of ghost runs (ADR-006 idea #8). Millis-since-start rather than wall clock so
     * a replay needs no clock math and survives serialization trivially.
     */
    public record TimedMove(Point to, long tMs) {}

    /** Trail recording stops here — a run this long is not ghost material, and the bound
     *  keeps a pathological client from growing a session without limit. */
    public static final int MAX_TRAIL = 5_000;

    private final UUID id;
    private final UUID mazeId;
    private final String playerName;
    private final String owner;
    private final ConcurrentMap<String, Point> players = new ConcurrentHashMap<>();
    private final java.util.List<TimedMove> trail =
            java.util.Collections.synchronizedList(new java.util.ArrayList<>());
    private Point currentPosition;
    /*
     * Writes to the three fields below are serialized by GameSessionService's per-session
     * lock; the concurrency here is for the un-locked readers this class promises never see
     * corruption (the same contract that makes {@link #players} a ConcurrentMap). Without it
     * a reader can see a torn 64-bit long or a stale completed flag. moveCount is an
     * AtomicLong rather than volatile because ++ is a read-modify-write, which would silently
     * start racing if the service lock ever stopped covering every writer. The SpotBugs
     * 4.10+ AT_ and VO_ detector gates fail the build if any of this regresses.
     */
    private final AtomicLong moveCount = new AtomicLong();
    private volatile long score;
    private volatile boolean completed;
    private final Instant startedAt;
    private Instant completedAt;

    /** Anonymous session — no owner recorded; see {@link #owner()}. */
    public GameSession(UUID mazeId, String playerName, Point start) {
        this(mazeId, playerName, start, null);
    }

    /**
     * @param owner the authenticated subject this session belongs to, or {@code null} for a
     *              session opened without credentials. Distinct from {@code playerName}, which
     *              is a display string the client chooses freely — the owner is asserted by a
     *              verified token and is what authorization decisions key on.
     */
    public GameSession(UUID mazeId, String playerName, Point start, String owner) {
        this.id = UUID.randomUUID();
        this.mazeId = mazeId;
        this.playerName = playerName;
        this.owner = owner;
        this.currentPosition = start;
        this.startedAt = Instant.now();
        this.players.put(playerName, start);
    }

    /** Moves the opening player; see {@link #move(String, Point)}. */
    public void move(Point next) {
        move(playerName, next);
    }

    /**
     * Moves the named player. The opening player's position is mirrored into
     * {@link #currentPosition()} so pre-multiplayer callers observe identical behavior.
     * Compound check-then-move sequences are the caller's job to make atomic
     * ({@code GameSessionService} holds a per-session lock); this map is concurrent only so
     * un-locked readers (health details, future spectator views) never see corruption.
     */
    public void move(String player, Point next) {
        players.put(player, next);
        if (player.equals(playerName)) {
            this.currentPosition = next;
            // Only the opening player's run is ghost material; bounded by MAX_TRAIL.
            if (trail.size() < MAX_TRAIL) {
                trail.add(new TimedMove(next,
                        java.time.Duration.between(startedAt, Instant.now()).toMillis()));
            }
        }
        this.moveCount.incrementAndGet();
    }

    /** Snapshot of the opening player's timed trail — the ghost recording. */
    public java.util.List<TimedMove> trail() {
        synchronized (trail) {
            return java.util.List.copyOf(trail);
        }
    }

    /**
     * Adds a player to this session at the given start, keeping the existing position if the
     * name is already present. Multiplayer is a server-side feature flag; the model itself is
     * indifferent to how many players a session tracks.
     */
    public void join(String player, Point start) {
        players.putIfAbsent(player, start);
    }

    public void complete(long finalScore) {
        this.completed = true;
        this.completedAt = Instant.now();
        this.score = finalScore;
    }

    public UUID id() { return id; }
    public UUID mazeId() { return mazeId; }
    public String playerName() { return playerName; }
    /** Verified owner subject, or {@code null} — an unowned session carries no access claim. */
    public String owner() { return owner; }
    /** The named player's position, or {@code null} if they never joined this session. */
    public Point playerPosition(String player) { return players.get(player); }
    /** Snapshot of every player's position, opening player included. */
    public Map<String, Point> players() { return Map.copyOf(players); }
    public Point currentPosition() { return currentPosition; }
    public long moveCount() { return moveCount.get(); }
    public long score() { return score; }
    public boolean completed() { return completed; }
    public Instant startedAt() { return startedAt; }
    public Instant completedAt() { return completedAt; }
}
