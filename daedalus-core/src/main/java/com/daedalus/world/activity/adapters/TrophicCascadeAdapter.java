// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.TrophicCascade;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G58 Trophic Cascade: the ark wolf pack learns from the valley's {@link TrophicCascade.Report}.
 * Only a CASCADE completes (the willow and the beavers came back); PARTIAL, BROWSED or CRASHED is a failure, so
 * culling to the same head count earns no wolf credit.
 */
public final class TrophicCascadeAdapter implements ActivityResultAdapter<TrophicCascadeAdapter.Valley> {

    public static final String ACTIVITY_ID = "battlefield.trophic-cascade";

    /** Valley snapshot; mean willow is per mille, elk and wolves are rounded head counts. */
    public record Valley(boolean cascade, int willowPm, int colonies, int elk, int wolves, int years,
                         boolean abandoned) {
        public Valley {
            if (colonies < 0 || elk < 0 || wolves < 0 || years < 0)
                throw new IllegalArgumentException("negative valley facts");
            if (willowPm < 0 || willowPm > 1000) throw new IllegalArgumentException("willow out of 0-1000");
        }

        public static Valley of(TrophicCascade.Report r, boolean abandoned) {
            int pm = (int) Math.max(0, Math.min(1000, Math.round(r.meanWillow() * 1000)));
            return new Valley(r.outcome() == TrophicCascade.Outcome.CASCADE, pm, r.colonies(),
                    (int) Math.max(0, Math.round(r.elk())), (int) Math.max(0, Math.round(r.wolves())),
                    r.years().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public TrophicCascadeAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "trophic-cascade", 1, "shattered-planet", mode,
                Set.of("animal"), Set.of("hunting", "guarding"),
                Map.of("cascade", 1L, "willow_pm", 1000L, "colonies", 1_000L, "elk", 1_000_000L,
                        "wolves", 1_000_000L, "years", 1_000L), 16);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Valley v) {
        ActivityOutcome o = v.abandoned() ? ActivityOutcome.ABANDONED
                : v.cascade() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("cascade", v.cascade() ? 1L : 0L);
        m.put("willow_pm", (long) v.willowPm());
        m.put("colonies", (long) v.colonies());
        m.put("elk", (long) v.elk());
        m.put("wolves", (long) v.wolves());
        m.put("years", (long) v.years());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}