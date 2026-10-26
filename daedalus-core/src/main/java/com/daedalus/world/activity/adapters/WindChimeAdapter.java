// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.WindChimeTuning;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** G12 adapter for G60 Wind Chime Tuning: the helper that held the tubes learns from the {@link WindChimeTuning.Verdict}. */
public final class WindChimeAdapter implements ActivityResultAdapter<WindChimeAdapter.Tuning> {

    public static final String ACTIVITY_ID = "audio.wind-chime-tuning";

    /** Tuning snapshot: tuned, tubes within tolerance, worst error in whole cents, trim in whole tenths of a mm. */
    public record Tuning(boolean tuned, int tubesOk, int worstCents, int trimTenthsMm, boolean abandoned) {
        public Tuning {
            if (tubesOk < 0 || tubesOk > WindChimeTuning.TUBES || worstCents < 0 || trimTenthsMm < 0)
                throw new IllegalArgumentException("tuning facts out of range");
        }

        public static Tuning of(WindChimeTuning.Verdict v, boolean abandoned) {
            int ok = 0;
            double worst = 0;
            for (WindChimeTuning.Tube t : v.tubes()) {
                if (t.ok()) ok++;
                worst = Math.max(worst, Math.abs(t.cents()));
            }
            return new Tuning(v.tuned(), ok, (int) Math.min(10_000, Math.round(worst)),
                    (int) Math.min(1_000_000, Math.round(Math.abs(v.trimMm()) * 10)), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public WindChimeAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "wind-chime-tuning", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("observation", "crafting"),
                Map.of("tuned", 1L, "tubes_ok", (long) WindChimeTuning.TUBES, "worst_cents", 10_000L,
                        "trim_tenths_mm", 1_000_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Tuning t) {
        ActivityOutcome o = t.abandoned() ? ActivityOutcome.ABANDONED
                : t.tuned() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("tuned", t.tuned() ? 1L : 0L);
        m.put("tubes_ok", (long) t.tubesOk());
        m.put("worst_cents", (long) t.worstCents());
        m.put("trim_tenths_mm", (long) t.trimTenthsMm());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
