// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.OwlFix;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G150 Owl Fix: the companion that listened at the four microphones while you placed the hooting owl
 * is credited once per fix. The exact cell completes, any other guess fails; the game's 0-100 score is kept. Read-only
 * on the audio core.
 */
public final class OwlFixAdapter implements ActivityResultAdapter<OwlFixAdapter.Fix> {

    public static final String ACTIVITY_ID = "audio.owl-fix";

    /** Fix snapshot. */
    public record Fix(boolean exact, int score, boolean abandoned) {
        public Fix {
            if (score < 0 || score > 100) throw new IllegalArgumentException("score out of range");
            if (exact && score != 100) throw new IllegalArgumentException("an exact fix scores 100");
        }

        public static Fix of(OwlFix.Verdict v, boolean abandoned) {
            return new Fix(v.exact(), Math.max(0, Math.min(100, v.score())), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public OwlFixAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "owl-fix", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "scouting", "observation"),
                Map.of("exact", 1L, "score", 100L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Fix r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.exact() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("exact", r.exact() ? 1L : 0L);
        m.put("score", (long) r.score());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
