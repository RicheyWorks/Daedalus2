// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.benford;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_cooked_ledger: the Keeper lays out {@link #LEDGERS} ark cargo ledgers of {@link #ENTRIES} entries. One was
 * cooked by a clerk who made the numbers up. Read the first digits (the Keeper shows the Benford chi-square of each)
 * and point at the cooked one. No wagering.
 */
public final class CookedLedgerQuest {

    public static final int LEDGERS = 3;
    public static final int ENTRIES = 200;

    /** Quest stages. */
    public enum Stage { AUDITING, CAUGHT, FOOLED }

    private final int cookedIndex;
    private final int[][] counts = new int[LEDGERS][];
    private Stage stage = Stage.AUDITING;
    private int pointed = -1;

    public CookedLedgerQuest(long seed) {
        OddsRng rng = new OddsRng(seed);
        cookedIndex = Math.min(LEDGERS - 1, (int) Math.floor(rng.nextDouble() * LEDGERS));
        for (int i = 0; i < LEDGERS; i++) {
            double[] v = i == cookedIndex ? CargoLedger.cooked(ENTRIES, rng) : CargoLedger.honest(ENTRIES, rng);
            counts[i] = BenfordLaw.digitCounts(v);
        }
    }

    public Stage stage() {
        return stage;
    }

    /** First-digit counts of ledger {@code i} (a copy; index 0 unused). */
    public int[] counts(int i) {
        checkLedger(i);
        return counts[i].clone();
    }

    /** Benford chi-square of ledger {@code i}. */
    public double chiSquare(int i) {
        checkLedger(i);
        return BenfordLaw.chiSquare(counts[i]);
    }

    /** The ledger with the worst Benford fit (the Keeper's hint). */
    public int worstFit() {
        int worst = 0;
        for (int i = 1; i < LEDGERS; i++) {
            if (chiSquare(i) > chiSquare(worst)) {
                worst = i;
            }
        }
        return worst;
    }

    /** Points at ledger {@code i}; returns the final stage. */
    public Stage point(int i) {
        if (stage != Stage.AUDITING) {
            throw new IllegalStateException("already pointed");
        }
        checkLedger(i);
        pointed = i;
        stage = i == cookedIndex ? Stage.CAUGHT : Stage.FOOLED;
        return stage;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case AUDITING -> String.format(Locale.ROOT,
                    "Honest cargo starts with a 1 three times in ten. Chi-square: %.1f, %.1f, %.1f (over %.1f is"
                            + " a lie one time in twenty). Which ledger was cooked?",
                    chiSquare(0), chiSquare(1), chiSquare(2), BenfordLaw.CRITICAL_5PCT);
            case CAUGHT -> String.format(Locale.ROOT, "Ledger %d, %d ones in %d. Cooked, and caught.", pointed + 1,
                    counts[pointed][1], ENTRIES);
            case FOOLED -> String.format(Locale.ROOT, "Ledger %d is honest. The cooked one was %d (%d ones in %d).",
                    pointed + 1, cookedIndex + 1, counts[cookedIndex][1], ENTRIES);
        };
    }

    private static void checkLedger(int i) {
        if (i < 0 || i >= LEDGERS) {
            throw new IllegalArgumentException("ledger must be in [0, " + (LEDGERS - 1) + "]: " + i);
        }
    }
}
