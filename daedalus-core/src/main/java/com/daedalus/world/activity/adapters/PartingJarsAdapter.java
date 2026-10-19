// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.parting.PartingJars;

import java.util.Map;
import java.util.Set;

/** Read-only G12 mapping of G167's accepted plan: FULL_SHELF completes and SHORT fails. */
public final class PartingJarsAdapter implements ActivityResultAdapter<PartingJarsAdapter.Shelf> {
    public static final String ACTIVITY_ID = "brew.parting-jars";
    public static final int MAX_FAMILIES = 64;

    public record Shelf(int orders, int onTime, int best, boolean abandoned) {
        public Shelf {
            if (orders < 1 || onTime < 0 || best < 0 || best > orders || onTime > best)
                throw new IllegalArgumentException("inconsistent shelf counts");
        }

        public static Shelf of(PartingJars jars, boolean abandoned) {
            if (jars.last() == null && !abandoned)
                throw new IllegalArgumentException("parting-jar plan still in progress");
            return new Shelf(jars.orders().size(), jars.lastOnTime(), jars.best().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public PartingJarsAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "parting-jars", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("hauling", "planning", "companionship"),
                Map.of("orders", (long) MAX_FAMILIES, "on_time", (long) MAX_FAMILIES,
                        "best", (long) MAX_FAMILIES), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Shelf r) {
        ActivityOutcome outcome = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.onTime() == r.best() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), Map.of("orders", (long) Math.min(MAX_FAMILIES, r.orders()),
                        "on_time", (long) Math.min(MAX_FAMILIES, r.onTime()),
                        "best", (long) Math.min(MAX_FAMILIES, r.best())),
                s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
