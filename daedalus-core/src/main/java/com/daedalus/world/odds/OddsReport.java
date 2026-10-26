// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import java.util.Locale;

/**
 * The answer: win probability with a 95% Wilson interval, the time-to-kill distribution of wins, the time-to-die
 * distribution of losses, how much health the player loses (mean, variance), and the expected value per encounter with
 * its own 95% interval. A pure function of (encounter, seed, trials, payoffs).
 */
public record OddsReport(long seed, int trials, int wins, int losses, int draws, double pWin, double pWinLow,
                         double pWinHigh, Summary winTtk, Summary lossTtd, Summary healthLost,
                         double meanHealthLostFraction, double meanFoesDowned, double expectedValue,
                         double expectedValueLow, double expectedValueHigh) {

    public double pLoss() {
        return trials == 0 ? 0 : (double) losses / trials;
    }

    public double pDraw() {
        return trials == 0 ? 0 : (double) draws / trials;
    }

    /** Width of the 95% interval on the win probability: the smaller, the more trials you can trust. */
    public double pWinWidth() {
        return pWinHigh - pWinLow;
    }

    /** DOR 1: the single-line encoding for the team link and golden tests. */
    public String encode() {
        return String.format(Locale.ROOT,
                "DOR 1 seed=%d trials=%d win=%d loss=%d draw=%d pwin=%.4f ci95=[%.4f,%.4f] ttk{%s} ttd{%s} hp{%s} "
                        + "hpfrac=%.4f downed=%.3f ev=%.4f ev95=[%.4f,%.4f]",
                seed, trials, wins, losses, draws, pWin, pWinLow, pWinHigh, winTtk.encode(), lossTtd.encode(),
                healthLost.encode(), meanHealthLostFraction, meanFoesDowned, expectedValue, expectedValueLow,
                expectedValueHigh);
    }
}