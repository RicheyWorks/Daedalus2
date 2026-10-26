// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.parlay;

import com.daedalus.world.fishing.CastSession;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * One player's side of the Storm Parlay: a purse of storm herbs, the tickets they staked, and settlement that pays (or
 * keeps) each stake exactly once. Settling also advances the keeper's quest, "The Keeper's Ledger": settle
 * {@value #LEDGER_GOAL} tickets, win or lose, and the Odds Keeper hands over the Storm Ledger. In-game herbs only.
 */
public final class ParlayBook {

    /** Tickets to settle for the Storm Ledger. */
    public static final int LEDGER_GOAL = 3;
    /** Biggest stake the keeper takes on one ticket. */
    public static final int MAX_STAKE = 50;

    /** How a staked ticket stands. */
    public enum Status { OPEN, WON, LOST }

    private static final class Stake {
        private final ParlayTicket ticket;
        private final int herbs;
        private Status status = Status.OPEN;

        Stake(ParlayTicket ticket, int herbs) {
            this.ticket = ticket;
            this.herbs = herbs;
        }
    }

    private final Map<String, Stake> stakes = new LinkedHashMap<>();
    private long herbs;
    private int settled;

    public ParlayBook(long startingHerbs) {
        if (startingHerbs < 0) {
            throw new IllegalArgumentException("herbs must be >= 0, got " + startingHerbs);
        }
        this.herbs = startingHerbs;
    }

    public long herbs() {
        return herbs;
    }

    /** Stakes {@code amount} herbs on {@code ticket}. One stake per ticket. */
    public void stake(ParlayTicket ticket, int amount) {
        if (ticket == null) {
            throw new IllegalArgumentException("no ticket");
        }
        if (amount < 1 || amount > MAX_STAKE) {
            throw new IllegalArgumentException("stake must be 1-" + MAX_STAKE + " herbs, got " + amount);
        }
        if (amount > herbs) {
            throw new IllegalStateException("only " + herbs + " herbs in the purse");
        }
        if (stakes.containsKey(ticket.id())) {
            throw new IllegalStateException("ticket " + ticket.id() + " is already staked");
        }
        herbs -= amount;
        stakes.put(ticket.id(), new Stake(ticket, amount));
    }

    /**
     * Settles a ticket against the catches of the casts after it was staked (one entry per cast, null or "" for
     * nothing landed). Pays the ticket's payout on a win. Returns the herbs paid (0 on a loss).
     *
     * @throws IllegalStateException if the ticket was never staked or is already settled
     */
    public long settle(String ticketId, List<String> catches) {
        Stake s = stakes.get(ticketId);
        if (s == null) {
            throw new IllegalStateException("ticket " + ticketId + " was not staked");
        }
        if (s.status != Status.OPEN) {
            throw new IllegalStateException("ticket " + ticketId + " is already settled (" + s.status + ")");
        }
        boolean win = s.ticket.wins(catches);
        s.status = win ? Status.WON : Status.LOST;
        settled++;
        long paid = win ? s.ticket.payout(s.herbs) : 0;
        herbs += paid;
        return paid;
    }

    /** {@link #settle(String, List)} from finished casts: a CAUGHT cast counts as its fish, anything else as nothing. */
    public long settleCasts(String ticketId, List<CastSession> casts) {
        List<String> catches = new ArrayList<>();
        for (CastSession c : casts) {
            catches.add(c.outcome() == CastSession.Outcome.CAUGHT ? c.fish().orElseThrow().name() : "");
        }
        return settle(ticketId, catches);
    }

    public Status status(String ticketId) {
        Stake s = stakes.get(ticketId);
        if (s == null) {
            throw new IllegalArgumentException("ticket " + ticketId + " was not staked");
        }
        return s.status;
    }

    /** Tickets settled so far. */
    public int settled() {
        return settled;
    }

    /** True once the keeper's quest is done. */
    public boolean ledgerEarned() {
        return settled >= LEDGER_GOAL;
    }

    /** Herbs staked on tickets still open. */
    public long atRisk() {
        long r = 0;
        for (Stake s : stakes.values()) {
            if (s.status == Status.OPEN) {
                r += s.herbs;
            }
        }
        return r;
    }
}
