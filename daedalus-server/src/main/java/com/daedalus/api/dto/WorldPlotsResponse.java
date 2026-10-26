// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * A Parcels world's district (ADR-033). Every plot is {@code plotSize} cubes square, and nothing may be
 * built above {@code height}. The plaza covers x {@code plazaMinX..plazaMaxX}, z {@code plazaMinZ..plazaMaxZ},
 * and is open to everyone and built by nobody. The helicopter rests on the cube {@code padX, padY, padZ}
 * over the helipad.
 */
public record WorldPlotsResponse(String worldId, int plotSize, int height, int plazaMinX, int plazaMinZ,
                                 int plazaMaxX, int plazaMaxZ, int padX, int padY, int padZ, List<PlotRow> plots) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldPlotsResponse {
        plots = plots == null ? List.of() : List.copyOf(plots);
    }
}
