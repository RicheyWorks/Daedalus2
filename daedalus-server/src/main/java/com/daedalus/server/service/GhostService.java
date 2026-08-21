// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.GameSession;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Ticker;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;

import com.daedalus.plugin.events.SessionCompletedEvent;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

/**
 * Ghost runs (ADR-006 idea #8): the best completed run per maze, kept as a timed move
 * recording. A new session on the same maze replays it as a translucent racer — you play
 * against the best real run this server has seen, with its actual pacing (hesitations
 * included; that is what makes ghosts fun to beat).
 *
 * <p>Only completed runs qualify — an abandoned wander is not a ghost — and "best" means
 * highest score (the same ordering the leaderboard uses, so the ghost IS the local record
 * holder). Empty walks (a session completed without recorded moves — theoretically a
 * 1×1 maze) are ignored rather than stored as degenerate ghosts. The recording is
 * the seat that stepped on the goal, not always the opener.
 *
 * <p><b>Bounded</b> (house rule): one ghost per maze in a Caffeine cache
 * ({@code daedalus.ghost.max-mazes} / {@code idle-ttl}), and each recording is already
 * capped at {@link GameSession#MAX_TRAIL} moves by the model. A finish on a maze
 * that is not already seated, at cap, is dropped rather than LRU-evicting a
 * recording someone is still racing or spectating. Finish cannot 409 — the
 * session already completed. An existing seat still merges the higher score.
 * Idle TTL still evicts abandoned recordings.
 */
@Service
public class GhostService {

    /**
     * A stored ghost: who, how well, and the timed steps to replay.
     *
     * @param elapsedMs wall-clock duration of the recorded run (last move's stamp)
     */
    public record GhostRun(UUID mazeId, String playerName, long score,
                           long elapsedMs, List<GameSession.TimedMove> moves) {}

    private final long maxMazes;
    private final Cache<UUID, GhostRun> ghosts;
    /**
     * Serialises first-insert against the cap. Caffeine {@code merge} at
     * {@code maximumSize} evicts LRU, so a finish on a new maze used to drop
     * another maze's ghost while someone was still racing or spectating it.
     * Living, traffic, session, walk, and maze refuse at cap under this lock.
     * A completed run cannot 409 — the move already happened — so a new maze
     * at cap drops this ghost instead of an in-use one. Idle TTL still evicts
     * abandoned recordings. An existing seat still merges.
     */
    private final Object admission = new Object();

    @Autowired
    public GhostService(
            @Value("${daedalus.ghost.max-mazes:1000}") long maxMazes,
            @Value("${daedalus.ghost.idle-ttl:24h}") Duration idleTtl) {
        this(maxMazes, idleTtl, Ticker.systemTicker());
    }

    /**
     * Ticker seam — see {@code BoundedStoresTest.everyCacheWithAnIdleTtlExposesASeamForMovingTheClock}
     * for why every idle-bounded store in this package now has one. Short version: deleting
     * {@code expireAfterAccess} from three different services on three different days left the
     * suite green each time, because no test could move a clock.
     */
    GhostService(long maxMazes, Duration idleTtl, Ticker ticker) {
        this.maxMazes = maxMazes;
        this.ghosts = Caffeine.newBuilder()
                .maximumSize(maxMazes)
                .expireAfterAccess(idleTtl)
                .ticker(ticker)
                .build();
    }

    /** A completed run challenges the maze's current ghost; the higher score keeps the seat. */
    @EventListener
    public void onCompleted(SessionCompletedEvent e) {
        GameSession s = e.session();
        String who = s.completedBy();
        List<GameSession.TimedMove> trail = s.walkOf(who);
        if (trail.isEmpty()) {
            return;
        }
        GhostRun challenger = new GhostRun(s.mazeId(), who, s.score(),
                trail.get(trail.size() - 1).tMs(), trail);
        synchronized (admission) {
            ghosts.cleanUp();
            if (ghosts.getIfPresent(s.mazeId()) == null
                    && ghosts.asMap().size() >= maxMazes) {
                return;
            }
            ghosts.asMap().merge(s.mazeId(), challenger,
                    (incumbent, fresh) -> fresh.score() > incumbent.score() ? fresh : incumbent);
        }
    }

    /**
     * Ghosts currently held — for tests and metrics, the window {@code trackedCount},
     * {@code liveCount} and {@code plannedCount} open onto their own stores. A store's bounds
     * are only as good as someone's ability to observe them working.
     */
    public long ghostCount() {
        ghosts.cleanUp();
        return ghosts.estimatedSize();
    }

    /** The maze's ghost, or {@code null} if nobody has completed a run on it (404). */
    public GhostRun ghostOf(UUID mazeId) {
        return ghosts.getIfPresent(mazeId);
    }
}
