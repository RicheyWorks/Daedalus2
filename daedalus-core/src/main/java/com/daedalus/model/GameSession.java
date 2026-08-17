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

    /**
     * Seats including the opening player. A session is not a lobby; eight is enough for
     * the WASD-plus-arrows UI and for a second authenticated client, and the bound is what
     * keeps {@link #join} from being an unbounded map put.
     */
    public static final int MAX_PLAYERS = 8;

    /**
     * What {@link #generatorId()} reports when nobody told the session which algorithm built
     * its maze — the legacy constructors below, and nothing else on the production path.
     *
     * <p>This constant used to be written unconditionally, three modules away, as a literal in
     * {@code GameSessionService.complete}. Every completed run reached the leaderboard claiming
     * {@code "unknown"}, which is a lie in the API response and a collapsed partition in Redis:
     * {@code LeaderboardService} keys a per-generator sorted set on this string, so every run
     * ever recorded landed in one set named after a placeholder. Carrying it on the session is
     * what makes the value true, and carrying it from <em>open</em> rather than resolving it at
     * completion is what keeps it true — a session outlives its maze in the cache by design, and
     * a finished run must still be able to say what it was played on.
     */
    public static final String UNKNOWN_GENERATOR = "unknown";

    private final UUID id;
    private final UUID mazeId;
    private final String generatorId;
    private final String playerName;
    private final String owner;
    private final ConcurrentMap<String, Point> players = new ConcurrentHashMap<>();
    /** Verified subjects allowed to SUBSCRIBE — the owner, plus anyone who joined with a token. */
    private final java.util.Set<String> subjects = ConcurrentHashMap.newKeySet();
    /**
     * Per-player hops from start. The opening player's list is also what
     * {@link #trail()} returns — ghost material stays opener-only. Joiners
     * used to be seats on the spectator snapshot: a late arrival saw them
     * teleport. Bounded per name by {@link #MAX_TRAIL}.
     */
    private final ConcurrentMap<String, java.util.List<TimedMove>> walks = new ConcurrentHashMap<>();
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
        this(mazeId, UNKNOWN_GENERATOR, playerName, start, owner);
    }

    /**
     * @param generatorId the algorithm that built this session's maze, recorded at open time.
     *                    {@link #UNKNOWN_GENERATOR} when the caller genuinely does not know;
     *                    the production path always does, because the controller has just
     *                    read the maze out of the cache to find its start cell.
     */
    public GameSession(UUID mazeId, String generatorId, String playerName, Point start,
                       String owner) {
        this.id = UUID.randomUUID();
        this.mazeId = mazeId;
        this.generatorId = generatorId == null ? UNKNOWN_GENERATOR : generatorId;
        this.playerName = playerName;
        this.owner = owner;
        this.currentPosition = start;
        this.startedAt = Instant.now();
        this.players.put(playerName, start);
        if (owner != null) {
            subjects.add(owner);
        }
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
        }
        java.util.List<TimedMove> w = walks.computeIfAbsent(player,
                p -> java.util.Collections.synchronizedList(new java.util.ArrayList<>()));
        synchronized (w) {
            if (w.size() < MAX_TRAIL) {
                w.add(new TimedMove(next,
                        java.time.Duration.between(startedAt, Instant.now()).toMillis()));
            }
        }
        this.moveCount.incrementAndGet();
    }

    /** Snapshot of the opening player's timed trail — the ghost recording. */
    public java.util.List<TimedMove> trail() {
        return walkOf(playerName);
    }

    /**
     * Every player's recorded hops, opening player included. Empty lists are
     * omitted — a seat that has not moved is just {@link #players()}.
     */
    public Map<String, java.util.List<TimedMove>> walks() {
        java.util.Map<String, java.util.List<TimedMove>> out = new java.util.LinkedHashMap<>();
        for (String name : players.keySet()) {
            java.util.List<TimedMove> w = walkOf(name);
            if (!w.isEmpty()) {
                out.put(name, w);
            }
        }
        return Map.copyOf(out);
    }

    private java.util.List<TimedMove> walkOf(String name) {
        java.util.List<TimedMove> w = walks.get(name);
        if (w == null) {
            return java.util.List.of();
        }
        synchronized (w) {
            return java.util.List.copyOf(w);
        }
    }

    /** Adds a player with no verified subject; see {@link #join(String, Point, String)}. */
    public boolean join(String player, Point start) {
        return join(player, start, null);
    }

    /**
     * Adds a player at {@code start}, keeping the existing position if the name is already
     * present. {@code subject} is the verified token subject, or {@code null} for an
     * anonymous join — only a subject is added to the STOMP allowlist. Returns {@code false}
     * when the session is already at {@link #MAX_PLAYERS} and the name is new.
     */
    public boolean join(String player, Point start, String subject) {
        if (!players.containsKey(player) && players.size() >= MAX_PLAYERS) {
            return false;
        }
        boolean added = players.putIfAbsent(player, start) == null;
        // First claimant of a display name keeps the subject. A rejoin must not let a
        // different token inherit the seat's STOMP rights by repeating the same name.
        if (added && subject != null) {
            subjects.add(subject);
        }
        return true;
    }

    /**
     * Whether {@code subject} may SUBSCRIBE to this session's player topic.
     * Unowned sessions have no claim to enforce (anyone may). Owned sessions allow the
     * owner and every subject that joined with a token; everyone else, including an
     * anonymous connection, is refused.
     */
    public boolean maySubscribe(String subject) {
        if (owner == null) {
            return true;
        }
        return subject != null && subjects.contains(subject);
    }

    public void complete(long finalScore) {
        this.completed = true;
        this.completedAt = Instant.now();
        this.score = finalScore;
    }

    public UUID id() { return id; }
    public UUID mazeId() { return mazeId; }

    /**
     * The algorithm that built this session's maze — never {@code null}, and
     * {@link #UNKNOWN_GENERATOR} only when the session was opened without it.
     */
    public String generatorId() { return generatorId; }
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
