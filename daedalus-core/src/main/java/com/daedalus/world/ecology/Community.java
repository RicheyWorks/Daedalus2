// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;
import java.util.SplittableRandom;
import java.util.TreeMap;

/**
 * The living things on one island, and one ecological day of change (ADR-022).
 *
 * <p><b>Growth</b> is logistic with competition inside a guild: every member of a guild draws on
 * the same habitat cells, so a species' growth is {@code r·N·(1 − F)} where F is how full its
 * guild is — the sum over members of N / K. K is the guild's cells times a density by body size
 * (tiny things pack in, large ones need room). r is 0.6 a day for r-selected kinds, 0.12 for
 * K-selected. A little seeded noise keeps populations from marching in lockstep.
 *
 * <p><b>Extinction</b> is demographic: a population below one individual is gone, and one below
 * {@link #FRAGILE} risks it each day with probability {@link #FRAGILE_LOSS} — so small islands,
 * whose populations stay small, lose kinds faster. That is MacArthur–Wilson's e/area, emerging
 * rather than typed in.
 *
 * <p>Deterministic: the day's noise comes from {@code SplittableRandom(seed)} drawn in key order.
 */
public final class Community {

    public static final double R_FAST = 0.6;
    public static final double R_SLOW = 0.12;
    public static final double FRAGILE = 3.0;
    public static final double FRAGILE_LOSS = 0.12;
    public static final double NOISE = 0.05;

    private final TreeMap<String, Double> abundance = new TreeMap<>();

    public Map<String, Double> abundance() {
        return Collections.unmodifiableMap(abundance);
    }

    public double count(String key) {
        return abundance.getOrDefault(key, 0.0);
    }

    /** Individuals per habitat cell, by body size. */
    public static double density(String size) {
        return switch (size) {
            case "TINY" -> 8.0;
            case "SMALL" -> 1.5;
            case "MEDIUM" -> 0.3;
            case "LARGE" -> 0.05;
            default -> 0.8; // SESSILE: rooted things
        };
    }

    public static double capacity(Species s, Habitat h) {
        return h.of(s.guild()) * density(s.size());
    }

    /** Land founders (from an ark's hold or drifting in). Unknown species and MARINE kinds cannot. */
    public double arrive(Species s, double n, Habitat h) {
        if (s == null || n <= 0 || capacity(s, h) <= 0) {
            return 0;
        }
        abundance.merge(s.key(), n, Double::sum);
        return n;
    }

    /** Set a count directly (restoring from disk). Zero or less removes the kind. */
    public void put(String key, double n) {
        if (n > 0) {
            abundance.put(key, n);
        } else {
            abundance.remove(key);
        }
    }

    /** One ecological day. Returns the kinds lost today. */
    public java.util.List<String> day(SpeciesCanon canon, Habitat h, long seed) {
        SplittableRandom rng = new SplittableRandom(seed);
        Map<Guild, Double> fullness = new EnumMap<>(Guild.class);
        for (Map.Entry<String, Double> e : abundance.entrySet()) {
            Species s = canon.byKey(e.getKey());
            double k = s == null ? 0 : capacity(s, h);
            fullness.merge(s == null ? Guild.MARINE : s.guild(), k > 0 ? e.getValue() / k : 1e9, Double::sum);
        }
        java.util.List<String> lost = new java.util.ArrayList<>();
        for (Map.Entry<String, Double> e : new TreeMap<>(abundance).entrySet()) {
            Species s = canon.byKey(e.getKey());
            double n = e.getValue();
            double next;
            if (s == null || capacity(s, h) <= 0) {
                next = 0;
            } else {
                double r = s.rSelected() ? R_FAST : R_SLOW;
                double f = fullness.get(s.guild());
                next = n + r * n * (1 - f);
                next *= 1 + NOISE * (rng.nextDouble() * 2 - 1);
                if (next < FRAGILE && rng.nextDouble() < FRAGILE_LOSS) {
                    next = 0;
                }
            }
            if (next < 1) {
                abundance.remove(e.getKey());
                lost.add(e.getKey());
            } else {
                abundance.put(e.getKey(), next);
            }
        }
        return lost;
    }

    public Diversity diversity() {
        return Diversity.of(abundance);
    }
}
