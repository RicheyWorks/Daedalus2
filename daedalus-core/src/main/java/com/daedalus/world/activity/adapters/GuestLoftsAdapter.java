// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.lofts.GuestLofts;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G149 The Guest Lofts: the companion that helped Aunt Brine air the lofts is credited once per
 * visit. Settling snug (lofts aired = the fewest possible) completes, sprawl fails; a visit not yet settled is refused
 * unless the host abandoned it. Read-only on the brew core.
 */
public final class GuestLoftsAdapter implements ActivityResultAdapter<GuestLoftsAdapter.Stay> {

    public static final String ACTIVITY_ID = "brew.guest-lofts";

    /** Visit snapshot. */
    public record Stay(int aired, int fewest, int families, boolean snug, boolean abandoned) {
        public Stay {
            if (aired < 0 || fewest < 0 || families < 0) throw new IllegalArgumentException("negative stay facts");
            if (aired > GuestLofts.LOFTS || fewest > GuestLofts.LOFTS) throw new IllegalArgumentException("too many lofts");
            if (snug && aired != fewest) throw new IllegalArgumentException("snug means aired equals fewest");
        }

        public static Stay of(GuestLofts g, boolean abandoned) {
            GuestLofts.Outcome s = g.settled();
            if (s == null && !abandoned) throw new IllegalArgumentException("visit still in progress");
            return new Stay(g.aired(), g.fewest(), g.families().size(), s == GuestLofts.Outcome.SNUG, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public GuestLoftsAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "guest-lofts", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("companionship", "planning", "housekeeping"),
                Map.of("aired", (long) GuestLofts.LOFTS, "fewest", (long) GuestLofts.LOFTS, "families", 64L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Stay r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.snug() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("aired", (long) r.aired());
        m.put("fewest", (long) r.fewest());
        m.put("families", (long) Math.min(64, r.families()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
