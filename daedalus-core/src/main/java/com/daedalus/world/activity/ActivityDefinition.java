// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

/**
 * Versioned activity-result v1 definition that wraps an existing game. It names the adapter, the revision, which
 * participant profiles and roles may take part, and the bounded measures a result may report. It is a contract
 * around a game, not a parallel minigame engine.
 *
 * @param activityId     canonical activity key, e.g. {@code labyrinth.chalk-trail}
 * @param adapterId      adapter that turns the game's own result into a receipt
 * @param revision       definition revision (1+); changing it never makes an old event payable again
 * @param realm          realm key the activity belongs to
 * @param mode           AUTHORITATIVE or DEVICE_LOCAL namespace
 * @param profiles       allowed participant life profiles
 * @param roles          allowed participant roles
 * @param measureMax     measure name to inclusive maximum (minimum is always 0)
 * @param maxParticipants upper bound on accepted participants per session
 */
public record ActivityDefinition(String activityId, String adapterId, int revision, String realm, ActivityMode mode,
                                 Set<String> profiles, Set<String> roles, Map<String, Long> measureMax,
                                 int maxParticipants) {

    public ActivityDefinition {
        activityId = ActivityParticipant.key(activityId, "activityId");
        adapterId = ActivityParticipant.key(adapterId, "adapterId");
        realm = ActivityParticipant.key(realm, "realm");
        Objects.requireNonNull(mode, "mode");
        if (revision < 1) throw new IllegalArgumentException("revision must be >= 1");
        if (maxParticipants < 1 || maxParticipants > 64) throw new IllegalArgumentException("maxParticipants 1..64");
        profiles = Set.copyOf(Objects.requireNonNull(profiles, "profiles"));
        roles = Set.copyOf(Objects.requireNonNull(roles, "roles"));
        if (profiles.isEmpty() || roles.isEmpty()) throw new IllegalArgumentException("profiles and roles required");
        profiles.forEach(p -> ActivityParticipant.key(p, "profile"));
        roles.forEach(r -> ActivityParticipant.key(r, "role"));
        Objects.requireNonNull(measureMax, "measureMax");
        TreeMap<String, Long> m = new TreeMap<>();
        measureMax.forEach((k, v) -> {
            ActivityParticipant.key(k, "measure");
            if (v == null || v < 0) throw new IllegalArgumentException("measure max must be >= 0: " + k);
            m.put(k, v);
        });
        measureMax = java.util.Collections.unmodifiableSortedMap(m);
    }

    /** Throws if the participant's profile or role is not allowed by this definition. */
    public void checkParticipant(ActivityParticipant p) {
        if (!profiles.contains(p.profile()))
            throw new IllegalArgumentException("profile not allowed in " + activityId + ": " + p.profile());
        if (!roles.contains(p.role()))
            throw new IllegalArgumentException("role not allowed in " + activityId + ": " + p.role());
    }

    /** Throws if a measure is unknown or out of its declared bounds. */
    public void checkMeasure(String name, long value) {
        Long max = measureMax.get(name);
        if (max == null) throw new IllegalArgumentException("unknown measure for " + activityId + ": " + name);
        if (value < 0 || value > max)
            throw new IllegalArgumentException("measure " + name + " out of bounds 0.." + max + ": " + value);
    }
}
