// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.Point;

import java.util.UUID;

/**
 * STOMP frame published to {@code /topic/session/{id}/player} after a successful player move.
 *
 * @param sessionId id of the session the move belongs to
 * @param from      previous player position
 * @param to        new player position
 */
public record MoveFrame(UUID sessionId, Point from, Point to) {}
