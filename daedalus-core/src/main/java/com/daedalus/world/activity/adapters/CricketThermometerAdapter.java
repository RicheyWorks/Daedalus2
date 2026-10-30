// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.CricketThermometer;

import java.util.Map;
import java.util.Set;

/** Read-only G12 mapping of G159's judged guess, including the core's correct "too cold" answer. */
public final class CricketThermometerAdapter
        implements ActivityResultAdapter<CricketThermometerAdapter.Listening> {
    public static final String ACTIVITY_ID = "audio.cricket-thermometer";

    public record Listening(boolean correct, int score, boolean abandoned) {
        public Listening {
            if (score < 0 || score > 100) throw new IllegalArgumentException("score out of range");
            if (correct && score != 100) throw new IllegalArgumentException("a correct reading scores 100");
        }

        /** The host passes the existing judge's verdict, or null before a guess was judged. */
        public static Listening of(CricketThermometer.Verdict verdict, boolean abandoned) {
            if (verdict == null) {
                if (!abandoned) throw new IllegalArgumentException("cricket guess still in progress");
                return new Listening(false, 0, true);
            }
            return new Listening(verdict.correct(), verdict.score(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public CricketThermometerAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "cricket-thermometer", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("listening", "observation", "counting"),
                Map.of("correct", 1L, "score", 100L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Listening r) {
        ActivityOutcome outcome = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), Map.of("correct", r.correct() ? 1L : 0L, "score", (long) r.score()),
                s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
