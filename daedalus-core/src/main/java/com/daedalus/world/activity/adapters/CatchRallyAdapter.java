// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.sports.ThrowableSports;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G11 throwable sports (catch): a pet playing catch or fetch learns from the
 * {@link ThrowableSports.CatchResult} the sports rules already scored.
 */
public final class CatchRallyAdapter implements ActivityResultAdapter<CatchRallyAdapter.Rally> {

    public static final String ACTIVITY_ID = "sports.catch-rally";
    public static final int MAX_THROWS = 500;

    /** Rally snapshot: throws, catches, best streak, score. */
    public record Rally(int throwsMade, int caught, int bestStreak, int score, boolean abandoned) {
        public Rally {
            if (throwsMade < 0 || caught < 0 || bestStreak < 0 || score < 0 || caught > throwsMade
                    || bestStreak > caught)
                throw new IllegalArgumentException("rally facts do not add up");
        }

        public static Rally of(ThrowableSports.CatchResult r, boolean abandoned) {
            return new Rally(r.log().size(), r.caught(), r.bestStreak(), r.score(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public CatchRallyAdapter(ActivityMode mode) {
        long t = MAX_THROWS;
        definition = new ActivityDefinition(ACTIVITY_ID, "catch-rally", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("fetching", "play"),
                Map.of("throws", t, "caught", t, "best_streak", t, "score", t * 2), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Rally r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.caught() > 0 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("throws", (long) r.throwsMade());
        m.put("caught", (long) r.caught());
        m.put("best_streak", (long) r.bestStreak());
        m.put("score", (long) r.score());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
