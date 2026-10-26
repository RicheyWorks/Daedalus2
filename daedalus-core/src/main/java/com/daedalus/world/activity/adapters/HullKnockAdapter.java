// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.HullKnockSurvey;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G101 Hull Knock Survey: the companion that tapped plates and listened for the dull ring is credited
 * once per survey. A perfect survey (every cracked plate marked, no false alarm) completes; otherwise it fails.
 * Read-only on the audio core.
 */
public final class HullKnockAdapter implements ActivityResultAdapter<HullKnockAdapter.Survey> {

    public static final String ACTIVITY_ID = "audio.hull-knock-survey";

    /** Survey snapshot. */
    public record Survey(int hits, int misses, int falseAlarms, boolean abandoned) {
        public Survey {
            if (hits < 0 || misses < 0 || falseAlarms < 0) throw new IllegalArgumentException("negative survey facts");
        }

        public static Survey of(HullKnockSurvey.Verdict v, boolean abandoned) {
            return new Survey(v.hits(), v.misses(), v.falseAlarms(), abandoned);
        }

        boolean perfect() { return misses == 0 && falseAlarms == 0; }
    }

    private final ActivityDefinition definition;

    public HullKnockAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "hull-knock-survey", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "guarding", "observation"),
                Map.of("hits", 256L, "misses", 256L, "false_alarms", 256L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Survey r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.perfect() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("hits", Math.min(256L, (long) (r.hits())));
        m.put("misses", Math.min(256L, (long) (r.misses())));
        m.put("false_alarms", Math.min(256L, (long) (r.falseAlarms())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
