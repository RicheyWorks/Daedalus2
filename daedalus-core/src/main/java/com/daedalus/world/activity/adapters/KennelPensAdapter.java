// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.companion.KennelArkLandfall;
import com.daedalus.world.companion.KennelArkPens;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 receipt for the Kennel Isle ark chapter G180 "The Warm Crates" (contest G185, art-master-flex): animals brought
 * home, penned and unpenned, pens built, planks used and left (straight from the merged G180 {@link KennelArkPens.Plan},
 * no recomputed stand-ins);
 * {@link #registerAll} adds it to a router without touching the hub. Companion of {@link KennelVoyageAdapters} (G161).
 */
public final class KennelPensAdapter implements ActivityResultAdapter<KennelPensAdapter.Pens> {
    public static final String ID = "kennel.the-warm-crates";
    public static final int MAX_ANIMALS = KennelArkLandfall.STRANDED_COUNT;
    public static final int MAX_PLANKS = KennelArkPens.STORES + KennelVoyageAdapters.MAX_PLANKS;

    /** The chapter's facts; a ship that never came home files a failed receipt with zeros. */
    public record Pens(boolean complete, int animals, int penned, int unpenned, int pens, int planksUsed,
                       int planksLeft, boolean abandoned) {
        public Pens {
            if (animals < 0 || animals > MAX_ANIMALS || penned < 0 || unpenned < 0 || penned + unpenned != animals
                    || pens < 0 || pens > penned
                    || planksUsed < pens || planksLeft < 0 || planksUsed + planksLeft > MAX_PLANKS
                    || (penned > 0 && pens == 0) || (complete && (animals == 0 || penned != animals))) {
                throw new IllegalArgumentException("warm crates facts do not add up");
            }
        }

        public static Pens of(KennelArkPens.WarmCrates w, boolean abandoned) {
            KennelArkPens.Plan p = w.plan();
            if (p == null) {
                return new Pens(false, 0, 0, 0, 0, 0, 0, abandoned);
            }
            return new Pens(w.complete(), p.penned().size() + p.unpenned().size(), p.penned().size(),
                    p.unpenned().size(), p.built().size(), p.planksUsed(), p.planksLeft(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public KennelPensAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ID, ID.replace('.', '-'), 1, "kennel-isle", mode, Set.of("animal"),
                Set.of("building", "carrying", "companion"), Map.of("complete", 1L, "animals", (long) MAX_ANIMALS,
                        "penned", (long) MAX_ANIMALS, "unpenned", (long) MAX_ANIMALS, "pens", (long) MAX_ANIMALS,
                        "planks_used", (long) MAX_PLANKS, "planks_left", (long) MAX_PLANKS,
                        "planks_start", (long) MAX_PLANKS), 2);
    }

    /** Registers the Warm Crates adapter with an inactive award policy (rescue track). */
    public static void registerAll(ActivityRouter r, ActivityMode mode) {
        r.register(new KennelPensAdapter(mode), Pens.class, AwardPolicy.inactive(ID, "mastery.rescue"));
    }

    @Override
    public ActivityDefinition definition() {
        return definition;
    }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Pens w) {
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("complete", w.complete() ? 1L : 0L);
        m.put("animals", (long) w.animals());
        m.put("penned", (long) w.penned());
        m.put("unpenned", (long) w.unpenned());
        m.put("pens", (long) w.pens());
        m.put("planks_used", (long) w.planksUsed());
        m.put("planks_left", (long) w.planksLeft());
        m.put("planks_start", (long) (w.planksUsed() + w.planksLeft()));
        ActivityOutcome o = w.abandoned() ? ActivityOutcome.ABANDONED
                : w.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(), o,
                s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
