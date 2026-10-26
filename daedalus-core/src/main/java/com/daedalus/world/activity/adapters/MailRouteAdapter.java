// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.parcels.MailRoute;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G14 mail route: a courier companion (a carrier pigeon, a satchel dog) learns route-finding from the
 * {@link MailRoute.Receipt} the route already settled. Every letter delivered completes; letters left in the bag are a
 * settleable failure.
 */
public final class MailRouteAdapter implements ActivityResultAdapter<MailRouteAdapter.Round> {

    public static final String ACTIVITY_ID = "parcels.mail-route";

    /** Round snapshot. {@code medal} is 3 gold, 2 silver, 1 bronze, 0 none. */
    public record Round(int delivered, int late, int undelivered, boolean ghostReturned, int stamps, int medal,
                        boolean abandoned) {
        public Round {
            if (delivered < 0 || late < 0 || undelivered < 0 || stamps < 0 || late > delivered || medal < 0 || medal > 3)
                throw new IllegalArgumentException("round facts do not add up");
        }

        public static Round of(MailRoute.Receipt r, boolean abandoned) {
            int medal = switch (r.medal()) { case GOLD -> 3; case SILVER -> 2; case BRONZE -> 1; case NONE -> 0; };
            return new Round(r.delivered(), r.late(), r.undelivered(), r.ghostReturned(), r.stamps(), medal, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public MailRouteAdapter(ActivityMode mode) {
        long l = MailRoute.MAX_LETTERS;
        definition = new ActivityDefinition(ACTIVITY_ID, "mail-route-round", 1, "parcels", mode,
                Set.of("animal", "bird"), Set.of("carrying", "scouting"),
                Map.of("delivered", l, "late", l, "undelivered", l, "ghost_returned", 1L, "stamps", 1_000L,
                        "medal", 3L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Round r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.undelivered() == 0 && r.delivered() > 0 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("delivered", (long) r.delivered());
        m.put("late", (long) r.late());
        m.put("undelivered", (long) r.undelivered());
        m.put("ghost_returned", r.ghostReturned() ? 1L : 0L);
        m.put("stamps", (long) r.stamps());
        m.put("medal", (long) r.medal());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
