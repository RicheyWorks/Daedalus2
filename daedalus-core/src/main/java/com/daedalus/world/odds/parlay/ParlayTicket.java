// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.parlay;

import com.daedalus.world.fishing.Conditions;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * One Storm Parlay ticket on the Odds Keeper's board: land these fish, one per cast, in this order. {@code probability}
 * is the true chance (from {@code FishingOdds}); {@code fairMultiplier} = 1 / probability; the board offers
 * {@code offeredMultiplier}, which never sits more than {@link ParlayBoard#HOUSE_EDGE} under fair. Immutable.
 */
public final class ParlayTicket {

    private final String id;
    private final int day;
    private final Conditions conditions;
    private final List<String> legs;
    private final double probability;
    private final double offeredMultiplier;

    public ParlayTicket(String id, int day, Conditions conditions, List<String> legs, double probability,
                        double offeredMultiplier) {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("ticket id is missing");
        }
        if (conditions == null) {
            throw new IllegalArgumentException("ticket needs conditions");
        }
        if (legs == null || legs.isEmpty()) {
            throw new IllegalArgumentException("ticket needs at least one leg");
        }
        if (!(probability > 0 && probability <= 1)) {
            throw new IllegalArgumentException("ticket probability must be in (0, 1], got " + probability);
        }
        if (!(offeredMultiplier >= 1) || Double.isInfinite(offeredMultiplier)) {
            throw new IllegalArgumentException("offered multiplier must be a finite number >= 1, got " + offeredMultiplier);
        }
        this.id = id;
        this.day = day;
        this.conditions = conditions;
        this.legs = List.copyOf(legs);
        this.probability = probability;
        this.offeredMultiplier = offeredMultiplier;
    }

    public String id() {
        return id;
    }

    public int day() {
        return day;
    }

    public Conditions conditions() {
        return conditions;
    }

    /** The catches, in order. A copy. */
    public List<String> legs() {
        return new ArrayList<>(legs);
    }

    public int legCount() {
        return legs.size();
    }

    public double probability() {
        return probability;
    }

    public double fairMultiplier() {
        return 1 / probability;
    }

    public double offeredMultiplier() {
        return offeredMultiplier;
    }

    /** The keeper's cut: 1 - offered / fair. */
    public double houseEdge() {
        return 1 - offeredMultiplier * probability;
    }

    /** Herbs paid back (stake included) on a win. */
    public long payout(int stake) {
        return (long) Math.floor(stake * offeredMultiplier);
    }

    /** Expected herbs won or lost per stake (negative = the keeper's edge). */
    public double expectedProfit(int stake) {
        return probability * payout(stake) - stake;
    }

    /** True when {@code catches} (one entry per cast, null or "" for nothing landed) hit every leg in order. */
    public boolean wins(List<String> catches) {
        if (catches == null || catches.size() < legs.size()) {
            throw new IllegalArgumentException("ticket " + id + " needs " + legs.size() + " cast results");
        }
        for (int i = 0; i < legs.size(); i++) {
            if (!legs.get(i).equals(catches.get(i))) {
                return false;
            }
        }
        return true;
    }

    @Override
    public String toString() {
        return String.format(Locale.ROOT, "%s %s %s: 1 in %.0f, pays %.1fx", id, conditions.label(), legs,
                fairMultiplier(), offeredMultiplier);
    }
}
