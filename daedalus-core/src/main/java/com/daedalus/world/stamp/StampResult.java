// SPDX-License-Identifier: MIT

package com.daedalus.world.stamp;

import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelId;
import com.daedalus.world.WorldRevision;

/**
 * Outcome of a stamp. Overlap is a named refusal, not a merge.
 */
public record StampResult(
        boolean ok,
        String reason,
        ParcelId parcelId,
        ParcelBounds bounds,
        WorldRevision revision) {

    public static final String PARCEL_OVERLAP = "PARCEL_OVERLAP";
    public static final String DENIED = "DENIED";

    public static StampResult applied(ParcelId parcelId, ParcelBounds bounds, WorldRevision revision) {
        return new StampResult(true, null, parcelId, bounds, revision);
    }

    public static StampResult overlap(WorldRevision revision) {
        return new StampResult(false, PARCEL_OVERLAP, null, null, revision);
    }

    public static StampResult denied(WorldRevision revision) {
        return new StampResult(false, DENIED, null, null, revision);
    }

    /** Named outcome for traces. Silence is not success. */
    public String outcome() {
        return ok ? "APPLIED" : reason;
    }
}
