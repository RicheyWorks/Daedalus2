// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.MarkRecapture;

import java.util.Map;
import java.util.Set;

/** Read-only G12 mapping of G156's completed census; only the core's ACCURATE verdict completes. */
public final class TagAndCountAdapter implements ActivityResultAdapter<TagAndCountAdapter.Census> {
    public static final String ACTIVITY_ID = "ecology.tag-and-count";
    public static final int MAX_COUNT = 1_000_000;

    /** Host snapshot of a returned census. No simulation or harvest is performed by the adapter. */
    public record Census(int marked, int caught, int recaptured, boolean accurate, boolean abandoned) {
        public Census {
            if (marked < 0 || caught < 0 || recaptured < 0 || recaptured > Math.min(marked, caught))
                throw new IllegalArgumentException("inconsistent census counts");
        }

        /** A missing result is still in play, accepted only as an abandonment. */
        public static Census of(MarkRecapture.Census result, boolean abandoned) {
            if (result == null) {
                if (!abandoned) throw new IllegalArgumentException("census still in progress");
                return new Census(0, 0, 0, false, true);
            }
            if (result.truth() < 1 || result.marked() > result.truth() || result.caught() > result.truth())
                throw new IllegalArgumentException("inconsistent census population");
            return new Census(result.marked(), result.caught(), result.recaptured(),
                    result.verdict() == MarkRecapture.Verdict.ACCURATE, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public TagAndCountAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "tag-and-count", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("counting", "observation", "scouting"),
                Map.of("marked", (long) MAX_COUNT, "caught", (long) MAX_COUNT,
                        "recaptured", (long) MAX_COUNT, "accurate", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Census r) {
        ActivityOutcome outcome = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.accurate() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), Map.of("marked", (long) Math.min(MAX_COUNT, r.marked()),
                        "caught", (long) Math.min(MAX_COUNT, r.caught()),
                        "recaptured", (long) Math.min(MAX_COUNT, r.recaptured()), "accurate", r.accurate() ? 1L : 0L),
                s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
