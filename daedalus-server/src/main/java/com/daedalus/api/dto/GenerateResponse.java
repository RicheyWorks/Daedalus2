// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.UUID;

/**
 * Response body for {@code POST /api/maze/generate} and {@code GET /api/maze/{id}}.
 *
 * <p>{@code generatorId} reflects the actual generator that produced the cached maze, which may
 * differ from the requested id when a circuit-breaker fallback fires.
 *
 * @param id          server-assigned maze id
 * @param generatorId id of the algorithm that actually produced this maze
 * @param rows        row count
 * @param cols        column count
 * @param seed        seed used to generate the maze
 * @param tiles       row-major tile glyph grid (walls, passages, start, goal)
 */
public record GenerateResponse(UUID id, String generatorId, int rows, int cols,
                               long seed, char[][] tiles) {}
