// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Append-only drive log for one world. Discover does not write this.
 */
public record WorldTraceResponse(String worldId, List<WorldTraceStepResponse> steps) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldTraceResponse {
        steps = steps == null ? List.of() : List.copyOf(steps);
    }
}
