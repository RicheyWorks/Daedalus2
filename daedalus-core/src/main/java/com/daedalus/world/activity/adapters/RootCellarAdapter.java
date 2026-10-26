// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.cellar.RootCellar;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G73 The Root Cellar (YTM story ch. 7): the companion that carried salt and minded the smokehouse
 * is credited once per Long Dark. A finished quest completes; a Long Dark that ended without the quest done fails;
 * before the dark is over the run is refused unless abandoned. Read-only on the core.
 */
public final class RootCellarAdapter implements ActivityResultAdapter<RootCellarAdapter.Cellar> {

    public static final String ACTIVITY_ID = "brew.root-cellar";

    /** Cellar snapshot. */
    public record Cellar(boolean questComplete, int jars, int badSeals, int day, boolean abandoned) {
        public Cellar {
            if (jars < 0 || jars > RootCellar.CAPACITY) throw new IllegalArgumentException("jars out of range");
            if (badSeals < 0 || badSeals > jars) throw new IllegalArgumentException("bad seals out of range");
            if (day < 0) throw new IllegalArgumentException("negative day");
        }

        public static Cellar of(RootCellar c, boolean abandoned) {
            boolean done = c.quest().complete();
            if (!done && !c.darkOver() && !abandoned) throw new IllegalArgumentException("cellar still in progress");
            int bad = (int) c.jars().stream().filter(RootCellar.Jar::badSeal).count();
            return new Cellar(done, c.jars().size(), bad, c.day(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public RootCellarAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "root-cellar-long-dark", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("carrying", "foraging", "guarding"),
                Map.of("jars", 12L, "bad_seals", 12L, "day", 365L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Cellar r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.questComplete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("jars", Math.min(12L, (long) (r.jars())));
        m.put("bad_seals", Math.min(12L, (long) (r.badSeals())));
        m.put("day", Math.min(365L, (long) (r.day())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
