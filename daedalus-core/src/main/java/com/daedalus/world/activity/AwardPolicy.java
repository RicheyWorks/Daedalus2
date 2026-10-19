// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/**
 * Owner-approved award policy for one activity and progression track. Weights turn bounded measures into points,
 * capped per award. {@link #inactive} is the default while curves remain an owner decision: it records the
 * contribution but grants 0 points.
 *
 * @param revision policy revision; changing it never makes an already-credited event payable again
 * @param track    progression track (e.g. {@code mastery.scouting})
 * @param weights  measure name to points per unit
 * @param cap      maximum points per award (0 = inactive)
 */
public record AwardPolicy(String activityId, int revision, String track, Map<String, Long> weights, long cap) {

    public AwardPolicy {
        activityId = ActivityParticipant.key(activityId, "activityId");
        track = ActivityParticipant.key(track, "track");
        if (revision < 1) throw new IllegalArgumentException("revision must be >= 1");
        if (cap < 0) throw new IllegalArgumentException("cap must be >= 0");
        weights = Map.copyOf(new TreeMap<>(Objects.requireNonNull(weights, "weights")));
        weights.values().forEach(w -> { if (w < 0) throw new IllegalArgumentException("weights must be >= 0"); });
    }

    /** Policy that records contributions without granting points (owner decision pending). */
    public static AwardPolicy inactive(String activityId, String track) {
        return new AwardPolicy(activityId, 1, track, Map.of(), 0);
    }

    /** Points this receipt earns under the policy (0 for unsettleable outcomes or device-local results). */
    public long points(ActivityResultReceipt r) {
        if (!r.activityId().equals(activityId)) throw new IllegalArgumentException("policy is for " + activityId);
        if (r.mode() != ActivityMode.AUTHORITATIVE || !r.outcome().settleable() || cap == 0) return 0;
        long sum = 0;
        for (Map.Entry<String, Long> e : r.measures().entrySet()) {
            long w = weights.getOrDefault(e.getKey(), 0L);
            sum = Math.addExact(sum, Math.multiplyExact(w, e.getValue()));
            if (sum >= cap) return cap;
        }
        return sum;
    }
}
