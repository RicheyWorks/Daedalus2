// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;
import java.util.TreeMap;

/**
 * What an ark carries (ADR-023). After the Shattering the arks are how walkers, burrowers and
 * swimmers reach another island: anything that cannot cross open sky alone rides in a hold.
 *
 * <p><b>Founders.</b> Every ark is launched with {@link #FOUNDER_KINDS} kinds, a pair of each —
 * two of every kind — drawn from the canon by its island's seed. Only kinds that need an ark are
 * drawn (non-dispersers, never MARINE: the sea fell away), weighted by rarity, so a legendary in
 * the hold is a real event.
 *
 * <p><b>Stowaways.</b> When an ark casts off, every kind on the island it leaves that is
 * {@link #BOARD_MIN} strong has a {@link #BOARD_CHANCE} chance of sending a pair aboard, up to
 * {@link #CAPACITY} kinds in the hold. Wings board too: a bird in a hold crosses faster than it
 * would drift.
 *
 * <p><b>Landing.</b> When an ark ties up, every kind in the hold steps off onto the island if the
 * island has room for its guild; a pond kind bound for a dry island stays aboard for the next one.
 *
 * <p>Deterministic: every choice is one {@code SplittableRandom(seed)} drawn in key order.
 */
public final class Hold {

    public static final int FOUNDER_KINDS = 6;
    public static final double PAIR = 2.0;
    public static final double BOARD_MIN = 6.0;
    public static final double BOARD_CHANCE = 0.25;
    public static final int CAPACITY = 12;

    private final TreeMap<String, Double> cargo = new TreeMap<>();

    public Map<String, Double> cargo() {
        return Collections.unmodifiableMap(cargo);
    }

    public boolean isEmpty() {
        return cargo.isEmpty();
    }

    /** Rarity weight: how much more often a kind is drawn than a legendary. */
    public static int weight(String rarity) {
        return switch (rarity) {
            case "COMMON" -> 8;
            case "UNCOMMON" -> 4;
            case "RARE" -> 2;
            default -> 1; // LEGENDARY
        };
    }

    /** True for kinds an ark is the only way to move: earthbound and not of the sea. */
    public static boolean needsArk(Species s) {
        return !s.disperses() && s.guild() != Guild.MARINE;
    }

    /** The founders an ark launched from an island of this seed carries: a pair of each kind. */
    public static Hold founders(long seed, SpeciesCanon canon) {
        List<Species> pool = new ArrayList<>();
        for (Species s : canon.all()) {
            if (needsArk(s)) {
                pool.add(s);
            }
        }
        Hold hold = new Hold();
        SplittableRandom rng = new SplittableRandom(seed ^ 0xA2C0FFEEL);
        while (hold.cargo.size() < FOUNDER_KINDS && hold.cargo.size() < pool.size()) {
            int total = 0;
            for (Species s : pool) {
                if (!hold.cargo.containsKey(s.key())) {
                    total += weight(s.rarity());
                }
            }
            int pick = rng.nextInt(total);
            for (Species s : pool) {
                if (hold.cargo.containsKey(s.key())) {
                    continue;
                }
                pick -= weight(s.rarity());
                if (pick < 0) {
                    hold.cargo.put(s.key(), PAIR);
                    break;
                }
            }
        }
        return hold;
    }

    /** Stowaways board from the island the ark is leaving. Returns the kinds that boarded. */
    public List<String> board(Community from, long seed) {
        List<String> boarded = new ArrayList<>();
        SplittableRandom rng = new SplittableRandom(seed);
        for (Map.Entry<String, Double> e : new TreeMap<>(from.abundance()).entrySet()) {
            boolean roll = rng.nextDouble() < BOARD_CHANCE;
            if (e.getValue() < BOARD_MIN || !roll) {
                continue;
            }
            if (!cargo.containsKey(e.getKey()) && cargo.size() >= CAPACITY) {
                continue;
            }
            from.put(e.getKey(), e.getValue() - PAIR);
            cargo.merge(e.getKey(), PAIR, Double::sum);
            boarded.add(e.getKey());
        }
        return boarded;
    }

    /** Everything that can live on the island steps off. Returns the kinds that landed. */
    public List<String> land(Community to, Habitat habitat, SpeciesCanon canon) {
        List<String> landed = new ArrayList<>();
        for (Map.Entry<String, Double> e : new TreeMap<>(cargo).entrySet()) {
            if (to.arrive(canon.byKey(e.getKey()), e.getValue(), habitat) > 0) {
                cargo.remove(e.getKey());
                landed.add(e.getKey());
            }
        }
        return landed;
    }

    /** Set a count directly (restoring from disk). Zero or less removes the kind. */
    public void put(String key, double n) {
        if (n > 0) {
            cargo.put(key, n);
        } else {
            cargo.remove(key);
        }
    }
}
