// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

/**
 * Order a vessel to the island in lane slot {@code toSlot} (ADR-020), to this world's sky gate
 * {@code toGate} in the clouds past the rainbow (ADR-031), or {@code toHome} — its own island, or the
 * helipad a Parcels world's helicopter lives on (ADR-033). Exactly one of the three.
 */
public record VoyageRequest(
        @Min(value = 0, message = "toSlot must be at least 0")
        @Max(value = 63, message = "toSlot must be at most 63")
        Integer toSlot,
        @Min(value = 0, message = "toGate must be at least 0")
        @Max(value = 7, message = "toGate must be at most 7")
        Integer toGate,
        Boolean toHome) {

    /** One island slot (the ADR-020 form, still accepted on its own). */
    public VoyageRequest(Integer toSlot) {
        this(toSlot, null, null);
    }

    /** An island or a gate (the ADR-031 form). */
    public VoyageRequest(Integer toSlot, Integer toGate) {
        this(toSlot, toGate, null);
    }

    @JsonIgnore
    @AssertTrue(message = "give exactly one of toSlot, toGate or toHome")
    public boolean isOneDestination() {
        int given = (toSlot == null ? 0 : 1) + (toGate == null ? 0 : 1) + (Boolean.TRUE.equals(toHome) ? 1 : 0);
        return given == 1;
    }
}
