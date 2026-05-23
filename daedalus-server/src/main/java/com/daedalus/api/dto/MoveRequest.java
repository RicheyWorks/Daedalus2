// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.api.validation.NonNegativeCoordinate;
import com.daedalus.model.Point;
import jakarta.validation.constraints.NotNull;

/**
 * Request body for {@code POST /api/v1/session/{id}/move}.
 *
 * <p>Validation contract:
 * <ul>
 *   <li>{@code to} — required (non-null) and must have non-negative {@code row} and
 *       {@code col} ({@link NonNegativeCoordinate}). The upper bound and the
 *       "adjacent to current position" check are still owned by
 *       {@code GameSessionService#tryMove} (which has access to the grid dimensions
 *       and the player's current cell); validation here only catches the structurally
 *       impossible — negative coordinates — so the API surface returns a clean 400
 *       instead of letting a malformed request silently flip {@code tryMove} to
 *       {@code false}.</li>
 * </ul>
 *
 * <p>The {@code Point} type lives in the framework-free {@code daedalus-core} module and
 * intentionally carries no validation annotations. {@code @NonNegativeCoordinate} is
 * defined in the server module and reaches into {@code Point} via its public accessors,
 * preserving the dependency boundary.
 *
 * @param to grid coordinate the player wants to move to (must be adjacent to the current position)
 */
public record MoveRequest(
        @NotNull(message = "target coordinate is required")
        @NonNegativeCoordinate
        Point to
) {}
