// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import com.daedalus.world.companion.TonicBottler.Bottle;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.SplittableRandom;

/**
 * Kennel Isle ark hound rescue (contest gap G50). When the planet shattered, some arks came down on plates that are
 * still breaking up. A {@link Wreck} has stranded survivors, a number of days before its plate falls, and a round-trip
 * time from the kennel. Only pets whose {@link KennelBond} tier obeys {@code "rescue"} (Devoted) can lead survivors off:
 * {@link #CARRY_PER_TRIP} each per trip, plus {@link #TONIC_BONUS} if the pet carries a bottled tonic that is still T3
 * or better ({@link TonicBottler#tierAt}) on the rescue day. Trips that cannot finish before the fall don't count.
 * Pure and deterministic.
 *
 * <p>Quest "The Last Ark Bell" ({@link #lastArkBell}): save all {@link #KEPLER} survivors before the plate drops.
 */
public final class KennelRescue {
    public static final int CARRY_PER_TRIP = 2;
    public static final int TONIC_BONUS = 1;
    /** The quest wreck: 9 survivors, the plate falls in 4 days, one-day round trips. */
    public static final Wreck KEPLER = new Wreck("Kepler", 9, 4, 1);

    public record Wreck(String name, int survivors, int daysUntilFall, int tripDays) {
        public Wreck {
            if (survivors < 0 || daysUntilFall < 0 || tripDays < 1) {
                throw new IllegalArgumentException("bad wreck");
            }
        }

        /** Seeded wreck: 4-12 survivors, plate falls in 3-8 days, round trip 1-2 days. */
        public static Wreck seeded(String name, long seed) {
            SplittableRandom r = new SplittableRandom(seed);
            return new Wreck(name, 4 + r.nextInt(9), 3 + r.nextInt(6), 1 + r.nextInt(2));
        }
    }

    /** A pet sent on the rescue, with its bond and an optional bottled tonic. */
    public record Rescuer(String name, int bond, Optional<Bottle> tonic) { }

    public record Plan(int trips, int perTrip, int saved, int lost, List<String> crew, List<String> leftHome) {
        public Plan {
            crew = List.copyOf(crew);
            leftHome = List.copyOf(leftHome);
        }

        public boolean allSaved() {
            return lost == 0;
        }
    }

    private KennelRescue() {
    }

    /** Survivors this pet can lead off per trip on {@code day}; 0 unless Devoted. */
    public static int capacity(Rescuer p, int day) {
        if (!KennelBond.obeys(p.bond(), "rescue")) {
            return 0;
        }
        OptionalInt lv = p.tonic().map(b -> TonicBottler.tierAt(b, day)).orElse(OptionalInt.empty());
        return CARRY_PER_TRIP + (lv.isPresent() && lv.getAsInt() >= 3 ? TONIC_BONUS : 0);
    }

    /** Plans a rescue starting on {@code day}. */
    public static Plan plan(Wreck w, List<Rescuer> team, int day) {
        List<String> crew = new ArrayList<>();
        List<String> home = new ArrayList<>();
        int per = 0;
        for (Rescuer p : team) {
            int c = capacity(p, day);
            if (c > 0) {
                crew.add(p.name());
                per += c;
            } else {
                home.add(p.name());
            }
        }
        int trips = w.daysUntilFall() / w.tripDays();
        int saved = Math.min(w.survivors(), trips * per);
        return new Plan(trips, per, saved, w.survivors() - saved, crew, home);
    }

    /** Fewest extra survivors per trip the crew would need to save everyone (0 if they already can). */
    public static int shortfallPerTrip(Wreck w, Plan p) {
        if (p.allSaved()) {
            return 0;
        }
        if (p.trips() == 0) {
            return Integer.MAX_VALUE;
        }
        int need = (w.survivors() + p.trips() - 1) / p.trips();
        return need - p.perTrip();
    }

    /** Quest "The Last Ark Bell": every Kepler survivor saved. */
    public static boolean lastArkBell(List<Rescuer> team, int day) {
        return plan(KEPLER, team, day).allSaved();
    }
}