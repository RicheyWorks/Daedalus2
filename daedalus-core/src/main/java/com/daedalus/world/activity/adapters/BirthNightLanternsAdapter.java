// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.odds.match.BirthNightQuest;

import java.util.Map;
import java.util.Set;

/** Read-only G12 mapping of G157; both Keeper nods complete, independent of the random crew's birthdays. */
public final class BirthNightLanternsAdapter
        implements ActivityResultAdapter<BirthNightLanternsAdapter.Muster> {
    public static final String ACTIVITY_ID = "odds.birth-night-lanterns";

    public record Muster(int nods, int closestGap, boolean shared, boolean abandoned) {
        public Muster {
            if (nods < 0 || nods > 2 || closestGap < 0 || closestGap > BirthNightQuest.NIGHTS)
                throw new IllegalArgumentException("muster facts out of range");
            if (shared && closestGap != 0) throw new IllegalArgumentException("shared nights have zero gap");
        }

        public static Muster of(BirthNightQuest quest, boolean abandoned) {
            if (quest.stage() != BirthNightQuest.Stage.MUSTERED && !abandoned)
                throw new IllegalArgumentException("birth-night guesses still in progress");
            return new Muster(quest.nods(), Math.max(0, quest.closestGap()), quest.crewShares(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public BirthNightLanternsAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "birth-night-lanterns", 1, "sky-islands", mode,
                Set.of("animal", "bird"), Set.of("counting", "observation", "companionship"),
                Map.of("nods", 2L, "closest_gap", (long) BirthNightQuest.NIGHTS, "shared", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Muster r) {
        ActivityOutcome outcome = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.nods() == 2 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), Map.of("nods", (long) r.nods(), "closest_gap", (long) r.closestGap(),
                        "shared", r.shared() ? 1L : 0L), s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
