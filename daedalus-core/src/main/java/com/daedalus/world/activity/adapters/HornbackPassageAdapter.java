// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.labyrinth.HornbackHerd;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G03 Calm the Hornbacks: a herding companion (a Kennel dog, a pack mule walking the trough route)
 * learns from the passage {@link HornbackHerd#run} already simulated. A GUIDED passage completes; a stampede or
 * timeout is a settleable failure, so the dog still learns from a hard day.
 */
public final class HornbackPassageAdapter implements ActivityResultAdapter<HornbackPassageAdapter.Passage> {

    public static final String ACTIVITY_ID = "labyrinth.hornback-passage";

    /** Snapshot of a finished passage (primitives only, so the receipt never holds the simulation). */
    public record Passage(HornbackHerd.Outcome outcome, int herd, int arrived, int calmArrived, int burned, int lost,
                          int drinks, boolean abandoned) {
        public Passage {
            if (outcome == null) throw new IllegalArgumentException("outcome required");
            if (herd < 1 || arrived < 0 || calmArrived < 0 || burned < 0 || lost < 0 || drinks < 0
                    || calmArrived > arrived || arrived + lost > herd)
                throw new IllegalArgumentException("passage facts do not add up");
        }

        public static Passage of(HornbackHerd.Report r, boolean abandoned) {
            return new Passage(r.outcome(), r.herd(), r.arrived(), r.calmArrived(), r.burned(), r.lost(), r.drinks(),
                    abandoned);
        }
    }

    private final ActivityDefinition definition;

    public HornbackPassageAdapter(ActivityMode mode) {
        long herd = HornbackHerd.MAX_HERD;
        definition = new ActivityDefinition(ACTIVITY_ID, "hornback-passage", 1, "labyrinth", mode,
                Set.of("animal"), Set.of("herding", "carrying", "guarding"),
                Map.of("herd", herd, "arrived", herd, "calm_arrived", herd, "burned", herd, "lost", herd,
                        "drinks", 10_000L, "guided", 1L), 3);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Passage p) {
        boolean guided = p.outcome() == HornbackHerd.Outcome.GUIDED;
        ActivityOutcome outcome = p.abandoned() ? ActivityOutcome.ABANDONED
                : guided ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("herd", (long) p.herd());
        m.put("arrived", (long) p.arrived());
        m.put("calm_arrived", (long) p.calmArrived());
        m.put("burned", (long) p.burned());
        m.put("lost", (long) p.lost());
        m.put("drinks", (long) p.drinks());
        m.put("guided", guided ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
