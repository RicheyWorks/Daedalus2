// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;

/**
 * A cell whose traversal cost is raised above the uniform {@code 1.0} — the API-level form of
 * {@code WeightedMazeGrid.setWeight}, and what makes the load-balancer story visible over
 * REST: an overloaded node the routing should detour around.
 *
 * <p>Cost is bounded to {@code [1.0, 1000.0]}. The lower bound matters for correctness, not
 * taste: below {@code 1.0} the unit-cost landmark bound stops being a valid lower bound
 * (ADR-001 item 4 measured A* silently suboptimal by up to 36% in that regime before the
 * heuristic learned to re-derive its metric). The engine handles sub-1.0 weights correctly
 * now, but the API keeps the simpler contract — a hotspot makes a cell <em>more</em>
 * expensive, never cheaper.
 *
 * @param row  cell row (bounds against the maze are checked at generation time)
 * @param col  cell column
 * @param cost traversal cost for entering this cell; {@code 1.0} is the uniform baseline
 */
public record Hotspot(
        @Min(value = 0, message = "hotspot row must be non-negative")
        int row,
        @Min(value = 0, message = "hotspot col must be non-negative")
        int col,
        @DecimalMin(value = "1.0", message = "hotspot cost must be at least 1.0 (the uniform baseline)")
        @DecimalMax(value = "1000.0", message = "hotspot cost must be at most 1000.0")
        double cost
) {}
