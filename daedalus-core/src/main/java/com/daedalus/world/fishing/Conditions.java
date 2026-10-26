// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

/**
 * The sky over the water when the line goes in. Night swaps in each fish's night weight (the rare ones feed after dusk).
 * A storm is OddsReaper Island's twist: the squall stirs the deep water, so RARE and LEGENDARY fish bite
 * {@value #STORM_RARE_BOOST}x as often, bites come sooner ({@value #STORM_WAIT_FACTOR}x the wait) and every bite is
 * shorter ({@value #STORM_WINDOW_FACTOR}x the window): better odds on the big fish, less time to land it.
 */
public record Conditions(boolean night, boolean storm) {

    public static final Conditions DAY = new Conditions(false, false);
    public static final Conditions NIGHT = new Conditions(true, false);
    public static final Conditions STORM = new Conditions(false, true);
    public static final Conditions NIGHT_STORM = new Conditions(true, true);

    public static final double STORM_RARE_BOOST = 2.0;
    public static final double STORM_WAIT_FACTOR = 0.75;
    public static final double STORM_WINDOW_FACTOR = 0.85;

    /** First night hour (19:00) and first day hour (06:00) on the 24-hour island clock. */
    public static final int DUSK_HOUR = 19;
    public static final int DAWN_HOUR = 6;

    /** Conditions at an hour of the island day (0-23). */
    public static Conditions atHour(int hour, boolean storm) {
        if (hour < 0 || hour > 23) {
            throw new IllegalArgumentException("hour must be 0-23, got " + hour);
        }
        return new Conditions(hour >= DUSK_HOUR || hour < DAWN_HOUR, storm);
    }

    /** The bite weight {@code fish} has under these conditions. */
    public double weight(FishSpecies fish) {
        double w = fish.weightAt(night);
        return storm && fish.rarity().isRare() ? w * STORM_RARE_BOOST : w;
    }

    /** How long a bite from {@code fish} lasts under these conditions, in seconds. */
    public double window(FishSpecies fish) {
        return storm ? fish.windowSeconds() * STORM_WINDOW_FACTOR : fish.windowSeconds();
    }

    /** Multiplier on the wait before a bite. */
    public double waitFactor() {
        return storm ? STORM_WAIT_FACTOR : 1.0;
    }

    /** "day", "night", "storm" or "night storm". */
    public String label() {
        if (night) {
            return storm ? "night storm" : "night";
        }
        return storm ? "storm" : "day";
    }
}
