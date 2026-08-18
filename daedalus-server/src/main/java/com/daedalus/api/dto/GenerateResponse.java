// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;
import java.util.UUID;

/**
 * Response body for {@code POST /api/v1/maze/generate} and {@code GET /api/v1/maze/{id}}.
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
 * @param hotspots    the weighted cells applied to this maze, echoed so clients can shade
 *                    them; omitted entirely for uniform-cost mazes (the pre-hotspot shape)
 * @param braid       generate-time dead-end opening factor; omitted when none was applied.
 *                    A living tick may open more walls; this is still the factor the maze
 *                    was born with, so {@code GET /maze/{id}} can label a permalink without
 *                    guessing from a UI select
 */
@com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
public record GenerateResponse(UUID id, String generatorId, int rows, int cols,
                               long seed, char[][] tiles, List<Hotspot> hotspots, Double braid) {
    /** Uniform-cost, unbraided shape — neither optional field in the JSON. */
    public GenerateResponse(UUID id, String generatorId, int rows, int cols,
                            long seed, char[][] tiles) {
        this(id, generatorId, rows, cols, seed, tiles, null, null);
    }

    /** Weighted, unbraided — the pre-braid-echo shape. */
    public GenerateResponse(UUID id, String generatorId, int rows, int cols,
                            long seed, char[][] tiles, List<Hotspot> hotspots) {
        this(id, generatorId, rows, cols, seed, tiles, hotspots, null);
    }
}
