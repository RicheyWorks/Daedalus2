// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.UUID;

/**
 * STOMP frame published to {@code /topic/maze/{id}/state} when a maze finishes generating.
 *
 * @param mazeId      id of the newly generated maze
 * @param rows        row count
 * @param cols        column count
 * @param generatorId id of the algorithm that produced the maze (may differ from the requested id
 *                    when a circuit-breaker fallback fires)
 */
public record GeneratedFrame(UUID mazeId, int rows, int cols, String generatorId) {}
