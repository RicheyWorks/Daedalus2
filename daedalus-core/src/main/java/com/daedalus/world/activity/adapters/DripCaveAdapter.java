// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.DripCaveChorus;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** G12 adapter for G64 Drip Cave Chorus: the cave bat that kept the beat learns from the {@link DripCaveChorus.Verdict}. */
public final class DripCaveAdapter implements ActivityResultAdapter<DripCaveAdapter.Chorus> {

    public static final String ACTIVITY_ID = "audio.drip-cave-chorus";

    /** Chorus snapshot: struck on the shared beat, and how far off in ms. */
    public record Chorus(boolean correct, int offMs, boolean abandoned) {
        public Chorus {
            if (offMs < 0) throw new IllegalArgumentException("offMs must be >= 0");
        }

        public static Chorus of(DripCaveChorus.Verdict v, boolean abandoned) {
            return new Chorus(v.correct(), (int) Math.min(3_600_000L, Math.abs((long) v.offMs())), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public DripCaveAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "drip-cave-chorus", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("observation", "scouting"),
                Map.of("correct", 1L, "off_ms", 3_600_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Chorus c) {
        ActivityOutcome o = c.abandoned() ? ActivityOutcome.ABANDONED
                : c.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("correct", c.correct() ? 1L : 0L);
        m.put("off_ms", (long) c.offMs());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
