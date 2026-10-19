// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Voyage;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Void Crossing (contest gap G152): sail a launched ark through the cold void to its shard, one day at a time. This
 * is the end of ISLAND.md beat 6 ("leave on an ark that remembers this forge") and the far side of the G24
 * {@link ArkDrydock} inspection. The quench-tub rule ("temper both, or the ark dies in the void") is now tested.
 *
 * <p>The crossing is seeded. On about every other day a void storm strikes one seam for 15 to 40 strength, and on
 * about one day in five a cold snap sets in. Each day the crew may patch one seam with a spare rivet, which restores
 * {@value ArkDrydock#MISSING_RIVET_COST} strength up to the seam's launch strength. On a cold-snap day the crew can
 * only work if they drank the Void Crossing tonic ({@code dual_void_crossing}: cold_resist + slow_hunger), and without
 * it they drink double that day. The tonic also cuts the crew's own water by a quarter. The hold pays the day's water (crew plus manifest, the G24 rates). On
 * a day it runs dry, one head of the thirstiest kind aboard is lost. If any seam ends a day below {@value #BREACH},
 * the hull breaches and the ark limps home.
 *
 * <p>The host owns the {@link Crossing}. The storms and snaps are fixed by the seed when the crossing begins, so the
 * crew's orders never change the weather. {@link #bosun} is the reference crew.
 */
public final class VoidCrossing {

    /** Below this a seam breaches. */
    public static final int BREACH = 30;
    /** Spare rivets an ark may carry in the rivet crate. */
    public static final int MAX_SPARES = 12;

    /** How the crossing ended. */
    public enum Outcome { SAILING, ARRIVED, ARRIVED_WITH_LOSSES, BREACHED, NOT_LAUNCHED }

    /** One day's weather, fixed at departure. {@code stormSeam} is -1 on a calm day. */
    public record Day(boolean cold, int stormSeam, int damage) {
    }

    /** One ark's crossing, held by the host. */
    public static final class Crossing {

        private final Ark ark;
        private final Voyage voyage;
        private final boolean tonic;
        private final List<Day> weather;
        private final int[] launch;
        private final int[] seam;
        private final Map<Life, Integer> aboard = new EnumMap<>(Life.class);
        private final Map<Life, Integer> lost = new EnumMap<>(Life.class);
        private int spares;
        private int water;
        private int day;
        private int patches;
        private int idleDays;
        private Outcome outcome;

        Crossing(Ark ark, Voyage voyage, boolean tonic, int spares, long seed) {
            if (spares < 0 || spares > MAX_SPARES) {
                throw new IllegalArgumentException("spare rivets 0.." + MAX_SPARES + ", not " + spares);
            }
            this.ark = ark;
            this.voyage = voyage;
            this.tonic = tonic;
            this.spares = spares;
            this.water = ark.waterDl();
            int n = ark.plates().size();
            launch = new int[n];
            for (int i = 0; i < n; i++) {
                launch[i] = ArkDrydock.seamStrength(ark, i);
            }
            seam = launch.clone();
            aboard.putAll(ark.manifest());
            SplittableRandom rng = new SplittableRandom(seed ^ 0x701DL);
            List<Day> w = new ArrayList<>(voyage.days());
            for (int d = 0; d < voyage.days(); d++) {
                boolean cold = rng.nextInt(5) == 0;
                boolean storm = rng.nextInt(2) == 0;
                int s = rng.nextInt(Math.max(1, n));
                int dmg = 15 + rng.nextInt(26);
                w.add(storm && n > 0 ? new Day(cold, s, dmg) : new Day(cold, -1, 0));
            }
            weather = List.copyOf(w);
            outcome = ArkDrydock.inspect(ark, voyage).ready() ? Outcome.SAILING : Outcome.NOT_LAUNCHED;
        }

        /** Today's weather, which the crew sees before giving the order (null once the crossing is over). */
        public Day today() {
            return outcome == Outcome.SAILING ? weather.get(day) : null;
        }

        /** Sail one day. {@code patchSeam} is the seam to patch, or -1 to hold. Returns the outcome so far. */
        public Outcome sail(int patchSeam) {
            if (outcome != Outcome.SAILING) {
                return outcome;
            }
            Day w = weather.get(day);
            boolean canWork = !w.cold() || tonic;
            if (!canWork) {
                idleDays++;
            } else if (patchSeam >= 0 && patchSeam < seam.length && spares > 0 && seam[patchSeam] < launch[patchSeam]) {
                spares--;
                patches++;
                seam[patchSeam] = Math.min(launch[patchSeam], seam[patchSeam] + ArkDrydock.MISSING_RIVET_COST);
            }
            if (w.stormSeam() >= 0) {
                seam[w.stormSeam()] = Math.max(0, seam[w.stormSeam()] - w.damage());
            }
            int need = needToday(w.cold());
            if (water >= need) {
                water -= need;
            } else {
                water = 0;
                loseThirstiest();
            }
            day++;
            if (minSeam() < BREACH) {
                outcome = Outcome.BREACHED;
            } else if (day == voyage.days()) {
                outcome = lost.isEmpty() ? Outcome.ARRIVED : Outcome.ARRIVED_WITH_LOSSES;
            }
            return outcome;
        }

        /** Water the ark drinks today: the crew (a quarter less on the tonic, double in the cold without it) plus everything aboard. */
        int needToday(boolean cold) {
            int crew = ark.arkClass().crew() * ArkDrydock.CREW_DL;
            int need = tonic ? crew * 3 / 4 : cold ? crew * 2 : crew;
            for (Map.Entry<Life, Integer> e : aboard.entrySet()) {
                need += e.getKey().dlPerDay() * e.getValue();
            }
            return need;
        }

        private void loseThirstiest() {
            Life worst = null;
            for (Map.Entry<Life, Integer> e : aboard.entrySet()) {
                if (e.getValue() > 0 && e.getKey().dlPerDay() > 0 && (worst == null || e.getKey().dlPerDay() > worst.dlPerDay())) {
                    worst = e.getKey();
                }
            }
            if (worst != null) {
                aboard.merge(worst, -1, Integer::sum);
                lost.merge(worst, 1, Integer::sum);
            }
        }

        public int minSeam() {
            int m = Integer.MAX_VALUE;
            for (int s : seam) {
                m = Math.min(m, s);
            }
            return seam.length == 0 ? 0 : m;
        }

        /** The weakest seam that is below its launch strength, or -1. */
        public int weakestPatchable() {
            int best = -1;
            for (int i = 0; i < seam.length; i++) {
                if (seam[i] < launch[i] && (best < 0 || seam[i] < seam[best])) {
                    best = i;
                }
            }
            return best;
        }

        public int seam(int i) {
            return seam[i];
        }

        public Outcome outcome() {
            return outcome;
        }

        public int day() {
            return day;
        }

        public int water() {
            return water;
        }

        public int spares() {
            return spares;
        }

        public int patches() {
            return patches;
        }

        public int idleDays() {
            return idleDays;
        }

        public List<Day> weather() {
            return weather;
        }

        public Map<Life, Integer> lost() {
            return Map.copyOf(lost);
        }

        public int lostHead() {
            int n = 0;
            for (int v : lost.values()) {
                n += v;
            }
            return n;
        }

        /** Captain Mira Sootvane's log line for where the crossing stands. */
        public String line() {
            return VoidCrossing.line(outcome, voyage);
        }

        /** One-line VXC 1 summary of the crossing so far. */
        public String encode() {
            int storms = 0;
            int colds = 0;
            for (Day w : weather) {
                storms += w.stormSeam() >= 0 ? 1 : 0;
                colds += w.cold() ? 1 : 0;
            }
            return "VXC 1 " + outcome + " to=" + voyage.shard().replace(' ', '_') + " day=" + day + "/" + voyage.days() + " storms="
                    + storms + " cold=" + colds + " minSeam=" + minSeam() + " patches=" + patches + " spares=" + spares + " idle="
                    + idleDays + " water=" + water + " lost=" + lostHead() + " | " + line();
        }
    }

    private VoidCrossing() {
    }

    /** Cast off: {@code ark} for {@code voyage}, with or without the tonic, carrying {@code spares} rivets. */
    public static Crossing depart(Ark ark, Voyage voyage, boolean tonic, int spares, long seed) {
        return new Crossing(ark, voyage, tonic, spares, seed);
    }

    /** The reference crew: every working day, patch the weakest seam that has taken damage. */
    public static Crossing bosun(Ark ark, Voyage voyage, boolean tonic, int spares, long seed) {
        Crossing c = depart(ark, voyage, tonic, spares, seed);
        while (c.outcome() == Outcome.SAILING) {
            c.sail(c.weakestPatchable());
        }
        return c;
    }

    static String line(Outcome o, Voyage v) {
        return switch (o) {
            case SAILING -> "Holding course for " + v.shard() + ". Keep a hand on the rivet crate.";
            case ARRIVED -> "Moored at " + v.shard() + ", every head aboard. She remembers the forge.";
            case ARRIVED_WITH_LOSSES -> "We made " + v.shard() + ", but the hold ran dry. Load more water next time.";
            case BREACHED -> "Seam's open to the void. We're limping home. Temper both, smith.";
            case NOT_LAUNCHED -> "Brannoc never cleared her off the slip. Fix the hull first.";
        };
    }
}
