// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.brew.round.HarbourRound;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G139 The Harbour Round (YTM story ch. 13): the companion that held a voice in the children's round
 * as the far ark came in is credited once per chapter run. A sweet round sung at the harbour (the quest is past its
 * sing step) completes; until then the chapter is refused unless the host abandoned it. The last round's harmony is
 * kept in whole percent. Read-only on the core.
 */
public final class HarbourRoundAdapter implements ActivityResultAdapter<HarbourRoundAdapter.Harbour> {

    public static final String ACTIVITY_ID = "brew.harbour-round";
    /** Quest step index once the harbour round was sweet (rehearse, sing, talk). */
    static final int SUNG_STEP = 2;

    /** Harbour snapshot. */
    public record Harbour(boolean sweet, int harmonyPct, boolean abandoned) {
        public Harbour {
            if (harmonyPct < 0 || harmonyPct > 100) throw new IllegalArgumentException("harmony out of range");
        }

        public static Harbour of(HarbourRound r, boolean abandoned) {
            boolean sweet = r.quest().complete() || r.quest().stepIndex() >= SUNG_STEP;
            if (!sweet && !abandoned) throw new IllegalArgumentException("round still in progress");
            double h = r.lastHarmony();
            int pct = Double.isFinite(h) ? (int) Math.max(0, Math.min(100, Math.round(h * 100))) : 0;
            return new Harbour(sweet, pct, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public HarbourRoundAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "harbour-round", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("listening", "singing", "companionship"),
                Map.of("sweet", 1L, "harmony_pct", 100L), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Harbour r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.sweet() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("sweet", r.sweet() ? 1L : 0L);
        m.put("harmony_pct", (long) r.harmonyPct());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}