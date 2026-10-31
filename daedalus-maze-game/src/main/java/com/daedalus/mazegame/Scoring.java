// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

/**
 * Pure scoring rules. Par time allows {@link #MILLIS_PER_PAR_MOVE} per optimal move.
 * Three stars: at or under par moves and par time with no hints. Two stars: within 150% of par
 * moves. One star: any finish. Score = 1000 * par / moves, minus time overrun and hint costs.
 */
public final class Scoring {

    public static final long MILLIS_PER_PAR_MOVE = 400L;
    public static final int HINT_COST = 100;

    private Scoring() {
    }

    public static long parMillis(int par) {
        return par * MILLIS_PER_PAR_MOVE;
    }

    public static int stars(int par, int moves, long millis, int hints) {
        if (moves <= par && millis <= parMillis(par) && hints == 0) {
            return 3;
        }
        if (moves * 2L <= par * 3L) {
            return 2;
        }
        return 1;
    }

    public static int score(int par, int moves, long millis, int hints) {
        if (moves <= 0) {
            return 0;
        }
        long base = 1000L * par / moves;
        long overrunSeconds = Math.max(0L, millis - parMillis(par)) / 1000L;
        long s = base - overrunSeconds - (long) HINT_COST * hints;
        return (int) Math.max(0L, s);
    }
}
