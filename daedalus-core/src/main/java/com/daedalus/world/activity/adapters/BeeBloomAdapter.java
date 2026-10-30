// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.BeeBloom;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G48 Bee Bloom: the ark hives (colonies) learn pollination from the season's
 * {@link BeeBloom.Report}. THRIVING completes; PATCHY or COLLAPSED is a failure.
 */
public final class BeeBloomAdapter implements ActivityResultAdapter<BeeBloomAdapter.Season> {

    public static final String ACTIVITY_ID = "battlefield.bee-bloom";

    /** Season snapshot; mean seed set is per mille, frost is the first frost day + 1 (0 = no frost). */
    public record Season(boolean thriving, boolean collapsed, int seedSetPm, int hivesAlive, int frostDayPlusOne,
                         int days, boolean abandoned) {
        public Season {
            if (hivesAlive < 0 || frostDayPlusOne < 0 || days < 0)
                throw new IllegalArgumentException("negative season facts");
            if (seedSetPm < 0 || seedSetPm > 1000) throw new IllegalArgumentException("seed set out of 0-1000");
            if (thriving && collapsed) throw new IllegalArgumentException("a season cannot thrive and collapse");
        }

        public static Season of(BeeBloom.Report r, boolean abandoned) {
            int pm = (int) Math.max(0, Math.min(1000, Math.round(r.meanSeedSet() * 1000)));
            return new Season(r.outcome() == BeeBloom.Outcome.THRIVING, r.outcome() == BeeBloom.Outcome.COLLAPSED,
                    pm, r.hivesAlive(), Math.max(0, r.frostDay() + 1), r.days().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public BeeBloomAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "bee-bloom", 1, "shattered-planet", mode,
                Set.of("social_insect", "bird"), Set.of("pollinating", "foraging"),
                Map.of("thriving", 1L, "seed_set_pm", 1000L, "hives_alive", 1_000L, "frost_day", 10_000L,
                        "days", 10_000L), 16);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Season r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.thriving() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("thriving", r.thriving() ? 1L : 0L);
        m.put("seed_set_pm", (long) r.seedSetPm());
        m.put("hives_alive", (long) r.hivesAlive());
        m.put("frost_day", (long) r.frostDayPlusOne());
        m.put("days", (long) r.days());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}