// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.supper.HomecomingSupper;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G85 The Homecoming Supper (YTM story ch. 8): the companion that sat at the hearth while the
 * guests ate is credited once per supper. A warm supper (quest complete) completes; a supper with all
 * {@link HomecomingSupper#COURSES} records played and someone still discontent fails; anything earlier is refused
 * unless abandoned. Read-only on the core.
 */
public final class HomecomingSupperAdapter implements ActivityResultAdapter<HomecomingSupperAdapter.Supper> {

    public static final String ACTIVITY_ID = "brew.homecoming-supper";

    /** Supper snapshot. */
    public record Supper(boolean warm, int seated, int courses, int discontent, boolean abandoned) {
        public Supper {
            if (seated < 0 || courses < 0 || courses > HomecomingSupper.COURSES || discontent < 0 || discontent > seated)
                throw new IllegalArgumentException("supper facts out of range");
            if (warm && discontent > 0) throw new IllegalArgumentException("a warm supper leaves nobody discontent");
        }

        public static Supper of(HomecomingSupper s, boolean abandoned) {
            boolean warm = s.quest().complete();
            boolean ended = s.played().size() >= HomecomingSupper.COURSES;
            if (!warm && !ended && !abandoned) throw new IllegalArgumentException("supper still in progress");
            int seated = s.seating().size();
            return new Supper(warm, seated, Math.min(HomecomingSupper.COURSES, s.played().size()),
                    warm ? 0 : Math.min(seated, s.discontent().size()), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public HomecomingSupperAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "homecoming-supper", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("companionship", "listening", "guarding"),
                Map.of("seated", 32L, "courses", 3L, "discontent", 32L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Supper r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.warm() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("seated", Math.min(32L, (long) (r.seated())));
        m.put("courses", Math.min(3L, (long) (r.courses())));
        m.put("discontent", Math.min(32L, (long) (r.discontent())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
