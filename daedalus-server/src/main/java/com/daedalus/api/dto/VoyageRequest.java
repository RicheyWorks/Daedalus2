// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/** Order an ark to the island in lane slot {@code toSlot} (ADR-020). */
public record VoyageRequest(
        @NotNull(message = "toSlot is required")
        @Min(value = 0, message = "toSlot must be at least 0")
        @Max(value = 63, message = "toSlot must be at most 63")
        Integer toSlot) {
}
