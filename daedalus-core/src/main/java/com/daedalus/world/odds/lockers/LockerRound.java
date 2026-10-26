// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.lockers;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/** One seeded locker round: prize placed, lockers opened by the Keeper or the blind deckhand, stay or switch. */
public final class LockerRound {

    /** Who opens the lockers. */
    public enum Opener { KEEPER, DECKHAND }

    /** How a round ends. */
    public enum Outcome { FOUND, MISSED, VOID }

    private final int lockers;
    private final int pick;
    private final int prize;
    private final boolean[] open;
    private final boolean voided;

    private LockerRound(int lockers, int pick, int prize, boolean[] open, boolean voided) {
        this.lockers = lockers;
        this.pick = pick;
        this.prize = prize;
        this.open = open;
        this.voided = voided;
    }

    /** Places the prize, then {@code opener} opens {@code opened} lockers other than {@code pick}. */
    public static LockerRound deal(LockerOdds odds, int pick, Opener opener, OddsRng rng) {
        int n = odds.lockers();
        if (pick < 0 || pick >= n) {
            throw new IllegalArgumentException("pick must be in [0, " + (n - 1) + "]: " + pick);
        }
        int prize = index(rng, n);
        int[] pool = new int[n];
        int size = 0;
        for (int i = 0; i < n; i++) {
            if (i != pick && !(opener == Opener.KEEPER && i == prize)) {
                pool[size++] = i;
            }
        }
        boolean[] open = new boolean[n];
        boolean voided = false;
        for (int j = 0; j < odds.opened(); j++) {
            int r = j + index(rng, size - j);
            int chosen = pool[r];
            pool[r] = pool[j];
            pool[j] = chosen;
            open[chosen] = true;
            voided |= chosen == prize;
        }
        return new LockerRound(n, pick, prize, open, voided);
    }

    /** Whether the opener showed the prize (blind deckhand only). */
    public boolean voided() {
        return voided;
    }

    /** Whether locker {@code i} is open. */
    public boolean isOpen(int i) {
        return open[i];
    }

    /** Resolves the round: stay on the pick or switch to a random other closed locker on {@code rng}. */
    public Outcome resolve(boolean switchPick, OddsRng rng) {
        if (voided) {
            return Outcome.VOID;
        }
        int choice = pick;
        if (switchPick) {
            int[] closed = new int[lockers];
            int size = 0;
            for (int i = 0; i < lockers; i++) {
                if (i != pick && !open[i]) {
                    closed[size++] = i;
                }
            }
            choice = closed[index(rng, size)];
        }
        return choice == prize ? Outcome.FOUND : Outcome.MISSED;
    }

    /** Seeded P(found | round not void) over {@code trials}: {estimate, lo, hi, voidRate}. */
    public static double[] simulate(LockerOdds odds, Opener opener, boolean switchPick, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int found = 0;
        int kept = 0;
        for (int t = 0; t < trials; t++) {
            OddsRng rng = OddsRng.forTrial(seed, t);
            Outcome o = deal(odds, 0, opener, rng).resolve(switchPick, rng);
            if (o != Outcome.VOID) {
                kept++;
                if (o == Outcome.FOUND) {
                    found++;
                }
            }
        }
        double[] ci = kept == 0 ? new double[] {0, 1} : Intervals.wilson(found, kept);
        double est = kept == 0 ? 0 : found / (double) kept;
        return new double[] {est, ci[0], ci[1], (trials - kept) / (double) trials};
    }

    private static int index(OddsRng rng, int bound) {
        return Math.min(bound - 1, (int) Math.floor(rng.nextDouble() * bound));
    }
}
