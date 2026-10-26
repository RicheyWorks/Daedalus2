// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.forge.TemperForge;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G19 Anvil and Quench: the forge helper (a bellows dog, a coal-fetching mule) learns smithing from the
 * {@link TemperForge.Result} the forge already judged. An uncracked blade completes; a cracked one is a settleable
 * failure.
 */
public final class TemperForgeAdapter implements ActivityResultAdapter<TemperForgeAdapter.Temper> {

    public static final String ACTIVITY_ID = "forge.anvil-quench";

    /** Temper snapshot: per-mille phase scores, perfect strikes, cracked, temper, ark plate. */
    public record Temper(int heatPm, int hammerPm, int quenchPm, int perfectStrikes, boolean cracked, int temper,
                         boolean arkPlate, boolean abandoned) {
        public Temper {
            for (int pm : new int[] {heatPm, hammerPm, quenchPm})
                if (pm < 0 || pm > 1000) throw new IllegalArgumentException("phase score out of 0-1000");
            if (perfectStrikes < 0 || temper < 0) throw new IllegalArgumentException("negative temper facts");
            if (arkPlate && cracked) throw new IllegalArgumentException("a cracked blank is never an ark plate");
        }

        public static Temper of(TemperForge.Result r, boolean abandoned) {
            int perfect = (int) r.strikes().stream().filter(k -> k == TemperForge.Strike.PERFECT).count();
            return new Temper(r.heatPm(), r.hammerPm(), r.quenchPm(), perfect, r.cracked(), r.temper(), r.arkPlate(),
                    abandoned);
        }
    }

    private final ActivityDefinition definition;

    public TemperForgeAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "anvil-and-quench", 1, "shattered-planet", mode,
                Set.of("animal"), Set.of("smithing", "carrying"),
                Map.of("heat_pm", 1000L, "hammer_pm", 1000L, "quench_pm", 1000L, "perfect_strikes", 100L,
                        "cracked", 1L, "temper", 1000L, "ark_plate", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Temper t) {
        ActivityOutcome o = t.abandoned() ? ActivityOutcome.ABANDONED
                : t.cracked() ? ActivityOutcome.FAILED : ActivityOutcome.COMPLETED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("heat_pm", (long) t.heatPm());
        m.put("hammer_pm", (long) t.hammerPm());
        m.put("quench_pm", (long) t.quenchPm());
        m.put("perfect_strikes", (long) t.perfectStrikes());
        m.put("cracked", t.cracked() ? 1L : 0L);
        m.put("temper", (long) t.temper());
        m.put("ark_plate", t.arkPlate() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
