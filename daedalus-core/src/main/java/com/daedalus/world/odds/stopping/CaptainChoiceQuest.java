// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.stopping;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_captain_choice: the last ark needs a captain. {@link #CANDIDATES} sailors are interviewed one at a time and
 * each must be hired or sent away on the spot. The player interviews in order and may hire at any point; the Keeper
 * whispers the look-then-leap rule (pass the first {@code bestCutoff}, then hire the first who beats them all). Hiring
 * the single best sailor wins; the score is shown only relative to those already seen.
 */
public final class CaptainChoiceQuest {

    public static final int CANDIDATES = 10;

    /** Quest stages. */
    public enum Stage { INTERVIEWING, BEST_HIRED, GOOD_HIRED }

    private final CaptainLineup lineup;
    private int seen;
    private int hired = -1;
    private Stage stage = Stage.INTERVIEWING;

    public CaptainChoiceQuest(long seed) {
        this.lineup = CaptainLineup.shuffled(CANDIDATES, new OddsRng(seed));
    }

    public Stage stage() {
        return stage;
    }

    public int seen() {
        return seen;
    }

    /** Interviews the next candidate; returns true if they are the best seen so far. */
    public boolean interview() {
        if (stage != Stage.INTERVIEWING) {
            throw new IllegalStateException("captain already hired: " + stage);
        }
        if (seen >= CANDIDATES) {
            throw new IllegalStateException("no candidates left; hire the last one");
        }
        seen++;
        return isBestSoFar(seen - 1);
    }

    private boolean isBestSoFar(int i) {
        for (int j = 0; j < i; j++) {
            if (lineup.score(j) > lineup.score(i)) {
                return false;
            }
        }
        return true;
    }

    /** Hires the candidate just interviewed. */
    public Stage hire() {
        if (stage != Stage.INTERVIEWING) {
            throw new IllegalStateException("captain already hired: " + stage);
        }
        if (seen == 0) {
            throw new IllegalStateException("interview someone first");
        }
        hired = seen - 1;
        stage = hired == lineup.best() ? Stage.BEST_HIRED : Stage.GOOD_HIRED;
        return stage;
    }

    /** Rank of the hired captain (1 = best), or -1 before hiring. */
    public int hiredRank() {
        return hired < 0 ? -1 : CANDIDATES + 1 - (int) lineup.score(hired);
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        int r = StoppingRule.bestCutoff(CANDIDATES);
        return switch (stage) {
            case INTERVIEWING -> String.format(Locale.ROOT,
                    "Send the first %d away, then take the first who beats them all. %.0f%% that's the best of ten.",
                    r, StoppingRule.success(CANDIDATES, r) * 100);
            case BEST_HIRED -> "The best sailor of the ten. The last ark is in good hands.";
            case GOOD_HIRED -> String.format(Locale.ROOT,
                    "Number %d of ten. A fair hand; the belt will test them.", hiredRank());
        };
    }
}
