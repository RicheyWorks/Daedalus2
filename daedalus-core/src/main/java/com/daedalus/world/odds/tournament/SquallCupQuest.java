// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tournament;

import com.daedalus.world.odds.OddsRng;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_squall_cup: the player enters the Odds Keeper's storm-lane fishing cup. Each story beat is backed by a
 * mechanic: entry seeds the {@link Bracket}, the board quotes {@link CupOdds}, each round is a {@link Heat}, and the
 * purse pays a longshot bonus scaled by the pre-cup odds. The player is always entrant {@link #PLAYER}.
 */
public final class SquallCupQuest {

    /** Index of the player in the field. */
    public static final int PLAYER = 0;
    /** Storm herbs paid to any champion. */
    public static final int BASE_PURSE = 10;
    /** Cap on the longshot bonus multiplier. */
    public static final int MAX_MULTIPLIER = 8;

    /** Quest stages, in order. */
    public enum Stage { ENTERED, ODDS_POSTED, CHAMPION, KNOCKED_OUT }

    private final Bracket bracket;
    private final Heat heat;
    private final CupOdds board;
    private Stage stage;
    private int roundsWon;

    public SquallCupQuest(List<Angler> field, Heat heat, long seed, int trials) {
        this.bracket = new Bracket(field);
        this.heat = Objects.requireNonNull(heat, "heat");
        this.board = CupOdds.simulate(bracket, heat, seed, trials);
        this.stage = Stage.ODDS_POSTED;
    }

    public Stage stage() {
        return stage;
    }

    public CupOdds board() {
        return board;
    }

    public int roundsWon() {
        return roundsWon;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case ENTERED -> "Name in the ledger, line in the water. The squall decides the rest.";
            case ODDS_POSTED -> String.format(Locale.ROOT,
                    "Chalk says %.0f%% you lift the Cup. The arks fished worse lanes than these.",
                    board.chance(PLAYER) * 100);
            case CHAMPION -> "Champion of the storm lanes. The survivors would have fed a whole ark on that catch.";
            case KNOCKED_OUT -> "The squall took your line this time. Come back when the glass falls again.";
        };
    }

    /** Storm-herb purse for a champion: base times min(cap, round(1 / pre-cup chance)), at least the base. */
    public int purse() {
        double p = board.chance(PLAYER);
        int mult = p <= 0 ? MAX_MULTIPLIER : (int) Math.max(1, Math.min(MAX_MULTIPLIER, Math.round(1 / p)));
        return BASE_PURSE * mult;
    }

    /**
     * Fishes the real cup once (a fresh stream, not one of the board's trials) and settles the quest.
     *
     * @return storm herbs won (0 when knocked out)
     */
    public int fish(long cupSeed) {
        if (stage != Stage.ODDS_POSTED) {
            throw new IllegalStateException("cup already fished: " + stage);
        }
        List<List<Integer>> history = bracket.play(heat, new OddsRng(cupSeed));
        for (List<Integer> round : history) {
            if (!round.contains(PLAYER)) {
                break;
            }
            roundsWon++;
        }
        boolean champion = roundsWon == history.size();
        stage = champion ? Stage.CHAMPION : Stage.KNOCKED_OUT;
        return champion ? purse() : 0;
    }
}
