// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.odds.tournament.SquallCupQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G35 Squall Cup: the fishing companion in the boat learns from a finished cup run. Champion completes,
 * knocked out fails; a cup still in progress has no result yet and is refused.
 */
public final class SquallCupAdapter implements ActivityResultAdapter<SquallCupAdapter.Cup> {

    public static final String ACTIVITY_ID = "odds.squall-cup";
    public static final int MAX_ROUNDS = 16;

    /** Cup snapshot: champion, heats won. */
    public record Cup(boolean champion, int roundsWon, boolean abandoned) {
        public Cup {
            if (roundsWon < 0 || roundsWon > MAX_ROUNDS) throw new IllegalArgumentException("roundsWon out of range");
        }

        public static Cup of(SquallCupQuest q, boolean abandoned) {
            return from(q.stage(), q.roundsWon(), abandoned);
        }

        static Cup from(SquallCupQuest.Stage stage, int roundsWon, boolean abandoned) {
            return switch (stage) {
                case CHAMPION -> new Cup(true, roundsWon, abandoned);
                case KNOCKED_OUT -> new Cup(false, roundsWon, abandoned);
                case ENTERED, ODDS_POSTED -> throw new IllegalArgumentException("cup still in progress: " + stage);
            };
        }
    }

    private final ActivityDefinition definition;

    public SquallCupAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "squall-cup", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("fishing", "scouting"),
                Map.of("champion", 1L, "rounds_won", (long) MAX_ROUNDS), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Cup c) {
        ActivityOutcome o = c.abandoned() ? ActivityOutcome.ABANDONED
                : c.champion() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("champion", c.champion() ? 1L : 0L);
        m.put("rounds_won", (long) c.roundsWon());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
