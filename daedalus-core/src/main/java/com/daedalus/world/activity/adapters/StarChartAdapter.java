// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.collect.ChartCollectorQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G125 The Torn Star Chart: the companion that helped haul the salvage crates is credited once per
 * voyage. A full chart (with or without the Keeper's trade-in) completes, a torn one fails; a skiff still planning is
 * refused unless the host abandoned the quest. Read-only on the odds core.
 */
public final class StarChartAdapter implements ActivityResultAdapter<StarChartAdapter.Haul> {

    public static final String ACTIVITY_ID = "odds.star-chart";

    /** Haul snapshot. */
    public record Haul(boolean charted, int traded, boolean abandoned) {
        public Haul {
            if (traded < 0 || traded > ChartCollectorQuest.FRAGMENTS)
                throw new IllegalArgumentException("traded out of range");
            if (!charted && traded != 0) throw new IllegalArgumentException("only a charted haul trades pieces");
        }

        public static Haul of(ChartCollectorQuest q, boolean abandoned) {
            if (q.stage() == ChartCollectorQuest.Stage.PLANNING && !abandoned)
                throw new IllegalArgumentException("skiff still planning: PLANNING");
            return new Haul(q.stage() == ChartCollectorQuest.Stage.CHARTED, q.traded(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public StarChartAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "star-chart", 1, "sky-islands", mode,
                Set.of("animal", "bird"), Set.of("scouting", "hauling", "observation"),
                Map.of("charted", 1L, "traded", (long) ChartCollectorQuest.FRAGMENTS), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Haul r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.charted() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("charted", r.charted() ? 1L : 0L);
        m.put("traded", (long) r.traded());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}