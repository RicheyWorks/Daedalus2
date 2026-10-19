// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.futures;

import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_herb_hedge: Mossa the herb grower will harvest {@link #HARVEST} bundles on {@link #HARVEST_DAY} and fears a
 * calm week will crash the price. The player chooses how many bundles to sell forward on the Keeper's desk. Revenue at
 * settlement is harvest x spot plus the forward's payoff. Selling h bundles forward scales the revenue variance by
 * ((HARVEST - h) / HARVEST)^2; hedging at least {@link #MIN_HEDGE} of the harvest earns Mossa's thanks. In-game only.
 */
public final class HerbHedgeQuest {

    public static final int HARVEST = 20;
    public static final int HARVEST_DAY = 3;
    public static final double MIN_HEDGE = 0.5;

    /** Quest stages. */
    public enum Stage { QUOTED, HEDGED, SETTLED }

    private final FuturesDesk desk;
    private final HerbMarket market;
    private Stage stage = Stage.QUOTED;
    private Forward forward;
    private double revenue;

    public HerbHedgeQuest(HerbMarket market, FuturesDesk desk) {
        this.market = Objects.requireNonNull(market, "market");
        this.desk = Objects.requireNonNull(desk, "desk");
    }

    public Stage stage() {
        return stage;
    }

    /** Revenue variance if {@code hedged} bundles are sold forward (forward price is fixed; only spot varies). */
    public double revenueVariance(int hedged) {
        if (hedged < 0 || hedged > HARVEST) {
            throw new IllegalArgumentException("hedged must be in [0, " + HARVEST + "]: " + hedged);
        }
        int open = HARVEST - hedged;
        return (double) open * open * market.spotVariance(desk.dawnReading(), HARVEST_DAY);
    }

    /** Sells {@code bundles} of the harvest forward (0 = stay unhedged). */
    public void hedge(int bundles) {
        if (stage != Stage.QUOTED) {
            throw new IllegalStateException("already hedged: " + stage);
        }
        if (bundles < 0 || bundles > HARVEST) {
            throw new IllegalArgumentException("bundles must be in [0, " + HARVEST + "]: " + bundles);
        }
        forward = bundles == 0 ? null : desk.sell(HARVEST_DAY, bundles);
        stage = Stage.HEDGED;
    }

    /** Hedged bundles (0 if unhedged). */
    public int hedged() {
        return forward == null ? 0 : forward.bundles();
    }

    /** Whether the hedge covers at least {@link #MIN_HEDGE} of the harvest. */
    public boolean prudent() {
        return hedged() >= Math.ceil(MIN_HEDGE * HARVEST);
    }

    /** Settles on the real harvest-day sky; returns Mossa's revenue. */
    public double settle() {
        if (stage != Stage.HEDGED) {
            throw new IllegalStateException("hedge first: " + stage);
        }
        revenue = HARVEST * desk.settleSpot(HARVEST_DAY) + (forward == null ? 0 : desk.settle(forward));
        stage = Stage.SETTLED;
        return revenue;
    }

    public double revenue() {
        return revenue;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case QUOTED -> String.format(Locale.ROOT,
                    "Glass reads %s. I'll take Mossa's day-%d bundles at %.1f each, forward.",
                    desk.dawnReading(), HARVEST_DAY, desk.bid(HARVEST_DAY));
            case HEDGED -> prudent()
                    ? "Half the harvest or more locked in. Mossa sleeps tonight."
                    : "Mostly open. Mossa is betting on the weather now, not on herbs.";
            case SETTLED -> String.format(Locale.ROOT,
                    "Harvest settled under a %s sky: %.0f tokens to Mossa.",
                    desk.skyOn(HARVEST_DAY).name().toLowerCase(Locale.ROOT), revenue);
        };
    }
}
