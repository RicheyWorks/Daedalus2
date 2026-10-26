// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.apprentice.Apprenticeships;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G155 The Apprentices: the companion that carried Old Wick's lantern is credited once per lantern
 * night. A stable announcement (no blocking pair) completes, an unstable one fails; a board not yet announced is
 * refused unless the host abandoned it. Read-only on the brew core.
 */
public final class ApprenticesAdapter implements ActivityResultAdapter<ApprenticesAdapter.Lantern> {

    public static final String ACTIVITY_ID = "brew.apprentices";
    /** Cap on pair measures. */
    public static final int MAX_PAIRS = 16;

    /** Lantern-night snapshot. */
    public record Lantern(int paired, int blocking, boolean abandoned) {
        public Lantern {
            if (paired < 0 || blocking < 0) throw new IllegalArgumentException("negative lantern facts");
        }

        public static Lantern of(Apprenticeships a, boolean abandoned) {
            if (a.announced() == null && !abandoned) throw new IllegalArgumentException("board not yet announced");
            Map<String, String> board = a.board();
            return new Lantern(board.size(), a.blockingPairs(board).size(), abandoned);
        }

        public boolean stable() { return paired > 0 && blocking == 0; }
    }

    private final ActivityDefinition definition;

    public ApprenticesAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "apprentices", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("companionship", "matchmaking", "observation"),
                Map.of("paired", (long) MAX_PAIRS, "blocking", (long) MAX_PAIRS * MAX_PAIRS), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Lantern r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.stable() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("paired", (long) Math.min(MAX_PAIRS, r.paired()));
        m.put("blocking", (long) Math.min(MAX_PAIRS * MAX_PAIRS, r.blocking()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
