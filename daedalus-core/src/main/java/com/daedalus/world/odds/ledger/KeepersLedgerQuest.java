// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.ledger;

import java.util.Locale;

/**
 * Quest q_keepers_ledger: the Odds Keeper opens a ledger of {@link #START} storm herbs for the player. Double it to
 * {@link #TARGET} within {@link #MAX_WAGERS} Keeper wagers (any board: G18 parlay, G35 cup, G47 route) without going
 * broke. Every stake at or under the Keeper's half-Kelly advice counts as disciplined; a doubled ledger with every
 * stake disciplined also earns the Keeper's Mark. Herbs are in-game only; there is no real-money wagering.
 */
public final class KeepersLedgerQuest {

    public static final int START = 20;
    public static final int TARGET = 40;
    public static final int MAX_WAGERS = 12;

    /** Quest stages. */
    public enum Stage { OPEN, DOUBLED, BROKE, OUT_OF_WAGERS }

    private final HerbLedger ledger = new HerbLedger(START);
    private Stage stage = Stage.OPEN;
    private int disciplined;

    public Stage stage() {
        return stage;
    }

    /** Current storm-herb balance. */
    public int balance() {
        return ledger.balance();
    }

    /** Settled wagers, oldest first (an immutable copy). */
    public java.util.List<HerbLedger.Entry> history() {
        return ledger.history();
    }

    public int disciplined() {
        return disciplined;
    }

    /** The Keeper's advised stake for a wager with chance {@code p} at posted {@code odds}. */
    public int advice(double p, double odds) {
        return KellyStake.advise(ledger.balance(), p, odds);
    }

    /**
     * Places and settles one wager. {@code p} is the board's quoted chance, used only to judge discipline.
     *
     * @return the new stage
     */
    public Stage wager(String game, int stake, double p, double odds, boolean won) {
        if (stage != Stage.OPEN) {
            throw new IllegalStateException("ledger closed: " + stage);
        }
        int advised = advice(p, odds);
        ledger.settle(game, stake, odds, won);
        if (stake <= advised) {
            disciplined++;
        }
        if (ledger.balance() >= TARGET) {
            stage = Stage.DOUBLED;
        } else if (ledger.broke()) {
            stage = Stage.BROKE;
        } else if (ledger.history().size() >= MAX_WAGERS) {
            stage = Stage.OUT_OF_WAGERS;
        }
        return stage;
    }

    /** Doubled with every stake at or under advice. */
    public boolean keepersMark() {
        return stage == Stage.DOUBLED && disciplined == ledger.history().size();
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case OPEN -> String.format(Locale.ROOT,
                    "%d herbs on the ledger, %d wagers left. Stake what the odds justify, not what hope asks.",
                    ledger.balance(), MAX_WAGERS - ledger.history().size());
            case DOUBLED -> keepersMark()
                    ? "Doubled, and never once over my advice. Take the Keeper's Mark; the arks needed hands like yours."
                    : "Doubled. Lucky or good, the ledger cannot tell yet. Next time, stake by the chalk.";
            case BROKE -> "Ledger's empty. The arks rationed better than that. Come back when the glass falls.";
            case OUT_OF_WAGERS -> String.format(Locale.ROOT,
                    "Twelve wagers and %d herbs. Steady keeps an ark afloat; it does not double it.",
                    ledger.balance());
        };
    }
}
