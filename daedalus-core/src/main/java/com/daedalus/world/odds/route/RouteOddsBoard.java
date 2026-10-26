// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.route;

import com.daedalus.world.odds.BalanceLimits;
import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import java.util.Objects;

/**
 * The Odds Keeper's ark-route board: every route sails once per trial under the same sky, and the route that brings the
 * most life home wins that trial (ties to the earlier-listed route). Trial {@code t} uses
 * {@link OddsRng#forTrial(long, long)}, so the board is a pure function of (routes, sky, seed, trials).
 */
public final class RouteOddsBoard {

    /** Smallest house edge the Keeper takes. */
    public static final double MIN_EDGE = 0.0;
    /** Largest house edge the Keeper may take; any request above is clamped. */
    public static final double MAX_EDGE = 0.10;

    private final List<ArkRoute> routes;
    private final Sky sky;
    private final int trials;
    private final int[] wins;
    private final int[] cleans;
    private final double[] lifeSum;

    private RouteOddsBoard(List<ArkRoute> routes, Sky sky, int trials, int[] wins, int[] cleans, double[] lifeSum) {
        this.routes = routes;
        this.sky = sky;
        this.trials = trials;
        this.wins = wins;
        this.cleans = cleans;
        this.lifeSum = lifeSum;
    }

    /** Sails every route {@code trials} times from {@code seed} under {@code sky}. */
    public static RouteOddsBoard simulate(List<ArkRoute> routes, Sky sky, long seed, int trials) {
        List<ArkRoute> rs = List.copyOf(Objects.requireNonNull(routes, "routes"));
        Objects.requireNonNull(sky, "sky");
        if (rs.size() < 2) {
            throw new IllegalArgumentException("a board needs at least two routes: " + rs.size());
        }
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int n = rs.size();
        int[] wins = new int[n];
        int[] cleans = new int[n];
        double[] lifeSum = new double[n];
        for (int t = 0; t < trials; t++) {
            wins[race(rs, sky, OddsRng.forTrial(seed, t), cleans, lifeSum)]++;
        }
        return new RouteOddsBoard(rs, sky, trials, wins, cleans, lifeSum);
    }

    /** Sails every route once on {@code rng}; returns the index of the route with the most life home. */
    static int race(List<ArkRoute> routes, Sky sky, OddsRng rng, int[] cleans, double[] lifeSum) {
        int best = 0;
        double bestLife = -1;
        for (int i = 0; i < routes.size(); i++) {
            ArkRoute.Voyage v = routes.get(i).sail(sky, rng);
            if (cleans != null && v.clean()) {
                cleans[i]++;
            }
            if (lifeSum != null) {
                lifeSum[i] += v.lifeHome();
            }
            if (v.lifeHome() > bestLife) {
                bestLife = v.lifeHome();
                best = i;
            }
        }
        return best;
    }

    public List<ArkRoute> routes() {
        return List.copyOf(routes);
    }

    public Sky sky() {
        return sky;
    }

    public int trials() {
        return trials;
    }

    /** Trials in which route {@code i} brought the most life home. */
    public int wins(int i) {
        return wins[i];
    }

    /** Estimated chance route {@code i} brings the most life home. */
    public double bestChance(int i) {
        return wins[i] / (double) trials;
    }

    /** Estimated clean-voyage chance of route {@code i}. */
    public double cleanChance(int i) {
        return cleans[i] / (double) trials;
    }

    /** 95% Wilson interval {lo, hi} on the clean-voyage chance of route {@code i}. */
    public double[] cleanInterval(int i) {
        return Intervals.wilson(cleans[i], trials);
    }

    /** Mean life home of route {@code i} across the trials. */
    public double meanLifeHome(int i) {
        return lifeSum[i] / trials;
    }

    /** Fair decimal odds that route {@code i} brings the most life home; infinite if it never did. */
    public double fairOdds(int i) {
        return wins[i] == 0 ? Double.POSITIVE_INFINITY : trials / (double) wins[i];
    }

    /** House edge clamped to [{@link #MIN_EDGE}, {@link #MAX_EDGE}]. */
    public static double clampEdge(double edge) {
        if (Double.isNaN(edge)) {
            return MIN_EDGE;
        }
        return Math.max(MIN_EDGE, Math.min(MAX_EDGE, edge));
    }

    /**
     * Posted decimal odds for route {@code i}: fair odds shaded by the clamped edge, never below evens (1.0). Infinite
     * fair odds post as 0 (off the board).
     */
    public double postedOdds(int i, double edge) {
        double fair = fairOdds(i);
        if (Double.isInfinite(fair)) {
            return 0.0;
        }
        return Math.max(1.0, fair * (1.0 - clampEdge(edge)));
    }

    /** Index of the favourite (most wins; ties to the earlier route). */
    public int favourite() {
        int best = 0;
        for (int i = 1; i < wins.length; i++) {
            if (wins[i] > wins[best]) {
                best = i;
            }
        }
        return best;
    }

    /**
     * Whether the Keeper may post this board under {@code limits}: no route may be a lock (favourite's best chance
     * above {@code maxPWin}), and the favourite must clear {@code 1 - maxPWin} so the race is not pure noise either.
     */
    public boolean postable(BalanceLimits limits) {
        Objects.requireNonNull(limits, "limits");
        double fav = bestChance(favourite());
        return fav <= limits.maxPWin() && fav >= 1.0 - limits.maxPWin();
    }
}
