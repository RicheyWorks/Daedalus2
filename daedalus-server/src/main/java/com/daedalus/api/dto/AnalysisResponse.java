// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.Point;
import com.daedalus.theory.MazeFlow;

import java.util.List;
import java.util.UUID;

/**
 * {@code GET /api/v1/maze/{id}/analysis} — the theory module's structural read of a maze
 * (ADR-006 idea #9), computed on the maze's <em>current</em> snapshot (so a living maze
 * analyzes differently after each erosion tick).
 *
 * @param routeLength cells on the shortest start→goal route (0 when unreachable)
 * @param cutSize     start↔goal edge connectivity — how many passages must close to sever
 *                    the route; {@code 1} on every perfect maze, higher only when braided
 * @param chokepoints the actual min-cut passages: sever these and start and goal fall into
 *                    different worlds — THE cells worth defending in any tower-defense
 *                    reading of a maze
 * @param deadEnds    cells with exactly one opening (erosion fuel, wall-follower traps)
 */
public record AnalysisResponse(UUID mazeId, int rows, int cols,
                               int routeLength, int cutSize,
                               List<MazeFlow.Passage> chokepoints,
                               int deadEndCount, List<Point> deadEnds) {
    public AnalysisResponse {
        chokepoints = chokepoints == null ? null : List.copyOf(chokepoints);
        deadEnds = deadEnds == null ? null : List.copyOf(deadEnds);
    }
}
