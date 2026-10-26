// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.BuzzGarden;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G145 Buzz Garden: the companion that listened as each bee buzzed its flower open is credited once
 * per garden. Matching bees to flowers for the most pollen completes, any other match fails; pollen is capped at
 * {@link #MAX_POLLEN}. Read-only on the audio core; the snapshot is built from the game's own {@code Verdict}.
 */
public final class BuzzGardenAdapter implements ActivityResultAdapter<BuzzGardenAdapter.Garden> {

    public static final String ACTIVITY_ID = "audio.buzz-garden";
    /** Cap on the pollen measures. */
    public static final int MAX_POLLEN = 10_000;

    /** Garden snapshot. */
    public record Garden(boolean best, int pollen, int bestPollen, boolean abandoned) {
        public Garden {
            if (pollen < 0 || bestPollen < 0) throw new IllegalArgumentException("negative pollen");
            if (pollen > bestPollen) throw new IllegalArgumentException("pollen exceeds the best");
            if (best != (pollen == bestPollen)) throw new IllegalArgumentException("best does not match pollen");
        }

        public static Garden of(BuzzGarden.Verdict v, boolean abandoned) {
            return new Garden(v.best(), v.pollen(), v.bestPollen(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public BuzzGardenAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "buzz-garden", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "pollination", "observation"),
                Map.of("best", 1L, "pollen", (long) MAX_POLLEN, "best_pollen", (long) MAX_POLLEN), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Garden r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.best() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("best", r.best() ? 1L : 0L);
        m.put("pollen", Math.min((long) MAX_POLLEN, (long) r.pollen()));
        m.put("best_pollen", Math.min((long) MAX_POLLEN, (long) r.bestPollen()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
