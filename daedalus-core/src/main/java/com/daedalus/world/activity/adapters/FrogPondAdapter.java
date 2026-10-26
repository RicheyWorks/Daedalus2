// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.audio.FrogPondNiches;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G130 Frog Pond Niches: the companion that listened at the regrown wetland while you sorted the
 * returning frogs into ponds is credited once per wetland. An assignment the game judges clear (no masking pair in
 * any pond) completes, anything else fails; the species count is kept. Read-only on the audio core.
 */
public final class FrogPondAdapter implements ActivityResultAdapter<FrogPondAdapter.Wetland> {

    public static final String ACTIVITY_ID = "audio.frog-pond-niches";
    /** Most species a wetland can hold. */
    public static final int MAX_SPECIES = 10;

    /** Wetland snapshot. */
    public record Wetland(boolean clear, int species, boolean abandoned) {
        public Wetland {
            if (species < 0 || species > MAX_SPECIES) throw new IllegalArgumentException("species out of range");
        }

        public static Wetland of(FrogPondNiches w, FrogPondNiches.Verdict v, boolean abandoned) {
            return new Wetland(v.ok(), w.frogs().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public FrogPondAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "frog-pond-niches", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "observation", "habitat"),
                Map.of("clear", 1L, "species", (long) MAX_SPECIES), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Wetland r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.clear() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("clear", r.clear() ? 1L : 0L);
        m.put("species", Math.min((long) MAX_SPECIES, (long) r.species()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}