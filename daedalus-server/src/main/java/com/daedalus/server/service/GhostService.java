// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.GameSession;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
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
 * holder). Empty trails (a session completed without recorded moves — theoretically a
 * 1×1 maze) are ignored rather than stored as degenerate ghosts.
 *
 * <p><b>Bounded</b> (house rule): one ghost per maze in a Caffeine cache
 * ({@code daedalus.ghost.max-mazes} / {@code idle-ttl}), and each recording is already
 * capped at {@link GameSession#MAX_TRAIL} moves by the model.
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

    private final Cache<UUID, GhostRun> ghosts;

    public GhostService(
            @Value("${daedalus.ghost.max-mazes:1000}") long maxMazes,
            @Value("${daedalus.ghost.idle-ttl:24h}") Duration idleTtl) {
        this.ghosts = Caffeine.newBuilder()
                .maximumSize(maxMazes)
                .expireAfterAccess(idleTtl)
                .build();
    }

    /** A completed run challenges the maze's current ghost; the higher score keeps the seat. */
    @EventListener
    public void onCompleted(SessionCompletedEvent e) {
        GameSession s = e.session();
        List<GameSession.TimedMove> trail = s.trail();
        if (trail.isEmpty()) {
            return;
        }
        GhostRun challenger = new GhostRun(s.mazeId(), s.playerName(), s.score(),
                trail.get(trail.size() - 1).tMs(), trail);
        ghosts.asMap().merge(s.mazeId(), challenger,
                (incumbent, fresh) -> fresh.score() > incumbent.score() ? fresh : incumbent);
    }

    /** The maze's ghost, or {@code null} if nobody has completed a run on it (404). */
    public GhostRun ghostOf(UUID mazeId) {
        return ghosts.getIfPresent(mazeId);
    }
}
