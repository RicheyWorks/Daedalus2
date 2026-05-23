// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.Point;

import java.util.UUID;

/**
 * Response body for {@code POST /api/maze/{id}/session}.
 *
 * @param sessionId server-assigned session id
 * @param mazeId    id of the maze the session is bound to
 * @param position  initial player position (the maze's start cell)
 */
public record SessionResponse(UUID sessionId, UUID mazeId, Point position) {}
