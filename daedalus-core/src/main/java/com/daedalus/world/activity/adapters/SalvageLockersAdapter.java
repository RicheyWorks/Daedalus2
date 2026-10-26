// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.odds.lockers.LockerQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G141 The Salvage Lockers: the companion that watched the wreck's lockers open beside you is credited
 * once per salvage. Finding the compass in {@link LockerQuest#GOAL} of {@link LockerQuest#ROUNDS} rounds completes,
 * coming up short fails; a salvage still dealing is refused unless the host abandoned it. Read-only on the odds core.
 */
public final class SalvageLockersAdapter implements ActivityResultAdapter<SalvageLockersAdapter.Salvage> {

    public static final String ACTIVITY_ID = "odds.salvage-lockers";

    /** Salvage snapshot. */
    public record Salvage(boolean enough, int found, int voids, int rounds, boolean abandoned) {
        public Salvage {
            int n = LockerQuest.ROUNDS;
            if (rounds < 0 || rounds > n || found < 0 || voids < 0 || found + voids > rounds)
                throw new IllegalArgumentException("salvage facts out of range");
            if (enough && found < LockerQuest.GOAL) throw new IllegalArgumentException("enough needs the goal");
        }

        public static Salvage of(LockerQuest q, boolean abandoned) {
            LockerQuest.Stage st = q.stage();
            boolean over = st == LockerQuest.Stage.FOUND_ENOUGH || st == LockerQuest.Stage.CAME_UP_SHORT;
            if (!over && !abandoned) throw new IllegalArgumentException("salvage still in progress: " + st);
            return new Salvage(st == LockerQuest.Stage.FOUND_ENOUGH, q.found(), q.voids(), q.round(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public SalvageLockersAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "salvage-lockers", 1, "sky-islands", mode,
                Set.of("animal", "bird"), Set.of("scouting", "observation", "judgement"),
                Map.of("enough", 1L, "found", (long) LockerQuest.ROUNDS, "voids", (long) LockerQuest.ROUNDS,
                        "rounds", (long) LockerQuest.ROUNDS), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Salvage r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.enough() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("enough", r.enough() ? 1L : 0L);
        m.put("found", (long) r.found());
        m.put("voids", (long) r.voids());
        m.put("rounds", (long) r.rounds());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
