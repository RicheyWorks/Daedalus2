// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Spark Tally (contest gap G322): sparks of many colours fly past faster than the clerk can write. Keep a fixed-size
 * tally that never undercounts a colour, overcounts by at most {@code eps * N} with probability {@code 1 - delta}, and
 * name the heavy colours.
 *
 * <p>The tool is plain: a Count-Min sketch with width {@code ceil(e / eps)}, depth {@code ceil(ln(1 / delta))} and
 * seeded per-row hashes, with an optional conservative update that only raises the rows it must. Any project can use
 * it for approximate frequency counts over {@code long} keys.
 */
public final class SparkTally {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_spark_tally";

    /** How a tally went. */
    public enum Grade { TALLIED, MISCOUNTED }

    private final int width;
    private final long[][] rows;
    private final long[] salt;
    private final boolean conservative;
    private long total;

    /** A sketch with error {@code eps} and failure chance {@code delta}; same seed, same hashes. */
    public SparkTally(double eps, double delta, long seed, boolean conservative) {
        if (!(eps > 0 && eps < 1) || !(delta > 0 && delta < 1)) {
            throw new IllegalArgumentException("need 0 < eps, delta < 1");
        }
        this.width = (int) Math.ceil(Math.E / eps);
        int depth = (int) Math.ceil(Math.log(1 / delta));
        this.rows = new long[depth][width];
        this.salt = new long[depth];
        SplittableRandom r = new SplittableRandom(seed);
        for (int i = 0; i < depth; i++) {
            salt[i] = r.nextLong();
        }
        this.conservative = conservative;
    }

    /** Columns per row. */
    public int width() {
        return width;
    }

    /** Number of rows. */
    public int depth() {
        return rows.length;
    }

    /** Total count added so far. */
    public long total() {
        return total;
    }

    private int col(int row, long key) {
        long z = key + salt[row];
        z = (z ^ (z >>> 30)) * 0xbf58476d1ce4e5b9L;
        z = (z ^ (z >>> 27)) * 0x94d049bb133111ebL;
        z ^= z >>> 31;
        return (int) Math.floorMod(z, (long) width);
    }

    /** Add {@code count} sparks of colour {@code key}. */
    public void add(long key, long count) {
        if (count < 0) {
            throw new IllegalArgumentException("count must be non-negative");
        }
        total += count;
        if (conservative) {
            long target = estimate(key) + count;
            for (int i = 0; i < rows.length; i++) {
                int c = col(i, key);
                rows[i][c] = Math.max(rows[i][c], target);
            }
        } else {
            for (int i = 0; i < rows.length; i++) {
                rows[i][col(i, key)] += count;
            }
        }
    }

    /** Estimated count of {@code key}: never below the true count. */
    public long estimate(long key) {
        long m = Long.MAX_VALUE;
        for (int i = 0; i < rows.length; i++) {
            m = Math.min(m, rows[i][col(i, key)]);
        }
        return m;
    }

    /** Candidates whose estimate reaches {@code phi * total}, in the order given. */
    public long[] heavy(long[] candidates, double phi) {
        double bar = phi * total;
        return Arrays.stream(candidates).filter(k -> estimate(k) >= bar).toArray();
    }

    /** A seeded skewed stream of {@code n} colours drawn from {@code 0..colours-1} (low colours far more common). */
    public static long[] stream(long seed, int n, int colours) {
        if (n < 0 || colours < 1) {
            throw new IllegalArgumentException("need n >= 0 and colours >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[] s = new long[n];
        for (int i = 0; i < n; i++) {
            int a = r.nextInt(colours);
            s[i] = r.nextInt(a + 1);
        }
        return s;
    }

    /** TALLIED only if the claimed heavy set is exactly what the sketch reports. */
    public Grade grade(long[] candidates, double phi, long[] claimed) {
        return Arrays.equals(heavy(candidates, phi), claimed) ? Grade.TALLIED : Grade.MISCOUNTED;
    }

    /** The Forgemaster's line for a tally. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TALLIED -> "Forgemaster: a small slate and still you caught the colours that matter.";
            case MISCOUNTED -> "Forgemaster: your slate tells a different story than the sparks. Tally again.";
        };
    }
}
