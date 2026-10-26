// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.companion.KennelWaterLoop;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G17 kennel water loop: the pack that hauled and guarded the water through the Quiet Spring quest
 * learns from the {@link KennelWaterLoop.QuestResult} the loop already simulated. A passed quest completes.
 */
public final class KennelWaterAdapter implements ActivityResultAdapter<KennelWaterAdapter.Watch> {

    public static final String ACTIVITY_ID = "kennel.quiet-spring";
    public static final int MAX_DAYS = 365;

    /** Watch snapshot: days kept, days with any thirsty animal, litres drunk and spilled (rounded). */
    public record Watch(boolean passed, int days, int thirstyDays, long drunkL, long spilledL, boolean abandoned) {
        public Watch {
            if (days < 0 || thirstyDays < 0 || thirstyDays > days || drunkL < 0 || spilledL < 0)
                throw new IllegalArgumentException("watch facts do not add up");
        }

        public static Watch of(KennelWaterLoop.QuestResult q, boolean abandoned) {
            int thirsty = 0;
            double drunk = 0;
            double spilled = 0;
            for (KennelWaterLoop.DayReport d : q.log()) {
                if (!d.thirsty().isEmpty()) thirsty++;
                drunk += d.drunkL();
                spilled += d.spilledL();
            }
            return new Watch(q.passed(), q.log().size(), thirsty, Math.round(drunk), Math.round(spilled), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public KennelWaterAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "kennel-quiet-spring", 1, "kennel-isle", mode,
                Set.of("animal"), Set.of("guarding", "carrying"),
                Map.of("passed", 1L, "days", (long) MAX_DAYS, "thirsty_days", (long) MAX_DAYS,
                        "drunk_l", 10_000_000L, "spilled_l", 10_000_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Watch w) {
        ActivityOutcome o = w.abandoned() ? ActivityOutcome.ABANDONED
                : w.passed() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("passed", w.passed() ? 1L : 0L);
        m.put("days", (long) w.days());
        m.put("thirsty_days", (long) w.thirstyDays());
        m.put("drunk_l", w.drunkL());
        m.put("spilled_l", w.spilledL());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
