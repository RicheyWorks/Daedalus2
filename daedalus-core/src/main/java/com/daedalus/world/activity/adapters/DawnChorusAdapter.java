// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.audio.DawnChorusCensus;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G124 Dawn Chorus Census: the companion that sat out the regrown meadow's dawn with you is credited
 * once per census. Naming both the most abundant and the missing species completes, anything else fails. Read-only on
 * the audio core; the snapshot is built from the game's own judged {@code Verdict}.
 */
public final class DawnChorusAdapter implements ActivityResultAdapter<DawnChorusAdapter.Census> {

    public static final String ACTIVITY_ID = "audio.dawn-chorus-census";

    /** Census snapshot. */
    public record Census(boolean rightLoudest, boolean rightMissing, boolean abandoned) {
        public static Census of(DawnChorusCensus.Verdict v, boolean abandoned) {
            return new Census(v.rightLoudest(), v.rightMissing(), abandoned);
        }

        public boolean correct() { return rightLoudest && rightMissing; }
    }

    private final ActivityDefinition definition;

    public DawnChorusAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "dawn-chorus-census", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "counting", "observation"),
                Map.of("right_loudest", 1L, "right_missing", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Census r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("right_loudest", r.rightLoudest() ? 1L : 0L);
        m.put("right_missing", r.rightMissing() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}