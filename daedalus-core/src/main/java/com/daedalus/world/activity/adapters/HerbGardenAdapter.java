// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.HerbChordGarden;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G40 Herb Chord Garden: the bees and songbirds working the 3x3 bed learn from the
 * {@link HerbChordGarden.Verdict}. Reaching the proven target completes; a bed short of it is a settleable failure.
 */
public final class HerbGardenAdapter implements ActivityResultAdapter<HerbGardenAdapter.Planting> {

    public static final String ACTIVITY_ID = "audio.herb-chord-garden";

    /** Planting snapshot: lines sounding the wanted effect, the proven target, perfect. */
    public record Planting(int lines, int target, boolean perfect, boolean abandoned) {
        public Planting {
            int max = HerbChordGarden.lineCount();
            if (lines < 0 || target < 0 || lines > max || target > max)
                throw new IllegalArgumentException("lines and target must be 0-" + max);
            if (perfect && lines < target) throw new IllegalArgumentException("perfect needs the target reached");
        }

        public static Planting of(HerbChordGarden.Verdict v, boolean abandoned) {
            return new Planting(v.lines(), v.target(), v.perfect(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public HerbGardenAdapter(ActivityMode mode) {
        long max = HerbChordGarden.lineCount();
        definition = new ActivityDefinition(ACTIVITY_ID, "herb-chord-garden", 1, "shattered-planet", mode,
                Set.of("social_insect", "bird"), Set.of("pollinating", "observation"),
                Map.of("lines", max, "target", max, "perfect", 1L), 4);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Planting p) {
        ActivityOutcome o = p.abandoned() ? ActivityOutcome.ABANDONED
                : p.perfect() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("lines", (long) p.lines());
        m.put("target", (long) p.target());
        m.put("perfect", p.perfect() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
