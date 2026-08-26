// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.GameSession;
import com.daedalus.model.Point;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * {@code GET /api/v1/session/{id}} — a read-only snapshot of a live session, the seam
 * spectator mode (ADR-006 idea #6) stands on: a spectator loads this once, then follows
 * the same {@code /topic/session/{id}/player} frames the players produce (or re-polls
 * when STOMP is unavailable). Owned sessions keep their existing STOMP authorization.
 *
 * <p>Positions alone are not enough to paint a walk. Frames carry one hop; a late
 * spectator arriving mid-run would otherwise see a marker with no corridor. {@code trail}
 * is the opening player's recorded {@link GameSession.TimedMove} list — the same
 * material a completed run becomes a ghost from. Subjects stay off this record.
 *
 * @param sessionId the live session
 * @param mazeId    the maze that session is playing
 * @param player    the opening player's display name — whose trail this is
 * @param players   every player's current position, opening player included
 * @param completed true once any seat reached the goal
 * @param completedBy the seat that finished, or {@code null} while the session is open
 * @param moveCount steps taken (any player)
 * @param score     current score
 * @param trail     opening-player hops from start, empty before the first move
 * @param walks     every player's recorded hops; the opener's list is {@code trail}.
 *                  A late spectator used to see joiners teleport.
 */
public record SessionViewResponse(UUID sessionId, UUID mazeId, String player,
                                  Map<String, Point> players,
                                  boolean completed, long moveCount, long score,
                                  List<GameSession.TimedMove> trail,
                                  Map<String, List<GameSession.TimedMove>> walks,
                                  String completedBy) {
    public SessionViewResponse {
        players = players == null ? null : Map.copyOf(players);
        trail = trail == null ? null : List.copyOf(trail);
        walks = copyWalks(walks);
    }

    private static Map<String, List<GameSession.TimedMove>> copyWalks(
            Map<String, List<GameSession.TimedMove>> walks) {
        if (walks == null) {
            return null;
        }
        HashMap<String, List<GameSession.TimedMove>> copy = new HashMap<>();
        walks.forEach((name, hops) -> copy.put(name, hops == null ? List.of() : List.copyOf(hops)));
        return Map.copyOf(copy);
    }

    /** Pre-winner-name shape. */
    public SessionViewResponse(UUID sessionId, UUID mazeId, String player,
                               Map<String, Point> players,
                               boolean completed, long moveCount, long score,
                               List<GameSession.TimedMove> trail,
                               Map<String, List<GameSession.TimedMove>> walks) {
        this(sessionId, mazeId, player, players, completed, moveCount, score, trail, walks,
                completed ? player : null);
    }
}
