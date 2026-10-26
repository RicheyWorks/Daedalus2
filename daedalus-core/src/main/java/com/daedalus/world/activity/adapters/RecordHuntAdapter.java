// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.hunt.RecordHunt;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G46 Ark Record Hunt (YTM story ch. 3): the companion that tracked the Archivist's hums with you is
 * credited once per hunt. A finished quest ({@link RecordHunt#RECORDS_FOR_QUEST} records home) completes; a hunt
 * still in play is refused unless the host abandoned it, and an abandoned hunt keeps its facts. Read-only on the core.
 */
public final class RecordHuntAdapter implements ActivityResultAdapter<RecordHuntAdapter.Hunt> {

    public static final String ACTIVITY_ID = "brew.ark-record-hunt";

    /** Hunt snapshot. */
    public record Hunt(boolean questComplete, int found, int remaining, int days, boolean abandoned) {
        public Hunt {
            if (found < 0 || remaining < 0 || days < 0) throw new IllegalArgumentException("negative hunt facts");
            if (questComplete && found < RecordHunt.RECORDS_FOR_QUEST)
                throw new IllegalArgumentException("quest complete needs " + RecordHunt.RECORDS_FOR_QUEST + " records");
        }

        public static Hunt of(RecordHunt h, boolean abandoned) {
            boolean done = h.quest().complete();
            if (!done && !abandoned) throw new IllegalArgumentException("hunt still in progress");
            return new Hunt(done, h.found().size(), h.remaining(), h.day(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public RecordHuntAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "ark-record-hunt", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("scouting", "foraging", "listening"),
                Map.of("found", 64L, "remaining", 64L, "days", 365L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Hunt r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.questComplete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("found", Math.min(64L, (long) (r.found())));
        m.put("remaining", Math.min(64L, (long) (r.remaining())));
        m.put("days", Math.min(365L, (long) (r.days())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
