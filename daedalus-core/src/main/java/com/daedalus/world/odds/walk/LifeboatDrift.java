// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.walk;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/**
 * A lifeboat between the reef and the harbour with a few biscuit rations. Each watch the crew may drift (shoreward
 * chance {@code p}) or row for one ration (chance {@code p + tilt}, capped at {@link #MAX_ROW_CHANCE}). The table holds
 * the exact best P(harbour) for every (rations, cable) and the plan that reaches it, by value iteration per ration
 * layer (layer 0 is the closed-form drift).
 */
public final class LifeboatDrift {

    public static final int MAX_RATIONS = 30;
    public static final int MAX_HARBOUR = 40;
    public static final double MAX_ROW_CHANCE = 0.99;
    private static final double TOL = 1e-15;
    private static final int MAX_SWEEPS = 2_000_000;
    private static final int MAX_WATCHES = 1_000_000;

    private final int harbour;
    private final double drift;
    private final double row;
    private final int rations;
    private final double[][] value;
    private final boolean[][] rowHere;

    public LifeboatDrift(int harbour, double drift, double tilt, int rations) {
        if (harbour < 2 || harbour > MAX_HARBOUR) {
            throw new IllegalArgumentException("harbour must be in [2, " + MAX_HARBOUR + "]: " + harbour);
        }
        DriftOdds.checkChance(drift);
        if (!(tilt >= 0 && tilt < 1)) {
            throw new IllegalArgumentException("tilt must be in [0, 1): " + tilt);
        }
        if (rations < 0 || rations > MAX_RATIONS) {
            throw new IllegalArgumentException("rations must be in [0, " + MAX_RATIONS + "]: " + rations);
        }
        this.harbour = harbour;
        this.drift = drift;
        this.row = Math.min(MAX_ROW_CHANCE, drift + tilt);
        this.rations = rations;
        this.value = new double[rations + 1][];
        this.rowHere = new boolean[rations + 1][harbour + 1];
        DriftOdds steady = new DriftOdds(harbour, drift);
        value[0] = new double[harbour + 1];
        for (int k = 0; k <= harbour; k++) {
            value[0][k] = steady.harbourChance(k);
        }
        for (int r = 1; r <= rations; r++) {
            fillLayer(r);
        }
    }

    private void fillLayer(int r) {
        double[] prev = value[r - 1];
        double[] v = prev.clone();
        double[] rowValue = new double[harbour + 1];
        for (int k = 1; k < harbour; k++) {
            rowValue[k] = row * prev[k + 1] + (1.0 - row) * prev[k - 1];
        }
        for (int sweep = 0; sweep < MAX_SWEEPS; sweep++) {
            double change = 0;
            for (int k = 1; k < harbour; k++) {
                double best = Math.max(drift * v[k + 1] + (1.0 - drift) * v[k - 1], rowValue[k]);
                change = Math.max(change, Math.abs(best - v[k]));
                v[k] = best;
            }
            if (change < TOL) {
                break;
            }
        }
        for (int k = 1; k < harbour; k++) {
            rowHere[r][k] = rowValue[k] > drift * v[k + 1] + (1.0 - drift) * v[k - 1] + 1e-12;
        }
        value[r] = v;
    }

    public int harbour() {
        return harbour;
    }

    public int rations() {
        return rations;
    }

    /** Shoreward chance while rowing. */
    public double rowChance() {
        return row;
    }

    /** Exact best P(harbour) from {@code cable} with {@code left} rations. */
    public double chance(int cable, int left) {
        check(cable, left);
        return value[left][cable];
    }

    /** Whether the best plan rows this watch at {@code cable} with {@code left} rations. */
    public boolean rows(int cable, int left) {
        check(cable, left);
        return rowHere[left][cable];
    }

    /** The plan for {@code left} rations as a string over cables 0..N: 'R' row, '.' drift. */
    public String plan(int left) {
        check(0, left);
        StringBuilder sb = new StringBuilder(harbour + 1);
        for (int k = 0; k <= harbour; k++) {
            sb.append(rowHere[left][k] ? 'R' : '.');
        }
        return sb.toString();
    }

    /** Sails one seeded voyage on the best plan; true when the boat makes the harbour. */
    public boolean sail(int cable, int left, OddsRng rng) {
        check(cable, left);
        int k = cable;
        int r = left;
        for (int w = 0; w < MAX_WATCHES && k > 0 && k < harbour; w++) {
            double p = drift;
            if (r > 0 && rowHere[r][k]) {
                p = row;
                r--;
            }
            k += rng.chance(p) ? 1 : -1;
        }
        return k >= harbour;
    }

    /** Seeded P(harbour) on the best plan over {@code trials}: {estimate, lo, hi}. */
    public double[] simulate(int cable, int left, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            if (sail(cable, left, OddsRng.forTrial(seed, t))) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }

    private void check(int cable, int left) {
        DriftOdds.checkCable(cable, harbour);
        if (left < 0 || left > rations) {
            throw new IllegalArgumentException("rations left must be in [0, " + rations + "]: " + left);
        }
    }
}
