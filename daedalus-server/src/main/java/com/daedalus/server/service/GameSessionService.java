// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.GameSession;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Ticker;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;


/** Active game sessions: open, move, complete. */
@Service
public class GameSessionService {

    /**
     * Join refused because the session finished or is at {@link GameSession#MAX_PLAYERS}.
     * Those used to be the same empty 409, so a client could not tell wait from give up.
     */
    public static final class JoinRefusedException extends RuntimeException {
        public enum Reason { COMPLETED, FULL }

        private final Reason reason;

        JoinRefusedException(Reason reason) {
            super(reason == Reason.COMPLETED
                    ? "This session is already finished."
                    : "This session is full (" + GameSession.MAX_PLAYERS + " players).");
            this.reason = reason;
        }

        public Reason reason() {
            return reason;
        }
    }

    private final ApplicationEventPublisher events;
    private final LeaderboardService leaderboard;
    private final boolean multiplayer;
    private final Cache<UUID, GameSession> sessions;

    /** Single-player service (multiplayer flag off) — the pre-flag behavior, kept for tests. */
    public GameSessionService(ApplicationEventPublisher events, LeaderboardService leaderboard) {
        this(events, leaderboard, false);
    }

    /** Default session-store bounds — see the five-arg constructor. */
    public GameSessionService(ApplicationEventPublisher events,
                              LeaderboardService leaderboard,
                              boolean multiplayer) {
        this(events, leaderboard, multiplayer, 10_000, Duration.ofHours(2));
    }

    /**
     * @param multiplayer the {@code daedalus.session.multiplayer} feature flag (BACKLOG stretch
     *                    goal, default {@code false}): when on, {@link #join} admits additional
     *                    named players into an existing session. Off, sessions behave exactly
     *                    as before the flag existed.
     * @param maxSessions bound on live sessions
     * @param idleTtl     eviction after inactivity. Sessions previously lived in an unbounded
     *                    {@code ConcurrentHashMap} and were never removed — not even after
     *                    completion — so every session ever opened stayed resident for the
     *                    life of the process. An evicted session simply answers 404 on its
     *                    next move, which is the API's existing "unknown session" path; the
     *                    idle TTL far outlives any game actually being played. Configurable
     *                    via {@code daedalus.session.*}.
     */
    @Autowired
    public GameSessionService(ApplicationEventPublisher events,
                              LeaderboardService leaderboard,
                              @Value("${daedalus.session.multiplayer:false}") boolean multiplayer,
                              @Value("${daedalus.session.max-sessions:10000}") long maxSessions,
                              @Value("${daedalus.session.idle-ttl:2h}") Duration idleTtl) {
        this(events, leaderboard, multiplayer, maxSessions, idleTtl, Ticker.systemTicker());
    }

    /**
     * Ticker seam, same shape as {@code PerKeyRateLimitInterceptor}'s and for the same reason:
     * the idle TTL is a promise about the passage of time, and a test that cannot move time can
     * only assert that the builder was called. {@code BoundedStoresTest} pinned
     * {@code maximumSize} and — reflectively — that every cache in the server declares one, but
     * nothing advanced a clock, so deleting {@code expireAfterAccess} left the suite green. Size
     * and idle are two separate bounds; only one of them was checked.
     */
    GameSessionService(ApplicationEventPublisher events,
                       LeaderboardService leaderboard,
                       boolean multiplayer,
                       long maxSessions,
                       Duration idleTtl,
                       Ticker ticker) {
        this.events = events;
        this.leaderboard = leaderboard;
        this.multiplayer = multiplayer;
        this.sessions = Caffeine.newBuilder()
                .maximumSize(maxSessions)
                .expireAfterAccess(idleTtl)
                .ticker(ticker)
                .build();
    }

    /** Whether the {@code daedalus.session.multiplayer} flag is on. */
    public boolean multiplayerEnabled() { return multiplayer; }

    /** Opens an anonymous (unowned) session; see {@link #open(UUID, String, Point, String)}. */
    public GameSession open(UUID mazeId, String playerName, Point start) {
        return open(mazeId, playerName, start, null);
    }

    /** Opens a session whose maze's generator is not known to the caller. */
    public GameSession open(UUID mazeId, String playerName, Point start, String owner) {
        return open(mazeId, GameSession.UNKNOWN_GENERATOR, playerName, start, owner);
    }

    /**
     * @param generatorId the algorithm that built the maze, recorded now rather than looked up
     *                    at completion. The controller already holds it — it has just read the
     *                    maze out of the cache for its start cell — and resolving it later is
     *                    unsound: a session is allowed to outlive its maze's cache entry, which
     *                    this class handles explicitly elsewhere, so a completion-time lookup
     *                    would put a placeholder on exactly the long games most worth recording.
     * @param owner       verified subject from the caller's token, or {@code null} when the
     *                    request carried no credentials. Recorded at open and immutable. STOMP
     *                    subscription authorization admits this subject and anyone who later
     *                    joins with a token via {@link #join} (ADR-012).
     */
    public GameSession open(UUID mazeId, String generatorId, String playerName, Point start,
                            String owner) {
        GameSession session = new GameSession(mazeId, generatorId, playerName, start, owner);
        sessions.put(session.id(), session);
        return session;
    }

    public GameSession find(UUID id) { return sessions.getIfPresent(id); }

    /**
     * Adds a named player to an existing session (multiplayer flag only).
     *
     * @return the session on success; {@code null} when the flag is off or the session is
     *         unknown. A finished session and a full session throw
     *         {@link JoinRefusedException} — those used to be the same {@code null}, so the
     *         controller could only answer an empty 409. Joining under a name already present
     *         succeeds and keeps that player's current position — rejoin after a dropped
     *         connection must not teleport anyone back to start.
     */
    public GameSession join(UUID sessionId, String player, Point start) {
        return join(sessionId, player, start, null);
    }

    /**
     * @param subject verified token subject, or {@code null} for an anonymous join.
     *                A subject is added to the session's STOMP allowlist so a second
     *                authenticated client can SUBSCRIBE to {@code /topic/session/{id}/player}.
     *                An anonymous join still gets a seat on the board; it does not get the feed
     *                of an owned session — that is the existing owner-only rule, extended
     *                rather than replaced.
     */
    public GameSession join(UUID sessionId, String player, Point start, String subject) {
        if (!multiplayer) return null;
        GameSession s = sessions.getIfPresent(sessionId);
        if (s == null) return null;
        synchronized (s) {
            if (s.completed()) {
                throw new JoinRefusedException(JoinRefusedException.Reason.COMPLETED);
            }
            if (!s.join(player, start, subject)) {
                throw new JoinRefusedException(JoinRefusedException.Reason.FULL);
            }
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
        return tryMove(sessionId, null, grid, to, null);
    }

    /**
     * Per-player variant: {@code player} names who is moving; {@code null} means the opening
     * player (the pre-multiplayer contract). A name that never joined is refused — a client
     * cannot conjure a player into a session by moving them.
     */
    public boolean tryMove(UUID sessionId, String player, MazeGrid grid, Point to) {
        return tryMove(sessionId, player, grid, to, null);
    }

    /**
     * @param mazes when non-null, the maze is re-read inside the session lock so a
     *              living tick cannot accept a sealed wall or refuse a newly opened one
     */
    public boolean tryMove(UUID sessionId, String player, MazeGrid grid, Point to,
                           MazeGenerationService mazes) {
        GameSession s = sessions.getIfPresent(sessionId);
        if (s == null) return false;
        synchronized (s) {
            if (s.completed()) return false;
            String actor = (player == null) ? s.playerName() : player;
            Point from = s.playerPosition(actor);
            if (from == null) return false;
            // Re-read inside the lock when a live cache is provided. The controller
            // found a snapshot, then waited for this lock; a living tick can
            // replace() the grid in that window. Agent steps already re-read
            // inside computeIfPresent. Tests keep passing a fixture grid.
            MazeGrid live = grid;
            if (mazes != null) {
                MazeGenerationService.Cached cached = mazes.find(s.mazeId());
                if (cached == null) {
                    return false;
                }
                live = cached.grid();
            }
            if (!live.openNeighbors(from).contains(to)) return false;
            s.move(actor, to);
            // Published inside the lock so events observe the same order the moves were
            // applied in — listeners were already invoked inline by publishEvent before
            // this lock existed, so no new reentrancy is introduced.
            //
            // What that costs, measured rather than assumed (21x21 maze, warmed): a move is
            // ~1.4us with no listeners and ~1.3us with traffic tracking on, i.e. the in-tree
            // listeners are free within noise. The cost that matters is any listener that
            // BLOCKS, because it blocks while holding this lock: a 60ms listener serialises
            // that session's next ten moves into 579ms. What makes that acceptable is the lock
            // being per session — a blocked listener cannot delay any other player, verified
            // in SessionLockIsolationTest, which is also the only thing standing between this
            // design and someone widening the lock. Widen it and one slow plugin queues the
            // whole server.
            //
            // Listeners are therefore on the request path by design. A listener that needs to
            // do slow or I/O-bound work should hand off to its own executor rather than
            // borrowing this thread.
            events.publishEvent(new PlayerMovedEvent(this, sessionId, actor, from, to));
            if (to.equals(live.goal())) complete(s, live, actor);
            return true;
        }
    }

    private void complete(GameSession s, MazeGrid grid, String winner) {
        long elapsed = Duration.between(s.startedAt(), Instant.now()).toMillis();
        // The winner's hops, not every seat's. moveCount() sums joiners and
        // would make a two-player finish look worse than it was.
        long hops = s.walkOf(winner).size();
        // Score formula ignores maze size for now; if size-normalized scoring
        // lands, the ideal-path baseline is grid.rows() + grid.cols().
        long score = Math.max(0, 100_000 - hops * 10 - elapsed / 100);
        s.complete(score, winner);
        // This argument was the literal "unknown" until a live probe read it back off the API.
        // Two things were wrong with that and only one of them was visible: the response field
        // was false on every run, and LeaderboardService keys its per-generator sorted set on
        // this string, so every run ever completed collapsed into one partition named after the
        // placeholder. No test caught it because every test built its own LeaderboardEntry —
        // the production value was the one value the suite never looked at.
        leaderboard.submit(new LeaderboardEntry(
                s.id(), s.mazeId(), winner, score, hops, elapsed,
                s.generatorId(), Instant.now()));
        // Inline like PlayerMovedEvent — listeners observe completion in move order.
        events.publishEvent(new com.daedalus.plugin.events.SessionCompletedEvent(this, s));
    }
}
