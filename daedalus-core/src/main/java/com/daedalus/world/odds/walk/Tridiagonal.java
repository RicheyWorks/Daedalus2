// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.walk;

/** Thomas-algorithm solver for diagonally dominant tridiagonal systems (absorbing walks on a line). */
final class Tridiagonal {

    private Tridiagonal() {
    }

    /** Solves lower[i] x[i-1] + diag[i] x[i] + upper[i] x[i+1] = rhs[i]; lower[0] and upper[n-1] are ignored. */
    static double[] solve(double[] lower, double[] diag, double[] upper, double[] rhs) {
        int n = diag.length;
        double[] c = new double[n];
        double[] d = new double[n];
        double den = diag[0];
        c[0] = n > 1 ? upper[0] / den : 0.0;
        d[0] = rhs[0] / den;
        for (int i = 1; i < n; i++) {
            den = diag[i] - lower[i] * c[i - 1];
            c[i] = i < n - 1 ? upper[i] / den : 0.0;
            d[i] = (rhs[i] - lower[i] * d[i - 1]) / den;
        }
        double[] x = new double[n];
        x[n - 1] = d[n - 1];
        for (int i = n - 2; i >= 0; i--) {
            x[i] = d[i] - c[i] * x[i + 1];
        }
        return x;
    }
}
