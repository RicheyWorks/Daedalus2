// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.Point;

import java.util.Map;
import java.util.UUID;

/**
 * {@code GET /api/v1/session/{id}} — a read-only snapshot of a live session, the seam
 * spectator mode (ADR-006 idea #6) stands on: a spectator loads this once, then follows
 * the same {@code /topic/session/{id}/player} frames the players produce (or re-polls
 * when STOMP is unavailable). Owned sessions keep their existing STOMP authorization —
 * this endpoint exposes no more than those frames already carry.
 *
 * @param players   every player's current position, opening player included
 * @param completed true once the opening player reached the goal
 */
public record SessionViewResponse(UUID sessionId, UUID mazeId,
                                  Map<String, Point> players,
                                  boolean completed, long moveCount, long score) {}
