// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.weather;

import com.daedalus.world.odds.OddsRng;

/**
 * The storm glass on the inn wall: a barometer that reads HIGH, FALLING or LOW. It is honest but noisy (a calm day
 * still reads FALLING one time in five), so a forecast is Bayes: start from a prior over today's sky, update on the
 * reading, then roll the {@link StormChain} forward. The Odds Keeper reads it every morning before she chalks the
 * Storm Parlay board.
 */
public final class StormGlass {

    /** What the glass shows. */
    public enum Reading { HIGH, FALLING, LOW }

    /** OddsReaper Island's glass: rows = true sky, columns = reading. */
    public static final StormGlass ODDSREAPER = new StormGlass(StormChain.ODDSREAPER, new double[][] {
        {0.75, 0.20, 0.05},
        {0.20, 0.60, 0.20},
        {0.05, 0.25, 0.70}});

    static final long GLASS_SALT = 0x5709_6A55_0DD5_1E1EL;

    private final StormChain chain;
    private final double[][] likelihood;

    /** A glass over {@code chain} with a 3x3 likelihood matrix P(reading | sky), rows summing to 1. Copied. */
    public StormGlass(StormChain chain, double[][] likelihood) {
        if (chain == null) {
            throw new IllegalArgumentException("a storm glass needs a weather chain");
        }
        this.chain = chain;
        this.likelihood = StormChain.copyStochastic(likelihood);
    }

    public StormChain chain() {
        return chain;
    }

    /** P(reading | sky). */
    public double likelihood(Sky sky, Reading reading) {
        return likelihood[sky.ordinal()][reading.ordinal()];
    }

    /** What the glass shows on a day whose true sky is {@code sky}, for a uniform draw {@code u}. */
    public Reading read(Sky sky, double u) {
        if (!(u >= 0 && u < 1)) {
            throw new IllegalArgumentException("read needs u in [0, 1), got " + u);
        }
        double r = u;
        double[] row = likelihood[sky.ordinal()];
        for (int j = 0; j < 3; j++) {
            r -= row[j];
            if (r < 0) {
                return Reading.values()[j];
            }
        }
        return Reading.LOW;
    }

    /** The glass reading on an island day, seeded so all players see the same needle. */
    public Reading readOn(long islandSeed, Sky start, int day) {
        Sky truth = chain.skyOn(islandSeed, start, day);
        return read(truth, OddsRng.forTrial(islandSeed ^ GLASS_SALT, day).nextDouble());
    }

    /** Today's sky after seeing {@code reading}, from {@code prior}. */
    public double[] posterior(double[] prior, Reading reading) {
        StormChain.checkDist(prior);
        double[] post = new double[3];
        double z = 0;
        for (int i = 0; i < 3; i++) {
            post[i] = prior[i] * likelihood[i][reading.ordinal()];
            z += post[i];
        }
        if (z == 0) {
            throw new IllegalArgumentException("reading " + reading + " is impossible under this prior");
        }
        for (int i = 0; i < 3; i++) {
            post[i] /= z;
        }
        return post;
    }

    /** The sky distribution {@code daysAhead} days after a morning reading (0 = today). */
    public double[] forecast(double[] prior, Reading reading, int daysAhead) {
        return chain.after(posterior(prior, reading), daysAhead);
    }

    /** Chance of a full STORM {@code daysAhead} days out, starting from the island's climate. */
    public double stormChance(Reading reading, int daysAhead) {
        return forecast(chain.climate(), reading, daysAhead)[Sky.STORM.ordinal()];
    }
}
