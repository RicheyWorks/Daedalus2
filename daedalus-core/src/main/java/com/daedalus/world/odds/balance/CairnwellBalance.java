// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.List;

/**
 * Cairnwell (DaedalusDesktopCairnwellCore.h, branch cursor/cairnwell-20261026 commit 5420cb03) re-played tick by
 * tick. Source constants: option 0 (mapped to "normal") is 6 columns, 8 rows, auto-drop every 16 ticks; option 1
 * (the practice well, mapped to "easy") is 4 columns, 6 rows, every 28 ticks. The source ships no third option, so
 * "hard" is reported as missing. Stones spawn in column (seed + locks) mod cols; a full layer sinks; a stone that
 * would spawn on a full column loses. Score is locks x 10 + layers x 100.
 *
 * <p>The game is endless, so a session counts as won when {@code targetLayers} layers sink before the well fills.
 * Player model: waits {@code reactTicks} ticks, then slides one column per two ticks (press, release) toward the lowest
 * column (nearest on ties) and lets the stone auto-drop; with probability {@code slip} per stone it aims at a uniformly
 * random column instead.
 */
public final class CairnwellBalance implements BalanceGame {

    static final List<String> NAMES = List.of("easy", "normal", "hard");
    /** {cols, rows, dropEvery} for "easy" (option 1) and "normal" (option 0). */
    private static final int[][] CONFIG = {{4, 6, 28}, {6, 8, 16}};
    static final int LOCK_POINTS = 10;
    static final int LAYER_POINTS = 100;

    private final int targetLayers;
    private final int reactTicks;
    private final double slip;

    public CairnwellBalance() {
        this(20, 6, 0.25);
    }

    public CairnwellBalance(int targetLayers, int reactTicks, double slip) {
        if (targetLayers < 1 || reactTicks < 0) {
            throw new IllegalArgumentException("targetLayers >= 1 and reactTicks >= 0 required");
        }
        this.targetLayers = targetLayers;
        this.reactTicks = reactTicks;
        this.slip = slip;
    }

    @Override
    public String id() {
        return "cairnwell";
    }

    @Override
    public List<String> difficulties() {
        return NAMES;
    }

    @Override
    public boolean supports(String difficulty) {
        return "easy".equals(difficulty) || "normal".equals(difficulty);
    }

    @Override
    public SessionOutcome play(String difficulty, OddsRng rng) {
        if (!supports(difficulty)) {
            throw new IllegalArgumentException("Cairnwell ships no '" + difficulty + "' well");
        }
        int[] cfg = CONFIG["easy".equals(difficulty) ? 0 : 1];
        int cols = cfg[0];
        int rows = cfg[1];
        int dropEvery = cfg[2];
        long seed = (rng.nextLong() >>> 32);
        seed = seed == 0 ? 1 : seed;
        int[] height = new int[cols];
        int locks = 0;
        int clears = 0;
        int col = (int) (seed % cols);
        while (clears < targetLayers) {
            int target = rng.chance(slip) ? ShardringBalance.pick(rng, cols) : lowest(height, col);
            for (int tick = 1; tick <= dropEvery; tick++) {
                boolean pressTick = tick > reactTicks && (tick - reactTicks) % 2 == 1;
                if (pressTick && col != target) {
                    int nextCol = col + Integer.signum(target - col);
                    if (height[nextCol] < rows) {
                        col = nextCol;
                    }
                }
            }
            height[col]++;
            locks++;
            int layers = rows;
            for (int h : height) {
                layers = Math.min(layers, h);
            }
            if (layers > 0) {
                for (int c = 0; c < cols; c++) {
                    height[c] -= layers;
                }
                clears += layers;
            }
            col = (int) ((seed + locks) % cols);
            if (height[col] >= rows) {
                return new SessionOutcome(false, score(locks, clears));
            }
        }
        return new SessionOutcome(true, score(locks, clears));
    }

    private static long score(int locks, int clears) {
        return (long) locks * LOCK_POINTS + (long) clears * LAYER_POINTS;
    }

    static int lowest(int[] height, int from) {
        int best = from;
        for (int c = 0; c < height.length; c++) {
            boolean lower = height[c] < height[best];
            boolean tieCloser = height[c] == height[best] && Math.abs(c - from) < Math.abs(best - from);
            if (lower || tieCloser) {
                best = c;
            }
        }
        return best;
    }
}
