// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.labyrinth.EchoBellGate;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G01 Echo Bell gate: the Echo Crickets that widen the timing window (a colony) and any companion
 * listening with the player learn from the {@link EchoBellGate.Verdict} the gate already judged. Misses only reset
 * the puzzle, so attempts are counted but never penalised here.
 */
public final class EchoBellAdapter implements ActivityResultAdapter<EchoBellAdapter.Listening> {

    public static final String ACTIVITY_ID = "labyrinth.echo-bell";
    public static final int MAX_BELLS = 32;
    public static final int MAX_ATTEMPTS = 99;

    /** A finished listening session: bells in the peal, echoes hit on the last attempt, attempts made, gate opened. */
    public record Listening(int bells, int hits, int attempts, boolean open, boolean abandoned) {
        public Listening {
            if (bells < 1 || hits < 0 || hits > bells || attempts < 1)
                throw new IllegalArgumentException("listening facts do not add up");
            if (open && hits != bells) throw new IllegalArgumentException("an open gate hit every echo");
        }

        /** From the gate and its last verdict. */
        public static Listening of(EchoBellGate gate, EchoBellGate.Verdict last, int attempts, boolean abandoned) {
            return new Listening(gate.rings().size(), last.hits(), attempts, last.open(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public EchoBellAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "echo-bell-listening", 1, "labyrinth", mode,
                Set.of("animal", "bird", "social_insect"), Set.of("observation", "scouting", "signaling"),
                Map.of("bells", (long) MAX_BELLS, "hits", (long) MAX_BELLS, "attempts", (long) MAX_ATTEMPTS,
                        "gate_open", 1L), 3);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Listening l) {
        ActivityOutcome outcome = l.abandoned() ? ActivityOutcome.ABANDONED
                : l.open() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("bells", (long) l.bells());
        m.put("hits", (long) l.hits());
        m.put("attempts", (long) Math.min(l.attempts(), MAX_ATTEMPTS));
        m.put("gate_open", l.open() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
