// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import java.util.Arrays;
import java.util.Locale;

/**
 * The tuner's answer for one difficulty: shipped knob values (null if the mode is missing), the suggested values
 * (null if no grid point qualified), and the confirming run behind the suggestion.
 */
public record Suggestion(String game, String difficulty, int[] shipped, int[] suggested, ModeResult confirm,
        int candidatesInBand) {

    public Suggestion {
        shipped = shipped == null ? null : shipped.clone();
        suggested = suggested == null ? null : suggested.clone();
    }

    public boolean found() {
        return suggested != null;
    }

    @Override
    public int[] shipped() {
        return shipped == null ? null : shipped.clone();
    }

    @Override
    public int[] suggested() {
        return suggested == null ? null : suggested.clone();
    }

    @Override
    public String toString() {
        String ship = shipped == null ? "missing" : Arrays.toString(shipped);
        if (!found()) {
            return String.format(Locale.ROOT, "%s/%s: shipped %s -> no in-band setting (%d grid points in band)", game,
                    difficulty, ship, candidatesInBand);
        }
        return String.format(Locale.ROOT, "%s/%s: shipped %s -> suggest %s win %.1f%% [%.1f, %.1f] n=%d (%d in band)",
                game, difficulty, ship, Arrays.toString(suggested), 100 * confirm.winRate(), 100 * confirm.low(),
                100 * confirm.high(), confirm.trials(), candidatesInBand);
    }
}
