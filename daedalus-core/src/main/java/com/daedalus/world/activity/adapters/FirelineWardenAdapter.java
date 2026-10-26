// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.FirelineWarden;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G27 Fireline Warden: the fire-crew animals (a water-hauling mule, a hound that cuts brush lines)
 * learn from the {@link FirelineWarden.Report}. SAVED or HELD completes, LOST fails; a fire still BURNING has no result
 * yet and is refused.
 */
public final class FirelineWardenAdapter implements ActivityResultAdapter<FirelineWardenAdapter.Defence> {

    public static final String ACTIVITY_ID = "battlefield.fireline-warden";

    /** Defence snapshot; {@code result} is 2 saved, 1 held, 0 lost; saved share is per mille. */
    public record Defence(int result, long ticks, int savedPm, int burnt, int cut, int wetted, int doused,
                          boolean abandoned) {
        public Defence {
            if (result < 0 || result > 2) throw new IllegalArgumentException("result is 0 lost, 1 held, 2 saved");
            if (ticks < 0 || burnt < 0 || cut < 0 || wetted < 0 || doused < 0)
                throw new IllegalArgumentException("negative fireline facts");
            if (savedPm < 0 || savedPm > 1000) throw new IllegalArgumentException("saved share out of 0-1000");
        }

        public static Defence of(FirelineWarden.Report r, boolean abandoned) {
            int result = switch (r.outcome()) {
                case SAVED -> 2;
                case HELD -> 1;
                case LOST -> 0;
                case BURNING -> throw new IllegalArgumentException("fire still burning: no result yet");
            };
            int pm = (int) Math.max(0, Math.min(1000, Math.round(r.saved() * 1000)));
            return new Defence(result, r.ticks(), pm, r.burnt(), r.cut(), r.wetted(), r.doused(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public FirelineWardenAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "fireline-warden", 1, "shattered-planet", mode,
                Set.of("animal"), Set.of("firefighting", "carrying"),
                Map.of("result", 2L, "ticks", 1_000_000L, "saved_pm", 1000L, "burnt", 1_000_000L, "cut", 10_000L,
                        "wetted", 10_000L, "doused", 10_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Defence d) {
        ActivityOutcome o = d.abandoned() ? ActivityOutcome.ABANDONED
                : d.result() > 0 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("result", (long) d.result());
        m.put("ticks", d.ticks());
        m.put("saved_pm", (long) d.savedPm());
        m.put("burnt", (long) d.burnt());
        m.put("cut", (long) d.cut());
        m.put("wetted", (long) d.wetted());
        m.put("doused", (long) d.doused());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
