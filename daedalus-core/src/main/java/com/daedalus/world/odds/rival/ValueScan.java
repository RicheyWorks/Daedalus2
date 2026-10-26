// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.rival;

import com.daedalus.world.odds.ledger.KellyStake;
import java.util.ArrayList;
import java.util.List;

/**
 * Reads two books against the Odds Keeper's fair chances: which lines carry a positive edge ({@code p x odds > 1},
 * via G56 {@link KellyStake#edge}), and whether taking the best price on every outcome across both books locks a
 * profit (an arbitrage: sum of 1 / best odds below 1).
 */
public final class ValueScan {

    private ValueScan() {
    }

    /** One positive-edge line. */
    public record Value(int outcome, double odds, double edge) {
    }

    /** Lines on {@code book} with edge above {@code minEdge}, in outcome order. */
    public static List<Value> values(double[] chances, RivalBook book, double minEdge) {
        double[] p = RivalBook.check(chances);
        if (book.size() != p.length) {
            throw new IllegalArgumentException("book size " + book.size() + " != outcomes " + p.length);
        }
        List<Value> out = new ArrayList<>();
        for (int i = 0; i < p.length; i++) {
            double o = book.odds(i);
            if (o > 0) {
                double e = KellyStake.edge(p[i], o);
                if (e > minEdge) {
                    out.add(new Value(i, o, e));
                }
            }
        }
        return out;
    }

    /** Best price per outcome across books (0 when no book offers it). */
    public static double[] bestPrices(RivalBook a, RivalBook b) {
        if (a.size() != b.size()) {
            throw new IllegalArgumentException("books differ in size");
        }
        double[] best = new double[a.size()];
        for (int i = 0; i < best.length; i++) {
            best[i] = Math.max(a.odds(i), b.odds(i));
        }
        return best;
    }

    /** Sum of 1 / best price; below 1 is an arbitrage. Infinite if any outcome is unpriced. */
    public static double arbSum(RivalBook a, RivalBook b) {
        double s = 0;
        for (double o : bestPrices(a, b)) {
            if (o <= 0) {
                return Double.POSITIVE_INFINITY;
            }
            s += 1 / o;
        }
        return s;
    }

    public static boolean isArb(RivalBook a, RivalBook b) {
        return arbSum(a, b) < 1.0;
    }

    /**
     * Herbs to stake on each outcome at the best price so every result returns the same amount from {@code total}
     * herbs (stake_i = total x (1 / o_i) / arbSum, floored). Empty when there is no arbitrage.
     */
    public static int[] arbStakes(RivalBook a, RivalBook b, int total) {
        if (total < 1) {
            throw new IllegalArgumentException("total must be >= 1: " + total);
        }
        double s = arbSum(a, b);
        if (!(s < 1.0)) {
            return new int[0];
        }
        double[] best = bestPrices(a, b);
        int[] stakes = new int[best.length];
        for (int i = 0; i < best.length; i++) {
            stakes[i] = (int) Math.floor(total / best[i] / s);
        }
        return stakes;
    }
}
