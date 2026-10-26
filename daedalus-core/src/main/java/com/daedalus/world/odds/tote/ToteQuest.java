// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tote;

import com.daedalus.world.odds.OddsRng;
import java.util.Arrays;
import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_keepers_tote: on Squall Cup day (G35) the Keeper runs a tote instead of fixed odds. The crowd bets first;
 * the player then backs one outcome. The Keeper approves only an overlay (fair chance x tote odds after your stake
 * above 1, judged by his chalk). The race is then decided by the fair chances on a fresh seeded stream. Herbs are
 * in-game only.
 */
public final class ToteQuest {

    public static final double TAKEOUT = 0.15;
    public static final int CROWD = 40;
    public static final int CROWD_HERBS = 5;
    public static final double CROWD_SPREAD = 0.8;

    /** Quest stages. */
    public enum Stage { BOARD_OPEN, BACKED, WON, LOST }

    private final double[] chances;
    private final ToteBoard board;
    private Stage stage = Stage.BOARD_OPEN;
    private int backed = -1;
    private long stake;
    private boolean overlay;
    private int winner = -1;
    private long paid;

    public ToteQuest(double[] chances, long seed) {
        Objects.requireNonNull(chances, "chances");
        this.chances = Arrays.copyOf(chances, chances.length);
        this.board = new ToteBoard(chances.length, TAKEOUT);
        CrowdBets.fill(board, this.chances, CROWD, CROWD_HERBS, CROWD_SPREAD, seed);
    }

    public Stage stage() {
        return stage;
    }

    public long pool() {
        return board.pool();
    }

    public double odds(int i) {
        return board.odds(i);
    }

    public long maxOverlayStake(int i) {
        return board.maxOverlayStake(i, chances[i]);
    }

    /** Best overlay by edge at a 1-herb stake, or -1 if the crowd left none. */
    public int bestOverlay() {
        int best = -1;
        double bestEdge = 0;
        for (int i = 0; i < chances.length; i++) {
            double e = chances[i] * board.oddsAfter(i, 1) - 1;
            if (e > bestEdge) {
                bestEdge = e;
                best = i;
            }
        }
        return best;
    }

    /** Backs outcome {@code i} with {@code herbs}; returns whether the Keeper judges it an overlay. */
    public boolean back(int i, long herbs) {
        if (stage != Stage.BOARD_OPEN) {
            throw new IllegalStateException("already backed: " + stage);
        }
        Objects.checkIndex(i, chances.length);
        overlay = chances[i] * board.oddsAfter(i, herbs) > 1;
        board.bet(i, herbs);
        backed = i;
        stake = herbs;
        stage = Stage.BACKED;
        return overlay;
    }

    public boolean overlay() {
        return overlay;
    }

    /** Runs the race once from the fair chances; returns herbs paid. */
    public long race(long raceSeed) {
        if (stage != Stage.BACKED) {
            throw new IllegalStateException("back an outcome first: " + stage);
        }
        double u = new OddsRng(raceSeed).nextDouble();
        winner = chances.length - 1;
        for (int i = 0; i < chances.length; i++) {
            u -= chances[i];
            if (u < 0) {
                winner = i;
                break;
            }
        }
        paid = winner == backed ? board.payout(winner, stake) : 0;
        stage = winner == backed ? Stage.WON : Stage.LOST;
        return paid;
    }

    public int winner() {
        return winner;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case BOARD_OPEN -> String.format(Locale.ROOT,
                    "%d herbs in the pool, %.0f%% to the house. The crowd sets the price; my chalk sets the truth.",
                    board.pool(), TAKEOUT * 100);
            case BACKED -> overlay
                    ? "An overlay. The crowd let that one drift; you did not."
                    : "Under the chalk. You paid the crowd's price for the crowd's hunch.";
            case WON -> String.format(Locale.ROOT, "Paid %d herbs from the pool.", paid);
            case LOST -> "Not this heat. A good price loses sometimes; a bad one loses for good.";
        };
    }
}
