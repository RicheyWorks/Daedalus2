// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotNull;

/**
 * Project a maze slab at the origin. {@code mazeId} is a lab cache key —
 * absent means the WorldOps 1×1 slab. Generators stay on {@code /maze/**}.
 */
public record StampWorldRequest(
        @NotNull(message = "x is required") Integer x,
        @NotNull(message = "y is required") Integer y,
        @NotNull(message = "z is required") Integer z,
        String mazeId) {
}
