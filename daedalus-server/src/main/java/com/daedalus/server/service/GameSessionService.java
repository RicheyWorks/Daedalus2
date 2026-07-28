// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.GameSession;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
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
    private final ConcurrentMap<UUID, GameSession> sessions = new ConcurrentHashMap<>();

    public GameSessionService(ApplicationEventPublisher events, LeaderboardService leaderboard) {
        this.events = events;
        this.leaderboard = leaderboard;
    }

    public GameSession open(UUID mazeId, String playerName, Point start) {
        GameSession session = new GameSession(mazeId, playerName, start);
        sessions.put(session.id(), session);
        return session;
    }

    public GameSession find(UUID id) { return sessions.get(id); }

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
        GameSession s = sessions.get(sessionId);
        if (s == null) return false;
        synchronized (s) {
            if (s.completed()) return false;
            Point from = s.currentPosition();
            // Only allow moves into open neighbors.
            if (!grid.openNeighbors(from).contains(to)) return false;
            s.move(to);
            // Published inside the lock so events observe the same order the moves were
            // applied in — listeners were already invoked inline by publishEvent before
            // this lock existed, so no new reentrancy is introduced.
            events.publishEvent(new PlayerMovedEvent(this, sessionId, from, to));
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
