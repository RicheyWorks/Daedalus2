// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.forge.ScarDig;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G132 Meteor Scar Dig: the companion that carried the canteens is credited once per dig. Walking off
 * the scar with at least one smelted ingot and without fainting completes; fainting or an empty haul fails. A dig
 * result is final once run, so only the host's abandon flag overrides it. Read-only on the forge core.
 */
public final class ScarDigAdapter implements ActivityResultAdapter<ScarDigAdapter.Dig> {

    public static final String ACTIVITY_ID = "forge.scar-dig";
    /** Cap on ore and ingot measures. */
    public static final int MAX_ORE = ScarDig.SIZE * ScarDig.SIZE * 2;

    /** Dig snapshot. */
    public record Dig(int ingots, int starmetal, int emberite, int water, boolean fainted, boolean abandoned) {
        public Dig {
            if (ingots < 0 || starmetal < 0 || emberite < 0) throw new IllegalArgumentException("negative haul");
            if (water < 0) throw new IllegalArgumentException("negative water");
        }

        public static Dig of(ScarDig.Result r, boolean abandoned) {
            return new Dig(r.ingots(), r.starmetal(), r.emberite(), Math.max(0, r.water()), r.fainted(), abandoned);
        }

        public boolean struck() { return !fainted && ingots > 0; }
    }

    private final ActivityDefinition definition;

    public ScarDigAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "scar-dig", 1, "shattered-planet", mode,
                Set.of("animal"), Set.of("hauling", "endurance", "prospecting"),
                Map.of("ingots", (long) MAX_ORE, "starmetal", (long) MAX_ORE, "emberite", (long) MAX_ORE,
                        "water", 1000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Dig r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.struck() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("ingots", (long) Math.min(MAX_ORE, r.ingots()));
        m.put("starmetal", (long) Math.min(MAX_ORE, r.starmetal()));
        m.put("emberite", (long) Math.min(MAX_ORE, r.emberite()));
        m.put("water", (long) Math.min(1000, r.water()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
