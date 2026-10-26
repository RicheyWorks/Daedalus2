// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.DopplerFlyby;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G96 Doppler Flyby: the companion that heard the horn drop as the ark passed is credited once per
 * flyby. Naming the right ark at the right speed completes; anything else fails (right ark and right speed are kept
 * as separate measures). Read-only on the audio core.
 */
public final class DopplerFlybyAdapter implements ActivityResultAdapter<DopplerFlybyAdapter.Flyby> {

    public static final String ACTIVITY_ID = "audio.doppler-flyby";

    /** Flyby snapshot. */
    public record Flyby(boolean rightArk, boolean rightSpeed, int speed, boolean abandoned) {
        public Flyby {
            if (speed < 0) throw new IllegalArgumentException("negative speed");
        }

        public static Flyby of(DopplerFlyby.Verdict v, boolean abandoned) {
            return new Flyby(v.rightArk(), v.rightSpeed(), Math.max(0, v.speed()), abandoned);
        }

        boolean correct() { return rightArk && rightSpeed; }
    }

    private final ActivityDefinition definition;

    public DopplerFlybyAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "doppler-flyby", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "observation", "scouting"),
                Map.of("right_ark", 1L, "right_speed", 1L, "speed", 343L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Flyby r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("right_ark", Math.min(1L, (long) (r.rightArk() ? 1 : 0)));
        m.put("right_speed", Math.min(1L, (long) (r.rightSpeed() ? 1 : 0)));
        m.put("speed", Math.min(343L, (long) (r.speed())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
