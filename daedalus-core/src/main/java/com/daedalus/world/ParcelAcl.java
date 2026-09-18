// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Extra grants and denials on a parcel. Owner is implicit and is not listed.
 * Deny wins. No tokens, no chain.
 */
public record ParcelAcl(List<Grant> grants, List<Grant> denials) {

    public record Grant(String actorId, ParcelVerb verb) {
        public Grant {
            Objects.requireNonNull(actorId, "actorId is required");
            Objects.requireNonNull(verb, "verb is required");
            if (actorId.isBlank()) {
                throw new IllegalArgumentException("actorId is required");
            }
        }
    }

    public ParcelAcl {
        grants = List.copyOf(Objects.requireNonNull(grants, "grants"));
        denials = List.copyOf(Objects.requireNonNull(denials, "denials"));
    }

    public static ParcelAcl empty() {
        return new ParcelAcl(List.of(), List.of());
    }

    public boolean denies(String actorId, ParcelVerb verb) {
        return contains(denials, actorId, verb);
    }

    public boolean grants(String actorId, ParcelVerb verb) {
        return contains(grants, actorId, verb);
    }

    public ParcelAcl grant(String actorId, ParcelVerb verb) {
        Grant row = new Grant(actorId, verb);
        if (grants.contains(row)) {
            return this;
        }
        List<Grant> next = new ArrayList<>(grants);
        next.add(row);
        return new ParcelAcl(next, denials);
    }

    public ParcelAcl deny(String actorId, ParcelVerb verb) {
        Grant row = new Grant(actorId, verb);
        if (denials.contains(row)) {
            return this;
        }
        List<Grant> next = new ArrayList<>(denials);
        next.add(row);
        return new ParcelAcl(grants, next);
    }

    /**
     * Drop one extra grant. Denials stay. Missing grant is a no-op.
     */
    public ParcelAcl revoke(String actorId, ParcelVerb verb) {
        Grant row = new Grant(actorId, verb);
        if (!grants.contains(row)) {
            return this;
        }
        List<Grant> next = new ArrayList<>(grants);
        next.remove(row);
        return new ParcelAcl(next, denials);
    }

    /**
     * Drop one extra denial. Grants stay. Missing denial is a no-op.
     */
    public ParcelAcl forgive(String actorId, ParcelVerb verb) {
        Grant row = new Grant(actorId, verb);
        if (!denials.contains(row)) {
            return this;
        }
        List<Grant> next = new ArrayList<>(denials);
        next.remove(row);
        return new ParcelAcl(grants, next);
    }

    private static boolean contains(List<Grant> rows, String actorId, ParcelVerb verb) {
        if (actorId == null || verb == null) {
            return false;
        }
        for (Grant row : rows) {
            if (row.actorId().equals(actorId) && row.verb() == verb) {
                return true;
            }
        }
        return false;
    }
}
