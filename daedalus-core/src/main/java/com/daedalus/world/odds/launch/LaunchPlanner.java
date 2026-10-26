// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.launch;

import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.route.ArkRouteWager;
import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Picks an ark's launch window: read the G22 storm glass this morning, forecast the sky for each of the next days, and
 * price every (route, day) pair from G47 by expected life home. Waiting is not free: every day at anchor keeps only
 * {@code waitKeep} of the life aboard (rations, sickness). Pure and deterministic; read-only on G22 and G47.
 */
public final class LaunchPlanner {

    /** OddsReaper Island: its storm glass, the three charted belt routes, up to 3 days' wait, 2% lost per day. */
    public static final LaunchPlanner ODDSREAPER =
            new LaunchPlanner(StormGlass.ODDSREAPER, ArkRouteWager.ODDSREAPER_ROUTES, 3, 0.98);

    private final StormGlass glass;
    private final List<ArkRoute> routes;
    private final int maxDays;
    private final double waitKeep;

    public LaunchPlanner(StormGlass glass, List<ArkRoute> routes, int maxDays, double waitKeep) {
        this.glass = Objects.requireNonNull(glass, "glass");
        this.routes = List.copyOf(Objects.requireNonNull(routes, "routes"));
        if (this.routes.isEmpty()) {
            throw new IllegalArgumentException("need at least one route");
        }
        if (maxDays < 0) {
            throw new IllegalArgumentException("maxDays must be >= 0: " + maxDays);
        }
        if (!(waitKeep > 0 && waitKeep <= 1)) {
            throw new IllegalArgumentException("waitKeep must be in (0, 1]: " + waitKeep);
        }
        this.maxDays = maxDays;
        this.waitKeep = waitKeep;
    }

    public List<ArkRoute> routes() {
        return List.copyOf(routes);
    }

    public int maxDays() {
        return maxDays;
    }

    public double waitKeep() {
        return waitKeep;
    }

    /** Sky distribution (by {@link Sky} ordinal) {@code day} days after this morning's {@code reading}. */
    public double[] forecast(StormGlass.Reading reading, int day) {
        return glass.forecast(glass.chain().climate(), Objects.requireNonNull(reading, "reading"), day);
    }

    /** Expected life home launching route {@code route} after waiting {@code day} days. */
    public double expectedLife(StormGlass.Reading reading, int route, int day) {
        Objects.checkIndex(route, routes.size());
        if (day < 0 || day > maxDays) {
            throw new IllegalArgumentException("day must be in [0, " + maxDays + "]: " + day);
        }
        double[] dist = forecast(reading, day);
        double life = 0;
        for (Sky sky : Sky.values()) {
            life += dist[sky.ordinal()] * routes.get(route).expectedLifeHome(sky);
        }
        return life * Math.pow(waitKeep, day);
    }

    /** Every (route, day) option, day-major then route order. */
    public List<LaunchOption> options(StormGlass.Reading reading) {
        List<LaunchOption> out = new ArrayList<>();
        for (int day = 0; day <= maxDays; day++) {
            for (int r = 0; r < routes.size(); r++) {
                out.add(new LaunchOption(r, routes.get(r).name(), day, expectedLife(reading, r, day)));
            }
        }
        return out;
    }

    /** The Keeper's pick: most expected life home (ties to the earlier day, then the earlier route). */
    public LaunchOption best(StormGlass.Reading reading) {
        LaunchOption best = null;
        for (LaunchOption o : options(reading)) {
            if (best == null || o.expectedLife() > best.expectedLife()) {
                best = o;
            }
        }
        return best;
    }
}
