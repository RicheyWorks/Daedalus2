// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.FogBellCallSigns;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** G12 adapter for G52 Fog Bell Call Signs: the lookout bird that listened learns from the judged {@link FogBellCallSigns.Verdict}. */
public final class FogBellAdapter implements ActivityResultAdapter<FogBellAdapter.Call> {

    public static final String ACTIVITY_ID = "audio.fog-bell-call-signs";

    /** Call snapshot: named the right ark, strokes blurred by the fog. */
    public record Call(boolean correct, int blurred, boolean abandoned) {
        public Call {
            if (blurred < 0) throw new IllegalArgumentException("blurred must be >= 0");
        }

        public static Call of(FogBellCallSigns.Verdict v, boolean abandoned) {
            return new Call(v.correct(), v.blurred(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public FogBellAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "fog-bell-call-signs", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("observation", "scouting"),
                Map.of("correct", 1L, "blurred", 100L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Call c) {
        ActivityOutcome o = c.abandoned() ? ActivityOutcome.ABANDONED
                : c.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("correct", c.correct() ? 1L : 0L);
        m.put("blurred", (long) c.blurred());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
