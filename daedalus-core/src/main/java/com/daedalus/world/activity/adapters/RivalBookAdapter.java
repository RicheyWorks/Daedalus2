// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.rival.RivalBookQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
/**
 * G12 adapter for G77 The Rival Book: the companion that sniffed out the rival's soft lines learns from the quest.
 * EXPOSED completes; FOOLED is a failure; a book still SCANNING is refused unless the host abandoned it.
 */
public final class RivalBookAdapter implements ActivityResultAdapter<RivalBookAdapter.Scan> {

    public static final String ACTIVITY_ID = "odds.rival-book";

    /** Scan snapshot. */
    public record Scan(boolean exposed, int valueLines, int found, int miscalls, int reward, boolean abandoned) {
        public Scan {
            if (valueLines < 0 || found < 0 || miscalls < 0 || reward < 0)
                throw new IllegalArgumentException("negative scan facts");
            if (found > valueLines) throw new IllegalArgumentException("found exceeds value lines");
            if (miscalls > RivalBookQuest.MAX_MISCALLS) throw new IllegalArgumentException("miscalls out of range");
        }

        public static Scan of(RivalBookQuest q, boolean abandoned) {
            if (q.stage() == RivalBookQuest.Stage.SCANNING && !abandoned)
                throw new IllegalArgumentException("scan still in progress: SCANNING");
            return new Scan(q.stage() == RivalBookQuest.Stage.EXPOSED, q.valueLines(), q.found(), q.miscalls(),
                    q.reward(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public RivalBookAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "rival-book", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("scouting", "observation"),
                Map.of("exposed", 1L, "value_lines", 64L, "found", 64L,
                        "miscalls", (long) RivalBookQuest.MAX_MISCALLS, "reward", 1_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Scan c) {
        ActivityOutcome o = c.abandoned() ? ActivityOutcome.ABANDONED
                : c.exposed() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("exposed", c.exposed() ? 1L : 0L);
        m.put("value_lines", (long) c.valueLines());
        m.put("found", (long) c.found());
        m.put("miscalls", (long) c.miscalls());
        m.put("reward", (long) c.reward());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}