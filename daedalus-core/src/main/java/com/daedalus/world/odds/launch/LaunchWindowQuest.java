// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.launch;

import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_launch_window: the glass is read at dawn, the Keeper chalks every launch option, and the player names a
 * route and a day. A choice within {@link #TOLERANCE} of the Keeper's best expected life earns the Keeper's nod; then
 * the ark sails once (sky drawn from the forecast, then the G47 voyage) on a fresh seeded stream.
 */
public final class LaunchWindowQuest {

    /** A choice worth at least this fraction of the best option's expected life counts as wise. */
    public static final double TOLERANCE = 0.98;

    /** Quest stages. */
    public enum Stage { FORECAST, CHOSEN, SAILED }

    private final LaunchPlanner planner;
    private final StormGlass.Reading reading;
    private final LaunchOption best;
    private Stage stage = Stage.FORECAST;
    private LaunchOption chosen;
    private Sky launchSky;
    private double lifeHome = -1;

    public LaunchWindowQuest(LaunchPlanner planner, StormGlass.Reading reading) {
        this.planner = Objects.requireNonNull(planner, "planner");
        this.reading = Objects.requireNonNull(reading, "reading");
        this.best = planner.best(reading);
    }

    public Stage stage() {
        return stage;
    }

    public LaunchOption best() {
        return best;
    }

    public LaunchOption chosen() {
        return chosen;
    }

    /** Sky on the launch day, or null before sailing. */
    public Sky launchSky() {
        return launchSky;
    }

    /** Life brought home, or -1 before sailing. */
    public double lifeHome() {
        return lifeHome;
    }

    /** Names a route and a day to launch. */
    public LaunchOption choose(int route, int day) {
        if (stage != Stage.FORECAST) {
            throw new IllegalStateException("already chosen: " + stage);
        }
        double life = planner.expectedLife(reading, route, day);
        chosen = new LaunchOption(route, planner.routes().get(route).name(), day, life);
        stage = Stage.CHOSEN;
        return chosen;
    }

    /** Whether the chosen option is within {@link #TOLERANCE} of the best. */
    public boolean wise() {
        return chosen != null && chosen.expectedLife() >= TOLERANCE * best.expectedLife();
    }

    /** Sails once: draws the launch-day sky from the forecast, then the route's voyage, then the wait cost. */
    public double sail(long voyageSeed) {
        if (stage != Stage.CHOSEN) {
            throw new IllegalStateException("choose a launch first: " + stage);
        }
        OddsRng rng = new OddsRng(voyageSeed);
        double[] dist = planner.forecast(reading, chosen.day());
        double u = rng.nextDouble();
        launchSky = Sky.STORM;
        for (Sky sky : Sky.values()) {
            u -= dist[sky.ordinal()];
            if (u < 0) {
                launchSky = sky;
                break;
            }
        }
        ArkRoute route = planner.routes().get(chosen.route());
        lifeHome = route.sail(launchSky, rng).lifeHome() * Math.pow(planner.waitKeep(), chosen.day());
        stage = Stage.SAILED;
        return lifeHome;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case FORECAST -> String.format(Locale.ROOT,
                    "Glass reads %s. Chalk says %s, %s, about %.0f souls home.",
                    reading, best.routeName(), dayWord(best.day()), best.expectedLife());
            case CHOSEN -> wise()
                    ? "A fair launch. The old ark captains would have signed it."
                    : String.format(Locale.ROOT, "Your call, captain. Chalk had %.0f souls on %s.",
                            best.expectedLife(), best.routeName());
            case SAILED -> String.format(Locale.ROOT,
                    "Launched under a %s sky on %s: %.0f souls home.",
                    launchSky.name().toLowerCase(Locale.ROOT), chosen.routeName(), lifeHome);
        };
    }

    private static String dayWord(int day) {
        return day == 0 ? "today" : day == 1 ? "tomorrow" : "in " + day + " days";
    }
}
