// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.SalmonRun;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G71 Salmon Run: the river bears and fishing birds learn from the run's {@link SalmonRun.Report}.
 * RESTORED completes; HOLDING or FISHED_OUT is a failure. Fish counts and forest nitrogen are rounded to whole
 * units so receipts stay canonical integers.
 */
public final class SalmonRunAdapter implements ActivityResultAdapter<SalmonRunAdapter.Run> {

    public static final String ACTIVITY_ID = "battlefield.salmon-run";

    /** Run snapshot. */
    public record Run(boolean restored, boolean fishedOut, long meanEscapement, long totalCatch, long forestNitrogen,
                      int years, boolean abandoned) {
        public Run {
            if (meanEscapement < 0 || totalCatch < 0 || forestNitrogen < 0 || years < 0)
                throw new IllegalArgumentException("negative run facts");
            if (restored && fishedOut) throw new IllegalArgumentException("a run cannot be restored and fished out");
        }

        public static Run of(SalmonRun.Report r, boolean abandoned) {
            return new Run(r.outcome() == SalmonRun.Outcome.RESTORED, r.outcome() == SalmonRun.Outcome.FISHED_OUT,
                    whole(r.meanEscapement()), whole(r.totalCatch()), whole(r.forestNitrogen()), r.years().size(),
                    abandoned);
        }

        private static long whole(double v) {
            return Double.isFinite(v) ? Math.max(0L, Math.min(1_000_000_000L, Math.round(v))) : 0L;
        }
    }

    private final ActivityDefinition definition;

    public SalmonRunAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "salmon-run", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("fishing", "carrying"),
                Map.of("restored", 1L, "fished_out", 1L, "mean_escapement", 1_000_000_000L,
                        "total_catch", 1_000_000_000L, "forest_nitrogen", 1_000_000_000L, "years", 1_000L), 8);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Run r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.restored() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("restored", r.restored() ? 1L : 0L);
        m.put("fished_out", r.fishedOut() ? 1L : 0L);
        m.put("mean_escapement", r.meanEscapement());
        m.put("total_catch", r.totalCatch());
        m.put("forest_nitrogen", r.forestNitrogen());
        m.put("years", (long) r.years());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}