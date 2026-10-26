// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/**
 * Raise a floating island from a seed into the next free slot of the island lane (ADR-018).
 * The seed is the island: the same seed always grows the same terrain. {@code radius} defaults
 * to 18.
 */
public record RaiseIslandRequest(
        @NotNull(message = "seed is required") Long seed,
        @Min(value = 8, message = "radius must be at least 8")
        @Max(value = 46, message = "radius must be at most 46 (8..28 an island, 32..46 a land)")
        Integer radius) {
}
