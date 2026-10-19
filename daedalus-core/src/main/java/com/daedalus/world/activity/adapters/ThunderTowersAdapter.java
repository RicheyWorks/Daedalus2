// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.ThunderTowers;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G89 Thunder Towers: the companion that counted the flash-to-thunder gaps with you is credited once
 * per storm. A correct strike cell completes, a wrong one fails. Read-only on the audio core.
 */
public final class ThunderTowersAdapter implements ActivityResultAdapter<ThunderTowersAdapter.Storm> {

    public static final String ACTIVITY_ID = "audio.thunder-towers";

    /** Storm snapshot: whether the strike was placed and the worst tower timing error (tenths of a second). */
    public record Storm(boolean correct, int towers, int worstErrorTenths, boolean abandoned) {
        public Storm {
            if (towers < 0 || worstErrorTenths < 0) throw new IllegalArgumentException("negative storm facts");
        }

        public static Storm of(ThunderTowers.Verdict v, boolean abandoned) {
            int worst = v.errorTenths().stream().mapToInt(Math::abs).max().orElse(0);
            return new Storm(v.correct(), v.errorTenths().size(), worst, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public ThunderTowersAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "thunder-towers-storm", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "counting", "observation"),
                Map.of("correct", 1L, "towers", 16L, "worst_error_tenths", 1000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Storm r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("correct", Math.min(1L, (long) (r.correct() ? 1 : 0)));
        m.put("towers", Math.min(16L, (long) (r.towers())));
        m.put("worst_error_tenths", Math.min(1000L, (long) (r.worstErrorTenths())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
