// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.SplittableRandom;
import java.util.function.IntUnaryOperator;

/**
 * G290 The Current Loop: a cask set adrift at a buoy follows the current from buoy to buoy
 * (a map from 0..m-1 to itself). Sooner or later it circles forever. Finds the lead-in (how many
 * hops before the loop starts) and the loop length with Floyd's tortoise and hare and with Brent's
 * power-of-two search, both in O(1) memory.
 */
public final class CurrentLoop {

    public static final String QUEST_ID = "q_current_loop";

    /** Lead-in mu (hops before the first looped buoy) and loop length lambda. */
    public record Drift(int leadIn, int loop) { }

    private CurrentLoop() { }

    /** A seeded current map over m buoys. */
    public static int[] currents(int m, long seed) {
        if (m < 1) {
            throw new IllegalArgumentException("need at least one buoy");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] f = new int[m];
        for (int i = 0; i < m; i++) {
            f[i] = rnd.nextInt(m);
        }
        return f;
    }

    public static Drift floyd(IntUnaryOperator f, int start) {
        int slow = f.applyAsInt(start);
        int fast = f.applyAsInt(f.applyAsInt(start));
        while (slow != fast) {
            slow = f.applyAsInt(slow);
            fast = f.applyAsInt(f.applyAsInt(fast));
        }
        int mu = 0;
        slow = start;
        while (slow != fast) {
            slow = f.applyAsInt(slow);
            fast = f.applyAsInt(fast);
            mu++;
        }
        int lam = 1;
        fast = f.applyAsInt(slow);
        while (slow != fast) {
            fast = f.applyAsInt(fast);
            lam++;
        }
        return new Drift(mu, lam);
    }

    public static Drift brent(IntUnaryOperator f, int start) {
        int power = 1;
        int lam = 1;
        int tortoise = start;
        int hare = f.applyAsInt(start);
        while (tortoise != hare) {
            if (power == lam) {
                tortoise = hare;
                power <<= 1;
                lam = 0;
            }
            hare = f.applyAsInt(hare);
            lam++;
        }
        tortoise = start;
        hare = start;
        for (int i = 0; i < lam; i++) {
            hare = f.applyAsInt(hare);
        }
        int mu = 0;
        while (tortoise != hare) {
            tortoise = f.applyAsInt(tortoise);
            hare = f.applyAsInt(hare);
            mu++;
        }
        return new Drift(mu, lam);
    }

    public static Drift drift(int[] map, int start) {
        if (start < 0 || start >= map.length) {
            throw new IllegalArgumentException("start out of range: " + start);
        }
        for (int v : map) {
            if (v < 0 || v >= map.length) {
                throw new IllegalArgumentException("current leaves the buoys: " + v);
            }
        }
        return brent(i -> map[i], start);
    }

    /** Quest q_current_loop: the navigator names lead-in and loop length of the cask's drift. */
    public static boolean quest(int[] map, int start, int leadIn, int loop) {
        return drift(map, start).equals(new Drift(leadIn, loop));
    }
}