// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.dice;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_storm_dice: the ark crews' dice game at the inn. The player picks how many herbs of free (true-odds) backing
 * to put behind every point, 0 to {@link #MAX_ODDS}, then shoots {@link #ROUNDS} rounds. The lesson: the pass line
 * has a small house edge and the odds bet has none, so full odds is the smartest table in the house. The quest passes
 * when the player takes full odds; the herbs are whatever the dice give. In-game herbs only.
 */
public final class StormDiceQuest {

    public static final int MAX_ODDS = 3;
    public static final int ROUNDS = 10;

    /** Quest stages. */
    public enum Stage { AT_THE_TABLE, SHOT }

    private Stage stage = Stage.AT_THE_TABLE;
    private int multiple = -1;
    private double net;
    private int wins;

    public Stage stage() {
        return stage;
    }

    /** Shoots {@link #ROUNDS} rounds with odds multiple {@code m}; returns net herbs. */
    public double shoot(int m, long seed) {
        if (stage != Stage.AT_THE_TABLE) {
            throw new IllegalStateException("already shot: " + stage);
        }
        if (m < 0 || m > MAX_ODDS) {
            throw new IllegalArgumentException("odds multiple must be in [0, " + MAX_ODDS + "]: " + m);
        }
        OddsRng rng = new OddsRng(seed);
        for (int i = 0; i < ROUNDS; i++) {
            StormDice.Round r = StormDice.play(rng, m);
            net += r.net();
            if (r.won()) {
                wins++;
            }
        }
        multiple = m;
        stage = Stage.SHOT;
        return net;
    }

    public double net() {
        return net;
    }

    public int wins() {
        return wins;
    }

    /** Passed when the player took full odds. */
    public boolean passed() {
        return stage == Stage.SHOT && multiple == MAX_ODDS;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case AT_THE_TABLE -> String.format(Locale.ROOT,
                    "Pass line wins 244 in 495. House keeps %.2f%% of every herb; behind a point I pay true odds.",
                    DiceMath.edgePerHerbWagered(0) * 100);
            case SHOT -> passed()
                    ? String.format(Locale.ROOT,
                            "Full odds: my edge is down to %.2f%% a herb. %d of %d rounds won, %+.1f herbs.",
                            DiceMath.edgePerHerbWagered(MAX_ODDS) * 100, wins, ROUNDS, net)
                    : String.format(Locale.ROOT,
                            "%d of %d rounds, %+.1f herbs. You left free odds on my table.", wins, ROUNDS, net);
        };
    }
}
