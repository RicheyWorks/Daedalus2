// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.futures;

import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import java.util.Objects;

/**
 * The Odds Keeper's herb forward desk: he quotes a bid and an ask around the fair forward price (spread capped at
 * {@link #MAX_SPREAD}), and settles on the island's real sky for the delivery day ({@code StormChain.skyOn}), so every
 * player on the same island seed settles the same way.
 */
public final class FuturesDesk {

    public static final double MAX_SPREAD = 0.10;

    private final HerbMarket market;
    private final long islandSeed;
    private final Sky start;
    private final double spread;

    public FuturesDesk(HerbMarket market, long islandSeed, Sky start, double spread) {
        this.market = Objects.requireNonNull(market, "market");
        this.start = Objects.requireNonNull(start, "start");
        this.islandSeed = islandSeed;
        this.spread = Double.isNaN(spread) ? 0 : Math.max(0, Math.min(MAX_SPREAD, spread));
    }

    public double spread() {
        return spread;
    }

    /** The glass reading at dawn on day 0 for this island. */
    public StormGlass.Reading dawnReading() {
        return market.glass().readOn(islandSeed, start, 0);
    }

    public double fair(int day) {
        return market.fairForward(dawnReading(), day);
    }

    /** Price the Keeper pays when you sell forward. */
    public double bid(int day) {
        return fair(day) * (1 - spread);
    }

    /** Price the Keeper charges when you buy forward. */
    public double ask(int day) {
        return fair(day) * (1 + spread);
    }

    /** Buy {@code bundles} forward for {@code day} at the ask. */
    public Forward buy(int day, int bundles) {
        return new Forward(day, bundles, ask(day), true);
    }

    /** Sell {@code bundles} forward for {@code day} at the bid. */
    public Forward sell(int day, int bundles) {
        return new Forward(day, bundles, bid(day), false);
    }

    /** The island's real sky on {@code day}. */
    public Sky skyOn(int day) {
        return market.glass().chain().skyOn(islandSeed, start, day);
    }

    /** Spot price on the delivery day. */
    public double settleSpot(int day) {
        return market.spot(skyOn(day));
    }

    public double settle(Forward f) {
        return f.payoff(settleSpot(f.day()));
    }
}
