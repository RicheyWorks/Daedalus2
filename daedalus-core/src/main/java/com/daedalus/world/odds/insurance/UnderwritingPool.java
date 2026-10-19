// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.insurance;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import java.util.List;
import java.util.Objects;

/**
 * The Keeper's underwriting pool for one sailing season: a starting reserve plus the premiums of every written policy,
 * minus the claims when each ark sails once. Arks sail in policy order, one G47 voyage each, on one stream. Insolvent
 * when the claims exceed the reserve plus premiums.
 */
public final class UnderwritingPool {

    private final int reserve;
    private final List<ArkPolicy> policies;
    private final double loading;

    public UnderwritingPool(int reserve, List<ArkPolicy> policies, double loading) {
        if (reserve < 0) {
            throw new IllegalArgumentException("reserve must be >= 0: " + reserve);
        }
        this.reserve = reserve;
        this.policies = List.copyOf(Objects.requireNonNull(policies, "policies"));
        if (this.policies.isEmpty()) {
            throw new IllegalArgumentException("write at least one policy");
        }
        this.loading = loading;
    }

    public int reserve() {
        return reserve;
    }

    public List<ArkPolicy> policies() {
        return List.copyOf(policies);
    }

    /** Sum of posted premiums. */
    public int premiums() {
        return policies.stream().mapToInt(p -> p.premium(loading)).sum();
    }

    /** Sum of expected claims. */
    public double expectedClaims() {
        return policies.stream().mapToDouble(ArkPolicy::expectedClaim).sum();
    }

    /** Sails every insured ark once on {@code rng}; returns the pool's closing balance (negative = insolvent). */
    public double season(OddsRng rng) {
        Objects.requireNonNull(rng, "rng");
        double balance = reserve + premiums();
        for (ArkPolicy p : policies) {
            balance -= p.claim(p.route().sail(p.sky(), rng).lifeHome());
        }
        return balance;
    }

    /** Seeded season board: trial {@code t} uses {@link OddsRng#forTrial(long, long)}. */
    public Board simulate(long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int bust = 0;
        double sum = 0;
        for (int t = 0; t < trials; t++) {
            double close = season(OddsRng.forTrial(seed, t));
            sum += close;
            if (close < 0) {
                bust++;
            }
        }
        return new Board(trials, bust, sum / trials - reserve);
    }

    /** Season odds: insolvent seasons out of {@code trials}, and mean profit over the reserve. */
    public record Board(int trials, int insolvent, double meanProfit) {
        public double insolvency() {
            return insolvent / (double) trials;
        }

        /** 95% Wilson interval on the insolvency chance. */
        public double[] interval() {
            return Intervals.wilson(insolvent, trials);
        }
    }
}
