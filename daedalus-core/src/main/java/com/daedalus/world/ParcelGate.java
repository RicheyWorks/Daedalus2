// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Allow/deny on {@code (ownerId, verb)}. Owner is allowed unless denied.
 * A listed deny wins. No tokens, no chain.
 */
public final class ParcelGate {

    private ParcelGate() {
    }

    public static ParcelAccess check(Parcel parcel, ParcelAcl acl, String actorId, ParcelVerb verb) {
        if (parcel == null || verb == null || actorId == null || actorId.isBlank()) {
            return ParcelAccess.DENIED;
        }
        ParcelAcl rows = acl == null ? ParcelAcl.empty() : acl;
        if (rows.denies(actorId, verb)) {
            return ParcelAccess.DENIED;
        }
        if (parcel.ownerId().equals(actorId) || rows.grants(actorId, verb)) {
            return ParcelAccess.ALLOWED;
        }
        return ParcelAccess.DENIED;
    }
}
