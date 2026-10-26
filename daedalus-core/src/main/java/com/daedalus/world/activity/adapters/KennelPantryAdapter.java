// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.companion.KennelPantry;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G26 kennel food loop: the pack that waited its turn at the bowls learns from the
 * {@link KennelPantry.QuestResult} of the pack-order quest. A passed quest completes.
 */
public final class KennelPantryAdapter implements ActivityResultAdapter<KennelPantryAdapter.Feeding> {

    public static final String ACTIVITY_ID = "kennel.pack-order";
    public static final int MAX_DAYS = 365;

    /** Feeding snapshot: days, days with anyone hungry, kibble crafted and bowls served, milk spoiled (rounded). */
    public record Feeding(boolean passed, int days, int hungryDays, int crafted, int served, long spoiledMilkL,
                          boolean abandoned) {
        public Feeding {
            if (days < 0 || hungryDays < 0 || hungryDays > days || crafted < 0 || served < 0 || spoiledMilkL < 0)
                throw new IllegalArgumentException("feeding facts do not add up");
        }

        public static Feeding of(KennelPantry.QuestResult q, boolean abandoned) {
            int hungry = 0;
            int crafted = 0;
            int served = 0;
            double spoiled = 0;
            for (KennelPantry.DayReport d : q.log()) {
                if (!d.hungry().isEmpty()) hungry++;
                crafted += d.crafted();
                served += d.served();
                spoiled += d.spoiledMilkL();
            }
            return new Feeding(q.passed(), q.log().size(), hungry, crafted, served, Math.round(spoiled), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public KennelPantryAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "kennel-pack-order", 1, "kennel-isle", mode,
                Set.of("animal"), Set.of("guarding", "foraging"),
                Map.of("passed", 1L, "days", (long) MAX_DAYS, "hungry_days", (long) MAX_DAYS,
                        "crafted", 1_000_000L, "served", 1_000_000L, "spoiled_milk_l", 1_000_000L), 8);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Feeding f) {
        ActivityOutcome o = f.abandoned() ? ActivityOutcome.ABANDONED
                : f.passed() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("passed", f.passed() ? 1L : 0L);
        m.put("days", (long) f.days());
        m.put("hungry_days", (long) f.hungryDays());
        m.put("crafted", (long) f.crafted());
        m.put("served", (long) f.served());
        m.put("spoiled_milk_l", f.spoiledMilkL());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
