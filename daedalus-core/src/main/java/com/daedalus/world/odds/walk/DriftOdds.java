// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.walk;

/**
 * Gambler's-ruin odds for a boat drifting one cable a watch on a line between the reef (0) and the harbour ({@code
 * harbour}). Each watch it moves shoreward with chance {@code p}, else reefward. Closed forms for a steady wind plus
 * exact solvers for a chance that changes with position.
 */
public final class DriftOdds {

    public static final int MAX_HARBOUR = 200;

    private final int harbour;
    private final double shoreward;

    public DriftOdds(int harbour, double shoreward) {
        checkHarbour(harbour);
        checkChance(shoreward);
        this.harbour = harbour;
        this.shoreward = shoreward;
    }

    public int harbour() {
        return harbour;
    }

    public double shoreward() {
        return shoreward;
    }

    /** P(reach the harbour before the reef) from {@code cable}: (1 - (q/p)^k) / (1 - (q/p)^N), k/N when fair. */
    public double harbourChance(int cable) {
        checkCable(cable, harbour);
        double q = 1.0 - shoreward;
        if (Math.abs(shoreward - q) < 1e-12) {
            return cable / (double) harbour;
        }
        double r = q / shoreward;
        return (1.0 - Math.pow(r, cable)) / (1.0 - Math.pow(r, harbour));
    }

    /** Expected watches until harbour or reef from {@code cable}: k(N - k) when fair, else the ruin-duration form. */
    public double expectedWatches(int cable) {
        checkCable(cable, harbour);
        double q = 1.0 - shoreward;
        if (Math.abs(shoreward - q) < 1e-12) {
            return cable * (double) (harbour - cable);
        }
        return cable / (q - shoreward) - harbour / (q - shoreward) * harbourChance(cable);
    }

    /**
     * Exact P(harbour) from every cable when the shoreward chance is {@code up[k]} at cable k (entries 0 and N are
     * ignored). Uses the step-ratio product, so it is exact up to rounding.
     */
    public static double[] harbourChancesAt(double[] up) {
        int n = checkUp(up);
        double[] gap = new double[n];
        gap[0] = 1.0;
        double total = 1.0;
        for (int k = 1; k < n; k++) {
            gap[k] = gap[k - 1] * (1.0 - up[k]) / up[k];
            total += gap[k];
        }
        double[] v = new double[n + 1];
        for (int k = 1; k <= n; k++) {
            v[k] = v[k - 1] + gap[k - 1] / total;
        }
        v[n] = 1.0;
        return v;
    }

    /** Exact expected watches to the end from every cable with position-dependent shoreward chance {@code up}. */
    public static double[] expectedWatchesAt(double[] up) {
        int n = checkUp(up);
        int m = n - 1;
        double[] lower = new double[m];
        double[] diag = new double[m];
        double[] upper = new double[m];
        double[] rhs = new double[m];
        for (int i = 0; i < m; i++) {
            int k = i + 1;
            lower[i] = -(1.0 - up[k]);
            diag[i] = 1.0;
            upper[i] = -up[k];
            rhs[i] = 1.0;
        }
        double[] inner = Tridiagonal.solve(lower, diag, upper, rhs);
        double[] t = new double[n + 1];
        System.arraycopy(inner, 0, t, 1, m);
        return t;
    }

    static void checkHarbour(int harbour) {
        if (harbour < 2 || harbour > MAX_HARBOUR) {
            throw new IllegalArgumentException("harbour must be in [2, " + MAX_HARBOUR + "]: " + harbour);
        }
    }

    static void checkChance(double p) {
        if (!(p > 0 && p < 1)) {
            throw new IllegalArgumentException("chance must be in (0, 1): " + p);
        }
    }

    static void checkCable(int cable, int harbour) {
        if (cable < 0 || cable > harbour) {
            throw new IllegalArgumentException("cable must be in [0, " + harbour + "]: " + cable);
        }
    }

    private static int checkUp(double[] up) {
        if (up == null) {
            throw new IllegalArgumentException("up must not be null");
        }
        int n = up.length - 1;
        checkHarbour(n);
        for (int k = 1; k < n; k++) {
            checkChance(up[k]);
        }
        return n;
    }
}
