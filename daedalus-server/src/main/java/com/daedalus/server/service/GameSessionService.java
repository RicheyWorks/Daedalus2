// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.GameSession;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/** Active game sessions: open, move, complete. */
@Service
public class GameSessionService {

    private final ApplicationEventPublisher events;
    private final LeaderboardService leaderboard;
    private final boolean multiplayer;
    private final ConcurrentMap<UUID, GameSession> sessions = new ConcurrentHashMap<>();

    /** Single-player service (multiplayer flag off) — the pre-flag behavior, kept for tests. */
    public GameSessionService(ApplicationEventPublisher events, LeaderboardService leaderboard) {
        this(events, leaderboard, false);
    }

    /**
     * @param multiplayer the {@code daedalus.session.multiplayer} feature flag (BACKLOG stretch
     *                    goal, default {@code false}): when on, {@link #join} admits additional
     *                    named players into an existing session. Off, sessions behave exactly as
     *                    before the flag existed.
     */
    @Autowired
    public GameSessionService(ApplicationEventPublisher events,
                              LeaderboardService leaderboard,
                              @Value("${daedalus.session.multiplayer:false}") boolean multiplayer) {
        this.events = events;
        this.leaderboard = leaderboard;
        this.multiplayer = multiplayer;
    }

    /** Whether the {@code daedalus.session.multiplayer} flag is on. */
    public boolean multiplayerEnabled() { return multiplayer; }

    /** Opens an anonymous (unowned) session; see {@link #open(UUID, String, Point, String)}. */
    public GameSession open(UUID mazeId, String playerName, Point start) {
        return open(mazeId, playerName, start, null);
    }

    /**
     * @param owner verified subject from the caller's token, or {@code null} when the request
     *              carried no credentials. Recorded at open and immutable — this is what STOMP
     *              subscription authorization keys on (BACKLOG: per-destination rules).
     */
    public GameSession open(UUID mazeId, String playerName, Point start, String owner) {
        GameSession session = new GameSession(mazeId, playerName, start, owner);
        sessions.put(session.id(), session);
        return session;
    }

    public GameSession find(UUID id) { return sessions.get(id); }

    /**
     * Adds a named player to an existing session (multiplayer flag only).
     *
     * @return the session on success; {@code null} when the flag is off, the session is
     *         unknown, or the session already completed. Joining under a name already present
     *         succeeds and keeps that player's current position — rejoin after a dropped
     *         connection must not teleport anyone back to start.
     */
    public GameSession join(UUID sessionId, String player, Point start) {
        if (!multiplayer) return null;
        GameSession s = sessions.get(sessionId);
        if (s == null) return null;
        synchronized (s) {
            if (s.completed()) return null;
            s.join(player, start);
        }
        return s;
    }

    /**
     * Attempt a move; returns {@code false} for unknown/completed sessions and illegal steps.
     *
     * <p>The check-then-act sequence (read position, validate against the grid, write position)
     * is guarded by a per-session lock: {@code ConcurrentHashMap} protects the <em>map</em>, not
     * compound operations on one {@link GameSession}, and concurrent access to a single session
     * is realistic — two tabs, a reconnect race. Without the lock, two racing moves could both
     * validate against the same stale position and produce an illegal transition, a lost
     * {@code moveCount} increment, or a double completion (two leaderboard entries for one win).
     * The lock is per session, so distinct sessions never contend. Pinned by
     * {@code GameSessionServiceConcurrencyTest}; this guard becomes ownership-critical the
     * moment session-ownership modelling lands (TESTING.md, gap P3).
     */
    public boolean tryMove(UUID sessionId, MazeGrid grid, Point to) {
        return tryMove(sessionId, null, grid, to);
    }

    /**
     * Per-player variant: {@code player} names who is moving; {@code null} means the opening
     * player (the pre-multiplayer contract). A name that never joined is refused — a client
     * cannot conjure a player into a session by moving them.
     */
    public boolean tryMove(UUID sessionId, String player, MazeGrid grid, Point to) {
        GameSession s = sessions.get(sessionId);
        if (s == null) return false;
        synchronized (s) {
            if (s.completed()) return false;
            String actor = (player == null) ? s.playerName() : player;
            Point from = s.playerPosition(actor);
            if (from == null) return false;
            // Only allow moves into open neighbors.
            if (!grid.openNeighbors(from).contains(to)) return false;
            s.move(actor, to);
            // Published inside the lock so events observe the same order the moves were
            // applied in — listeners were already invoked inline by publishEvent before
            // this lock existed, so no new reentrancy is introduced.
            events.publishEvent(new PlayerMovedEvent(this, sessionId, actor, from, to));
            if (to.equals(grid.goal())) complete(s, grid);
            return true;
        }
    }

    private void complete(GameSession s, MazeGrid grid) {
        long elapsed = Duration.between(s.startedAt(), Instant.now()).toMillis();
        // Score formula ignores maze size for now; if size-normalized scoring
        // lands, the ideal-path baseline is grid.rows() + grid.cols().
        long score = Math.max(0, 100_000 - s.moveCount() * 10 - elapsed / 100);
        s.complete(score);
        leaderboard.submit(new LeaderboardEntry(
                s.id(), s.playerName(), score, s.moveCount(), elapsed,
                /* mazeGeneratorId */ "unknown", Instant.now()));
    }
}
