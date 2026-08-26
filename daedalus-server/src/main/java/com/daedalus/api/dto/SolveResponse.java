// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.Point;

import java.util.List;

/**
 * Response body for {@code POST /api/v1/maze/{id}/solve/{solverId}}.
 *
 * @param solverId  id of the solver that produced the run
 * @param path      ordered sequence of grid points from start to goal (empty when {@code success=false})
 * @param visited   number of cells the solver visited
 * @param explored  number of cells the solver expanded / explored
 * @param elapsedMs wall-clock duration of the solve in milliseconds
 * @param success   whether the solver actually reached the goal
 * @param expansions search-expansion order for replay/animation — present only when the
 *                   caller asked for it ({@code ?replay=true}); empty for solvers that are
 *                   off the graph seam (IDA*, wall follower) and so have nothing recorded
 */
@com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
public record SolveResponse(String solverId, List<Point> path,
                             long visited, long explored, long elapsedMs, boolean success,
                             List<Point> expansions) {
    public SolveResponse {
        path = path == null ? null : List.copyOf(path);
        expansions = expansions == null ? null : List.copyOf(expansions);
    }

    /** Pre-replay shape — no expansion data, omitted from the JSON entirely. */
    public SolveResponse(String solverId, List<Point> path,
                         long visited, long explored, long elapsedMs, boolean success) {
        this(solverId, path, visited, explored, elapsedMs, success, null);
    }
}
