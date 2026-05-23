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

    public boolean tryMove(UUID sessionId, MazeGrid grid, Point to) {
        GameSession s = sessions.get(sessionId);
        if (s == null || s.completed()) return false;
        Point from = s.currentPosition();
        // Only allow moves into open neighbors.
        if (!grid.openNeighbors(from).contains(to)) return false;
        s.move(to);
        events.publishEvent(new PlayerMovedEvent(this, sessionId, from, to));
        if (to.equals(grid.goal())) complete(s, grid);
        return true;
    }

    private void complete(GameSession s, MazeGrid grid) {
        long elapsed = Duration.between(s.startedAt(), Instant.now()).toMillis();
        long ideal = grid.rows() + grid.cols();
        long score = Math.max(0, 100_000 - s.moveCount() * 10 - elapsed / 100);
        s.complete(score);
        leaderboard.submit(new LeaderboardEntry(
                s.id(), s.playerName(), score, s.moveCount(), elapsed,
                /* mazeGeneratorId */ "unknown", Instant.now()));
        // ideal kept for future score-tuning telemetry
        if (ideal < 0) throw new IllegalStateException("unreachable");
    }
}
