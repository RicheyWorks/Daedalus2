// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tote;

import com.daedalus.world.odds.OddsRng;

/**
 * Fills a tote with the island crowd's bets. Each bettor starts from the Keeper's chalked chances and skews each one by
 * a seeded factor {@code exp(u)}, {@code u} uniform in [-spread, spread] (hunches, favourite bias), then backs one
 * outcome drawn from those skewed weights. Pure in (chances, crowd, herbs, spread, seed).
 */
public final class CrowdBets {

    private CrowdBets() {
    }

    public static void fill(ToteBoard board, double[] chances, int crowd, int herbsEach, double spread, long seed) {
        if (chances.length != board.size()) {
            throw new IllegalArgumentException("chances size " + chances.length + " != board " + board.size());
        }
        if (crowd < 1 || herbsEach < 1 || !(spread >= 0)) {
            throw new IllegalArgumentException("crowd and herbsEach must be >= 1 and spread >= 0");
        }
        OddsRng rng = new OddsRng(seed);
        double[] w = new double[chances.length];
        for (int b = 0; b < crowd; b++) {
            double sum = 0;
            for (int i = 0; i < w.length; i++) {
                w[i] = Math.max(0, chances[i]) * Math.exp((rng.nextDouble() * 2 - 1) * spread);
                sum += w[i];
            }
            if (sum <= 0) {
                throw new IllegalArgumentException("chances must have positive mass");
            }
            double u = rng.nextDouble() * sum;
            int pick = w.length - 1;
            for (int i = 0; i < w.length; i++) {
                u -= w[i];
                if (u < 0) {
                    pick = i;
                    break;
                }
            }
            board.bet(pick, herbsEach);
        }
    }
}
