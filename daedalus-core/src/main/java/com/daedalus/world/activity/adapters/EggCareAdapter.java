// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.eggs.EggHatchery;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G06 egg hatching: the companion that warmed and turned the egg (a nest-warming hen, a hound
 * curled round the incubator) learns nursery care from the {@link EggHatchery.EggState} the hatchery produced.
 * Hatched completes; an egg still waiting is a settleable failure; walking away pays nothing.
 */
public final class EggCareAdapter implements ActivityResultAdapter<EggCareAdapter.Care> {

    public static final String ACTIVITY_ID = "eggs.hatch-care";

    /** Care snapshot: ticks tended, turns, chills, hatched, perfect care. */
    public record Care(int ticks, int turns, int chills, boolean hatched, boolean perfectCare, boolean abandoned) {
        public Care {
            if (ticks < 0 || turns < 0 || chills < 0) throw new IllegalArgumentException("negative care facts");
            if (perfectCare && !hatched) throw new IllegalArgumentException("perfect care is judged at hatching");
        }

        public static Care of(EggHatchery.EggState s, boolean abandoned) {
            boolean perfect = s.hatched() && s.hatchling() != null && s.hatchling().perfectCare();
            return new Care(s.ticks(), s.turns(), s.chills(), s.hatched(), perfect, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public EggCareAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "egg-hatch-care", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("nursery", "guarding"),
                Map.of("ticks", 100_000L, "turns", 100_000L, "chills", 100_000L, "hatched", 1L, "perfect_care", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Care c) {
        ActivityOutcome o = c.abandoned() ? ActivityOutcome.ABANDONED
                : c.hatched() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("ticks", (long) c.ticks());
        m.put("turns", (long) c.turns());
        m.put("chills", (long) c.chills());
        m.put("hatched", c.hatched() ? 1L : 0L);
        m.put("perfect_care", c.perfectCare() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
