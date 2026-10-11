// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

/**
 * Order an ark to the island in lane slot {@code toSlot} (ADR-020), or to this world's sky gate
 * {@code toGate} in the clouds past the rainbow (ADR-031). Exactly one of the two.
 */
public record VoyageRequest(
        @Min(value = 0, message = "toSlot must be at least 0")
        @Max(value = 63, message = "toSlot must be at most 63")
        Integer toSlot,
        @Min(value = 0, message = "toGate must be at least 0")
        @Max(value = 7, message = "toGate must be at most 7")
        Integer toGate) {

    /** One island slot (the ADR-020 form, still accepted on its own). */
    public VoyageRequest(Integer toSlot) {
        this(toSlot, null);
    }

    @JsonIgnore
    @AssertTrue(message = "give exactly one of toSlot or toGate")
    public boolean isOneDestination() {
        return (toSlot == null) != (toGate == null);
    }
}
