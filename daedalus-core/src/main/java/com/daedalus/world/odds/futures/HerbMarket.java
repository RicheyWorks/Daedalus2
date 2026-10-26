// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.futures;

import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import java.util.Objects;

/**
 * Storm-herb spot prices on OddsReaper Island: storms flatten the herb beds, so herbs are dearest after a STORM day.
 * The fair forward price for day {@code d} is the forecast-weighted spot price, using the G22 storm glass read at dawn.
 */
public final class HerbMarket {

    /** CALM 10, SQUALL 14, STORM 22 herb-tokens per bundle. */
    public static final HerbMarket ODDSREAPER = new HerbMarket(StormGlass.ODDSREAPER, 10, 14, 22);

    private final StormGlass glass;
    private final double[] spot;

    public HerbMarket(StormGlass glass, double calm, double squall, double storm) {
        this.glass = Objects.requireNonNull(glass, "glass");
        if (!(calm > 0 && squall > 0 && storm > 0)) {
            throw new IllegalArgumentException("prices must be > 0");
        }
        this.spot = new double[] {calm, squall, storm};
    }

    public StormGlass glass() {
        return glass;
    }

    /** Spot price on a day whose sky is {@code sky}. */
    public double spot(Sky sky) {
        return spot[Objects.requireNonNull(sky, "sky").ordinal()];
    }

    /** Fair forward price {@code day} days out, given this morning's reading. */
    public double fairForward(StormGlass.Reading reading, int day) {
        double[] d = forecast(reading, day);
        double f = 0;
        for (Sky s : Sky.values()) {
            f += d[s.ordinal()] * spot(s);
        }
        return f;
    }

    /** Variance of the spot price {@code day} days out, given this morning's reading. */
    public double spotVariance(StormGlass.Reading reading, int day) {
        double[] d = forecast(reading, day);
        double mean = fairForward(reading, day);
        double v = 0;
        for (Sky s : Sky.values()) {
            double x = spot(s) - mean;
            v += d[s.ordinal()] * x * x;
        }
        return v;
    }

    /** Sky distribution {@code day} days after the dawn reading. */
    public double[] forecast(StormGlass.Reading reading, int day) {
        if (day < 0) {
            throw new IllegalArgumentException("day must be >= 0: " + day);
        }
        return glass.forecast(glass.chain().climate(), Objects.requireNonNull(reading, "reading"), day);
    }
}
