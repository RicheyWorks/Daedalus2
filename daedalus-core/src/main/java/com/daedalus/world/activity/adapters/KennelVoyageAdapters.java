// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.companion.KennelArkLandfall;
import com.daedalus.world.companion.KennelArkVoyage;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 receipts for the Kennel Isle ark voyage chapters (contest G161, art-master-flex): G140 "Crossing the Storm Belt"
 * ({@link CrossingAdapter}) and G147 "Landfall on the Cinder Shelf" ({@link ShoreAdapter}). Each reads the result the
 * companion code already simulated; {@link #registerAll} adds both to a router without touching the hub. Companion of
 * {@link KennelArkAdapters} (G118).
 */
public final class KennelVoyageAdapters {
    public static final String CROSSING_ID = "kennel.crossing-the-storm-belt";
    public static final String SHORE_ID = "kennel.landfall-cinder-shelf";
    public static final int MAX_PLANKS = KennelArkLandfall.DAYS * (KennelArkLandfall.FETCH_PLANKS + KennelArkLandfall.HAUL_PLANKS);

    private KennelVoyageAdapters() {
    }

    private static ActivityDefinition def(String id, ActivityMode mode, Map<String, Long> max) {
        return new ActivityDefinition(id, id.replace('.', '-'), 1, "kennel-isle", mode, Set.of("animal"),
                Set.of("guarding", "carrying", "companion"), max, 2);
    }

    private static ActivityOutcome outcome(boolean abandoned, boolean complete) {
        return abandoned ? ActivityOutcome.ABANDONED : complete ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
    }

    private static ActivityResultReceipt issue(ActivityDefinition d, ActivityResultAdapter.Session s, ActivityOutcome o,
                                               Map<String, Long> m) {
        return ActivityResultReceipt.issue(d, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(), o,
                s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }

    /** Registers both voyage chapter adapters with inactive award policies (husbandry / rescue tracks). */
    public static void registerAll(ActivityRouter r, ActivityMode mode) {
        r.register(new CrossingAdapter(mode), CrossingAdapter.Crossing.class,
                AwardPolicy.inactive(CROSSING_ID, "mastery.husbandry"));
        r.register(new ShoreAdapter(mode), ShoreAdapter.Shore.class, AwardPolicy.inactive(SHORE_ID, "mastery.rescue"));
    }

    /** G140 Crossing the Storm Belt: legs sailed, troubles answered, hull and water left. */
    public static final class CrossingAdapter implements ActivityResultAdapter<CrossingAdapter.Crossing> {
        public record Crossing(boolean arrived, int legs, int answered, int hull, int water, boolean abandoned) {
            public Crossing {
                if (legs < 0 || legs > KennelArkVoyage.LEGS || answered < 0 || answered > legs || hull < 0
                        || hull > KennelArkVoyage.START_HULL || water < 0 || water > KennelArkVoyage.START_WATER
                        || (arrived && (hull == 0 || water == 0)) || (!arrived && legs > 0 && hull > 0 && water > 0)) {
                    throw new IllegalArgumentException("crossing facts do not add up");
                }
            }

            public static Crossing of(KennelArkVoyage.Voyage v, boolean abandoned) {
                int answered = (int) v.legs().stream().filter(KennelArkVoyage.Leg::answered).count();
                return new Crossing(v.arrived(), v.legs().size(), answered, v.hull(), v.water(), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public CrossingAdapter(ActivityMode mode) {
            definition = def(CROSSING_ID, mode, Map.of("complete", 1L, "legs", (long) KennelArkVoyage.LEGS,
                    "answered", (long) KennelArkVoyage.LEGS, "hull", (long) KennelArkVoyage.START_HULL,
                    "water", (long) KennelArkVoyage.START_WATER));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Crossing w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.arrived() ? 1L : 0L);
            m.put("legs", (long) w.legs());
            m.put("answered", (long) w.answered());
            m.put("hull", (long) w.hull());
            m.put("water", (long) w.water());
            return issue(definition, s, outcome(w.abandoned(), w.arrived()), m);
        }
    }

    /** G147 Landfall on the Cinder Shelf: repair days, planks, hull and water at the end, animals rescued. */
    public static final class ShoreAdapter implements ActivityResultAdapter<ShoreAdapter.Shore> {
        public record Shore(boolean seaworthy, int days, int planks, int hull, int water, int rescued, boolean abandoned) {
            public Shore {
                if (days < 0 || days > KennelArkLandfall.DAYS || planks < 0 || planks > MAX_PLANKS || hull < 0
                        || hull > KennelArkLandfall.HULL_FULL || water < 0 || water > KennelArkVoyage.START_WATER
                        || rescued < 0 || rescued > Math.min(days, KennelArkLandfall.STRANDED_COUNT)
                        || (seaworthy && (hull != KennelArkLandfall.HULL_FULL || water == 0))) {
                    throw new IllegalArgumentException("landfall facts do not add up");
                }
            }

            /** The whole chapter; a voyage that never reached the shelf files a failed receipt with its hull and water. */
            public static Shore of(KennelArkLandfall.Chapter c, boolean abandoned) {
                KennelArkLandfall.Landfall l = c.landfall();
                if (l == null) {
                    return new Shore(false, 0, 0, c.voyage().hull(), c.voyage().water(), 0, abandoned);
                }
                int planks = l.days().stream().mapToInt(KennelArkLandfall.Day::planks).sum();
                return new Shore(l.seaworthy(), l.days().size(), planks, l.hull(), l.water(), l.rescued().size(), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public ShoreAdapter(ActivityMode mode) {
            definition = def(SHORE_ID, mode, Map.of("complete", 1L, "days", (long) KennelArkLandfall.DAYS,
                    "planks", (long) MAX_PLANKS, "hull", (long) KennelArkLandfall.HULL_FULL,
                    "water", (long) KennelArkVoyage.START_WATER, "rescued", (long) KennelArkLandfall.STRANDED_COUNT));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Shore w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.seaworthy() ? 1L : 0L);
            m.put("days", (long) w.days());
            m.put("planks", (long) w.planks());
            m.put("hull", (long) w.hull());
            m.put("water", (long) w.water());
            m.put("rescued", (long) w.rescued());
            return issue(definition, s, outcome(w.abandoned(), w.seaworthy()), m);
        }
    }
}
