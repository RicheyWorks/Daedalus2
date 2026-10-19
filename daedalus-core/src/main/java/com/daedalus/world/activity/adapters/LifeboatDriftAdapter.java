// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.walk.LifeboatQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G133 The Lifeboat Drift: the companion that rowed with you after the wreck is credited once per
 * voyage. Reaching the harbour lights completes, the reef fails; a boat still adrift is refused unless the host
 * abandoned the quest. Watches are capped at {@link #MAX_WATCHES}. Read-only on the odds core.
 */
public final class LifeboatDriftAdapter implements ActivityResultAdapter<LifeboatDriftAdapter.Voyage> {

    public static final String ACTIVITY_ID = "odds.lifeboat-drift";
    /** Cap on the watches measure. */
    public static final int MAX_WATCHES = 1_000;

    /** Voyage snapshot. */
    public record Voyage(boolean harbour, int watches, int rationsLeft, boolean abandoned) {
        public Voyage {
            if (watches < 0) throw new IllegalArgumentException("negative watches");
            if (rationsLeft < 0 || rationsLeft > LifeboatQuest.RATIONS)
                throw new IllegalArgumentException("rations out of range");
        }

        public static Voyage of(LifeboatQuest q, boolean abandoned) {
            if (q.stage() == LifeboatQuest.Stage.ADRIFT && !abandoned)
                throw new IllegalArgumentException("lifeboat still adrift: ADRIFT");
            return new Voyage(q.stage() == LifeboatQuest.Stage.HARBOUR, q.watches(), q.rations(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public LifeboatDriftAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "lifeboat-drift", 1, "sky-islands", mode,
                Set.of("animal", "bird"), Set.of("rowing", "companionship", "endurance"),
                Map.of("harbour", 1L, "watches", (long) MAX_WATCHES, "rations_left", (long) LifeboatQuest.RATIONS), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Voyage r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.harbour() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("harbour", r.harbour() ? 1L : 0L);
        m.put("watches", Math.min((long) MAX_WATCHES, (long) r.watches()));
        m.put("rations_left", (long) r.rationsLeft());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}