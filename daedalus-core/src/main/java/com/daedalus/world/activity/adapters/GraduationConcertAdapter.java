// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.brew.concert.GraduationConcert;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G131 The Graduation Concert (YTM story ch. 12): the companion that sang along on the homestead green
 * is credited once per evening. A cheered concert completes, a rough one fails; an evening still under way is refused
 * unless the host abandoned it. Key changes are kept against the smoothest legal set. Read-only on the core.
 */
public final class GraduationConcertAdapter implements ActivityResultAdapter<GraduationConcertAdapter.Evening> {

    public static final String ACTIVITY_ID = "brew.graduation-concert";
    /** Cap on the key-change measures. */
    public static final int MAX_KEY_CHANGES = 64;

    /** Evening snapshot. */
    public record Evening(boolean cheered, int keyChanges, int best, int evenings, boolean abandoned) {
        public Evening {
            if (keyChanges < 0 || best < 0 || evenings < 1) throw new IllegalArgumentException("evening facts out of range");
            if (cheered && keyChanges > best + GraduationConcert.SLACK)
                throw new IllegalArgumentException("a cheered set is within slack of the best");
        }

        public static Evening of(GraduationConcert c, boolean abandoned) {
            if (c.result() == null && !abandoned) throw new IllegalArgumentException("concert still under way");
            boolean cheered = c.result() == GraduationConcert.Outcome.CHEERED;
            return new Evening(cheered, GraduationConcert.cost(c.setList()), c.best(), c.evening(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public GraduationConcertAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "graduation-concert", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("listening", "singing", "companionship"),
                Map.of("cheered", 1L, "key_changes", (long) MAX_KEY_CHANGES, "best", (long) MAX_KEY_CHANGES,
                        "evenings", 32L), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Evening r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.cheered() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("cheered", r.cheered() ? 1L : 0L);
        m.put("key_changes", Math.min((long) MAX_KEY_CHANGES, (long) r.keyChanges()));
        m.put("best", Math.min((long) MAX_KEY_CHANGES, (long) r.best()));
        m.put("evenings", Math.min(32L, (long) r.evenings()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}