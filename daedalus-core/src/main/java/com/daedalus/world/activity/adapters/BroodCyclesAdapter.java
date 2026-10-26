// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.audio.BroodCycles;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G135 Brood Cycles: the companion that counted predator boom years with you is credited once per
 * brood. Picking a cycle with the fewest predator meetings completes, any other cycle fails; meetings are capped at
 * {@link #MAX_MEETINGS}. Read-only on the audio core; the snapshot is built from the game's own {@code Verdict}.
 */
public final class BroodCyclesAdapter implements ActivityResultAdapter<BroodCyclesAdapter.Brood> {

    public static final String ACTIVITY_ID = "audio.brood-cycles";
    /** Cap on the meetings measures. */
    public static final int MAX_MEETINGS = 10_000;

    /** Brood snapshot. */
    public record Brood(boolean best, int meetings, int bestMeetings, boolean abandoned) {
        public Brood {
            if (meetings < 0 || bestMeetings < 0) throw new IllegalArgumentException("negative meetings");
            if (bestMeetings > meetings) throw new IllegalArgumentException("best exceeds chosen meetings");
            if (best != (meetings == bestMeetings)) throw new IllegalArgumentException("best does not match meetings");
        }

        public static Brood of(BroodCycles.Verdict v, boolean abandoned) {
            return new Brood(v.best(), v.meetings(), v.bestMeetings(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public BroodCyclesAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "brood-cycles", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "counting", "observation"),
                Map.of("best", 1L, "meetings", (long) MAX_MEETINGS, "best_meetings", (long) MAX_MEETINGS), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Brood r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.best() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("best", r.best() ? 1L : 0L);
        m.put("meetings", Math.min((long) MAX_MEETINGS, (long) r.meetings()));
        m.put("best_meetings", Math.min((long) MAX_MEETINGS, (long) r.bestMeetings()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}