// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.parlay;

import java.text.NumberFormat;
import java.util.Locale;

/**
 * What the Odds Keeper says. She runs the chalkboard at the OddsReaper Island inn, keeps her cut small and says it out
 * loud, and never lets a player stake what they cannot see the odds of. Lines are plain text for any dialog system.
 */
public final class OddsKeeper {

    private OddsKeeper() {
    }

    /** The keeper's pitch for a ticket. */
    public static String pitch(ParlayTicket t) {
        String sky = t.conditions().storm() ? "Storm's up, the deep fish are rising." : "Calm water today.";
        String legs = String.join(", then ", t.legs());
        return sky + " " + legs + ": one in " + whole(t.fairMultiplier()) + ". I pay " + whole(t.offeredMultiplier())
                + " herbs back for every herb, my cut is " + String.format(Locale.ROOT, "%.1f", 100 * t.houseEdge()) + "%.";
    }

    /** What she says when a ticket settles. */
    public static String settle(ParlayTicket t, long paid) {
        if (paid > 0) {
            return "The water paid you: " + whole(paid) + " storm herbs. Ticket " + t.id() + " is closed.";
        }
        return "Not this time. The odds were honest, and so is the ledger. Ticket " + t.id() + " is closed.";
    }

    /** Her line for the keeper's quest, by progress. */
    public static String ledger(ParlayBook book) {
        if (book.ledgerEarned()) {
            return "You have settled your tickets like a true reaper of odds. Take the Storm Ledger.";
        }
        int left = ParlayBook.LEDGER_GOAL - book.settled();
        return "Settle " + left + " more ticket" + (left == 1 ? "" : "s") + ", win or lose, and the Storm Ledger is yours.";
    }

    private static String whole(double v) {
        return NumberFormat.getIntegerInstance(Locale.ROOT).format(Math.round(v));
    }
}
