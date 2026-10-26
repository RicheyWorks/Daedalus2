// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.audio.DrumRollId;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G138 Drum Roll ID: the companion that listened at the regrown snags with you is credited once per
 * roll. Naming the drumming woodpecker the game judges right completes, a wrong name fails. Read-only on the audio
 * core.
 */
public final class DrumRollAdapter implements ActivityResultAdapter<DrumRollAdapter.Roll> {

    public static final String ACTIVITY_ID = "audio.drum-roll-id";

    /** Roll snapshot. */
    public record Roll(boolean correct, int beats, boolean abandoned) {
        public Roll {
            if (beats < 0 || beats > 1_000) throw new IllegalArgumentException("beats out of range");
        }

        public static Roll of(DrumRollId d, String guess, boolean abandoned) {
            return new Roll(d.judge(guess), d.onsets().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public DrumRollAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "drum-roll-id", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "observation", "counting"),
                Map.of("correct", 1L, "beats", 1_000L), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Roll r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("correct", r.correct() ? 1L : 0L);
        m.put("beats", (long) r.beats());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}