// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.forge.VoidCrossing;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G152 Void Crossing: the crew companion is credited once per crossing. Arriving (with or without
 * losses) completes and the heads lost are kept as a measure; a breach or an ark that never launched fails. A
 * crossing still sailing is refused unless the host abandoned it. Read-only on the forge core.
 */
public final class VoidCrossingAdapter implements ActivityResultAdapter<VoidCrossingAdapter.Passage> {

    public static final String ACTIVITY_ID = "forge.void-crossing";
    /** Cap on day and count measures. */
    public static final int MAX_COUNT = 365;

    /** Crossing snapshot. */
    public record Passage(boolean arrived, int days, int minSeam, int patches, int lost, boolean abandoned) {
        public Passage {
            if (days < 0 || patches < 0 || lost < 0) throw new IllegalArgumentException("negative crossing facts");
        }

        public static Passage of(VoidCrossing.Crossing x, boolean abandoned) {
            VoidCrossing.Outcome o = x.outcome();
            if (o == VoidCrossing.Outcome.SAILING && !abandoned)
                throw new IllegalArgumentException("crossing still SAILING");
            boolean arrived = o == VoidCrossing.Outcome.ARRIVED || o == VoidCrossing.Outcome.ARRIVED_WITH_LOSSES;
            return new Passage(arrived, x.day(), Math.max(0, x.minSeam()), x.patches(), x.lostHead(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public VoidCrossingAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "void-crossing", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("crewing", "endurance", "hauling", "companionship"),
                Map.of("days", (long) MAX_COUNT, "min_seam", 100L, "patches", (long) MAX_COUNT,
                        "lost", (long) MAX_COUNT), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Passage r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.arrived() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("days", (long) Math.min(MAX_COUNT, r.days()));
        m.put("min_seam", (long) Math.min(100, r.minSeam()));
        m.put("patches", (long) Math.min(MAX_COUNT, r.patches()));
        m.put("lost", (long) Math.min(MAX_COUNT, r.lost()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
