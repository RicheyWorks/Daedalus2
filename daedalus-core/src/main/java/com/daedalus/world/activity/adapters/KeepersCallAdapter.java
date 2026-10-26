// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.audio.KeepersCall;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G121 Keeper's Call: the companion that echoed the harbour Keeper's bells beside you is credited once
 * per run. A finished run with at least one star (a phrase of 6 or more echoed) completes, a shorter one fails; a run
 * still in play is refused unless the host abandoned it. Read-only on the audio core.
 */
public final class KeepersCallAdapter implements ActivityResultAdapter<KeepersCallAdapter.Echo> {

    public static final String ACTIVITY_ID = "audio.keepers-call";

    /** Echo-run snapshot. */
    public record Echo(int score, int stars, boolean abandoned) {
        public Echo {
            if (score < 0 || score > KeepersCall.MAX_LENGTH) throw new IllegalArgumentException("score out of range");
            if (stars != KeepersCall.stars(score)) throw new IllegalArgumentException("stars do not match score");
        }

        public static Echo of(KeepersCall.Run run, boolean abandoned) {
            if (!run.over() && !abandoned) throw new IllegalArgumentException("run still in play");
            return new Echo(run.score(), KeepersCall.stars(run.score()), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public KeepersCallAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "keepers-call-run", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "singing", "memory"),
                Map.of("score", (long) KeepersCall.MAX_LENGTH, "stars", 3L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Echo r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.stars() >= 1 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("score", Math.min((long) KeepersCall.MAX_LENGTH, (long) r.score()));
        m.put("stars", Math.min(3L, (long) r.stars()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}