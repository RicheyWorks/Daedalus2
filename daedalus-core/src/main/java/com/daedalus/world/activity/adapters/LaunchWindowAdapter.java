// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.launch.LaunchOption;
import com.daedalus.world.odds.launch.LaunchWindowQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
/**
 * G12 adapter for G68 The Launch Window: the ark's weather bird learns from the launch. A wise choice (within the
 * Keeper's tolerance of the best expected life) completes, whatever the sky did; an unwise launch is a failure. A
 * quest that has not SAILED is refused unless the host abandoned it. Souls are rounded to whole numbers.
 */
public final class LaunchWindowAdapter implements ActivityResultAdapter<LaunchWindowAdapter.Launch> {

    public static final String ACTIVITY_ID = "odds.launch-window";

    /** Launch snapshot. */
    public record Launch(boolean wise, int route, int day, int expectedSouls, int bestSouls, int soulsHome,
                         boolean abandoned) {
        public Launch {
            if (route < 0 || day < 0 || expectedSouls < 0 || bestSouls < 0 || soulsHome < 0)
                throw new IllegalArgumentException("negative launch facts");
        }

        public static Launch of(LaunchWindowQuest q, boolean abandoned) {
            if (q.stage() != LaunchWindowQuest.Stage.SAILED && !abandoned)
                throw new IllegalArgumentException("launch still in progress: " + q.stage());
            LaunchOption c = q.chosen();
            return new Launch(q.wise(), c == null ? 0 : c.route(), c == null ? 0 : c.day(),
                    c == null ? 0 : souls(c.expectedLife()), souls(q.best().expectedLife()), souls(q.lifeHome()),
                    abandoned);
        }

        private static int souls(double v) {
            return Double.isFinite(v) ? (int) Math.max(0, Math.min(1_000_000, Math.round(v))) : 0;
        }
    }

    private final ActivityDefinition definition;

    public LaunchWindowAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "launch-window", 1, "sky-islands", mode,
                Set.of("bird", "animal"), Set.of("observation", "scouting"),
                Map.of("wise", 1L, "route", 64L, "day", 64L, "expected_souls", 1_000_000L,
                        "best_souls", 1_000_000L, "souls_home", 1_000_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Launch l) {
        ActivityOutcome o = l.abandoned() ? ActivityOutcome.ABANDONED
                : l.wise() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("wise", l.wise() ? 1L : 0L);
        m.put("route", (long) l.route());
        m.put("day", (long) l.day());
        m.put("expected_souls", (long) l.expectedSouls());
        m.put("best_souls", (long) l.bestSouls());
        m.put("souls_home", (long) l.soulsHome());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}