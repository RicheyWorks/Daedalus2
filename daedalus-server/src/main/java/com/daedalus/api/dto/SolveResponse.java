// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.model.Point;

import java.util.List;

/**
 * Response body for {@code POST /api/maze/{id}/solve/{solverId}}.
 *
 * @param solverId  id of the solver that produced the run
 * @param path      ordered sequence of grid points from start to goal (empty when {@code success=false})
 * @param visited   number of cells the solver visited
 * @param explored  number of cells the solver expanded / explored
 * @param elapsedMs wall-clock duration of the solve in milliseconds
 * @param success   whether the solver actually reached the goal
 */
public record SolveResponse(String solverId, List<Point> path,
                             long visited, long explored, long elapsedMs, boolean success) {}
