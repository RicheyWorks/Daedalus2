// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.AshfallRegrowth;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G20 Ashfall Regrowth: grazing herds and seed-carrying birds learn succession work from the
 * {@link AshfallRegrowth.Report}. Restored completes; still growing or scorched at the end of the plan is a failure.
 */
public final class AshfallRegrowthAdapter implements ActivityResultAdapter<AshfallRegrowthAdapter.Regrowth> {

    public static final String ACTIVITY_ID = "battlefield.ashfall-regrowth";

    /** Regrowth snapshot; old growth is per mille of land. */
    public record Regrowth(boolean restored, int seasons, int oldGrowthPm, int strikes, int burnt, int cachesUsed,
                           int herdsPlaced, boolean abandoned) {
        public Regrowth {
            if (seasons < 0 || strikes < 0 || burnt < 0 || cachesUsed < 0 || herdsPlaced < 0)
                throw new IllegalArgumentException("negative regrowth facts");
            if (oldGrowthPm < 0 || oldGrowthPm > 1000) throw new IllegalArgumentException("old growth out of 0-1000");
        }

        public static Regrowth of(AshfallRegrowth.Report r, boolean abandoned) {
            int pm = (int) Math.max(0, Math.min(1000, Math.round(r.oldGrowth() * 1000)));
            return new Regrowth(r.outcome() == AshfallRegrowth.Outcome.RESTORED, r.seasons(), pm, r.strikes(),
                    r.burnt(), r.cachesUsed(), r.herdsPlaced(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public AshfallRegrowthAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "ashfall-regrowth", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("grazing", "seeding"),
                Map.of("restored", 1L, "seasons", 1_000L, "old_growth_pm", 1000L, "strikes", 1_000L,
                        "burnt", 1_000_000L, "caches_used", 1_000L, "herds_placed", 1_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Regrowth r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.restored() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("restored", r.restored() ? 1L : 0L);
        m.put("seasons", (long) r.seasons());
        m.put("old_growth_pm", (long) r.oldGrowthPm());
        m.put("strikes", (long) r.strikes());
        m.put("burnt", (long) r.burnt());
        m.put("caches_used", (long) r.cachesUsed());
        m.put("herds_placed", (long) r.herdsPlaced());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
