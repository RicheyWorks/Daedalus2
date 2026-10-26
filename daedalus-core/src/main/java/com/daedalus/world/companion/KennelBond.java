// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * Kennel Isle pet bond meter (contest gap G37). Each pet has a bond from 0 to {@link Rules#max()} that moves once a
 * day from the care it got: fed (G26 {@link KennelPantry} pack order), watered (G17 {@link KennelWaterLoop}), a
 * tonic, and fetch catches (G11 throwables). A day without food or water is a neglect day: no gains, a penalty, and
 * the usual decay. The bond's {@link Tier} decides which commands the pet will take, and a pair must both be at least
 * {@link Tier#FAMILIAR} before a G32 {@link KennelLitter} pairing. Pure and deterministic.
 *
 * <p>Quest "The Keeper's Mark" ({@link #keepersMark}): a stray ark hound starts at {@link Rules#strayStart()} and must
 * reach {@link Tier#LOYAL} within {@link Rules#questDays()} days with no neglect day. Food and water alone are not
 * enough; the keeper has to play and brew too.
 */
public final class KennelBond {
    /** Bond tiers, lowest first, with the commands each one unlocks (cumulative). */
    public enum Tier {
        WARY(0, Set.of()),
        FAMILIAR(25, Set.of("come")),
        LOYAL(50, Set.of("come", "stay", "fetch")),
        DEVOTED(80, Set.of("come", "stay", "fetch", "guard", "rescue"));

        private final int min;
        private final Set<String> commands;

        Tier(int min, Set<String> commands) {
            this.min = min;
            this.commands = commands;
        }

        public int min() {
            return min;
        }

        public Set<String> commands() {
            return Collections.unmodifiableSet(new TreeSet<>(commands));
        }

        public static Tier of(int bond) {
            Tier t = WARY;
            for (Tier x : values()) {
                if (bond >= x.min) {
                    t = x;
                }
            }
            return t;
        }
    }

    public record Rules(int fedGain, int waterGain, int tonicGain, int fetchGainPerCatch, int fetchCap,
                        int neglectPenalty, int dailyDecay, int max, int strayStart, int questDays) {
        public Rules {
            if (fedGain < 0 || waterGain < 0 || tonicGain < 0 || fetchGainPerCatch < 0 || fetchCap < 0
                || neglectPenalty < 0 || dailyDecay < 0 || max < Tier.DEVOTED.min() || strayStart < 0
                || strayStart > max || questDays < 1) {
                throw new IllegalArgumentException("bad kennel bond rules");
            }
        }

        /** Shipped balance: full care is +13 a day, food and water alone only +5. */
        public static Rules defaults() {
            return new Rules(4, 2, 3, 1, 5, 10, 1, 100, 10, 7);
        }
    }

    /** One day's care for one pet. */
    public record Care(boolean fed, boolean watered, boolean tonic, int fetchCatches) {
        public Care {
            if (fetchCatches < 0) {
                throw new IllegalArgumentException("negative catches");
            }
        }

        public boolean neglected() {
            return !fed || !watered;
        }
    }

    public record QuestResult(boolean complete, int dayReached, List<Integer> trail, String failReason) {
        public QuestResult {
            trail = List.copyOf(trail);
        }
    }

    private KennelBond() {
    }

    /** The bond after one day of care. */
    public static int step(int bond, Care c, Rules r) {
        int next;
        if (c.neglected()) {
            next = bond - r.neglectPenalty() - r.dailyDecay();
        } else {
            next = bond + r.fedGain() + r.waterGain() + (c.tonic() ? r.tonicGain() : 0)
                + Math.min(c.fetchCatches(), r.fetchCap()) * r.fetchGainPerCatch() - r.dailyDecay();
        }
        return Math.max(0, Math.min(r.max(), next));
    }

    /** Runs several days; returns the bond after each day (first element is the start). */
    public static List<Integer> run(int start, List<Care> days, Rules r) {
        List<Integer> trail = new ArrayList<>();
        int b = Math.max(0, Math.min(r.max(), start));
        trail.add(b);
        for (Care c : days) {
            b = step(b, c, r);
            trail.add(b);
        }
        return trail;
    }

    public static boolean obeys(int bond, String command) {
        return Tier.of(bond).commands().contains(command);
    }

    /** G32 tie-in: both pets must be at least Familiar before they will pair. */
    public static boolean pairReady(int bondA, int bondB) {
        return Tier.of(bondA).compareTo(Tier.FAMILIAR) >= 0 && Tier.of(bondB).compareTo(Tier.FAMILIAR) >= 0;
    }

    /**
     * G26/G17 adapter: a pet counts as fed if the pantry served it in pack order and it is not on the hungry list.
     */
    public static Care careFromPantry(KennelPantry.DayReport day, String pet, boolean watered, boolean tonic,
                                      int fetchCatches) {
        boolean fed = day.fedOrder().contains(pet) && !day.hungry().contains(pet);
        return new Care(fed, watered, tonic, fetchCatches);
    }

    /** Quest "The Keeper's Mark": reach Loyal from the stray start within the quest days, never neglecting. */
    public static QuestResult keepersMark(List<Care> days, Rules r) {
        List<Integer> trail = new ArrayList<>();
        int b = r.strayStart();
        trail.add(b);
        for (int d = 0; d < Math.min(days.size(), r.questDays()); d++) {
            Care c = days.get(d);
            if (c.neglected()) {
                trail.add(step(b, c, r));
                return new QuestResult(false, -1, trail, "neglect on day " + (d + 1));
            }
            b = step(b, c, r);
            trail.add(b);
            if (Tier.of(b).compareTo(Tier.LOYAL) >= 0) {
                return new QuestResult(true, d + 1, trail, null);
            }
        }
        return new QuestResult(false, -1, trail, "not loyal after " + r.questDays() + " days");
    }
}