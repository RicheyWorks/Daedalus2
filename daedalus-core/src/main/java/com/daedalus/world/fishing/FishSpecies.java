// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/**
 * One kind of fish, as a fish table describes it (schema {@code daedalus.rpg-fish/v1}, e.g. {@code data/rpg/prism-fish.json}).
 * {@code weight} is how often it bites relative to the rest; {@code nightWeight} (0 = none) replaces it between dusk and
 * dawn; {@code windowSeconds} is how long the bite lasts before it gets away. The optional sky-island fields say where and
 * when it lives: {@code seasons} (empty = all year), {@code spots} (empty = a native lake fish that any spot on its island
 * can hook; otherwise a visitor found only at those spots) and {@code duskOnly}.
 */
public final class FishSpecies {

    private final String name;
    private final Rarity rarity;
    private final double weight;
    private final double nightWeight;
    private final double windowSeconds;
    private final String effect;
    private final int price;
    private final String note;
    private final Set<String> seasons;
    private final Set<String> spots;
    private final boolean duskOnly;

    public FishSpecies(String name, Rarity rarity, double weight, double nightWeight, double windowSeconds, String effect,
                       int price, String note, Collection<String> seasons, Collection<String> spots, boolean duskOnly) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("fish name is missing");
        }
        this.name = name;
        this.rarity = Objects.requireNonNull(rarity, "rarity");
        if (!(weight > 0) || Double.isInfinite(weight)) {
            throw new IllegalArgumentException(name + ": weight must be a positive number, got " + weight);
        }
        if (!(nightWeight >= 0) || Double.isInfinite(nightWeight)) {
            throw new IllegalArgumentException(name + ": night weight must be >= 0 (0 = none), got " + nightWeight);
        }
        if (!(windowSeconds > 0) || Double.isInfinite(windowSeconds)) {
            throw new IllegalArgumentException(name + ": bite window must be positive seconds, got " + windowSeconds);
        }
        if (price < 0) {
            throw new IllegalArgumentException(name + ": price must be >= 0, got " + price);
        }
        this.weight = weight;
        this.nightWeight = nightWeight;
        this.windowSeconds = windowSeconds;
        this.effect = effect == null ? "" : effect;
        this.price = price;
        this.note = note == null ? "" : note;
        this.seasons = words(seasons);
        this.spots = words(spots);
        this.duskOnly = duskOnly;
    }

    /** A plain pond fish: no night weight, all year, every spot. */
    public static FishSpecies of(String name, Rarity rarity, double weight, double windowSeconds, int price) {
        return new FishSpecies(name, rarity, weight, 0, windowSeconds, "", price, "", List.of(), List.of(), false);
    }

    private static Set<String> words(Collection<String> in) {
        Set<String> out = new TreeSet<>();
        if (in != null) {
            for (String w : in) {
                if (w == null || w.isBlank()) {
                    throw new IllegalArgumentException("blank season or spot");
                }
                out.add(w.trim().toLowerCase(Locale.ROOT));
            }
        }
        return out;
    }

    public String name() {
        return name;
    }

    public Rarity rarity() {
        return rarity;
    }

    public double weight() {
        return weight;
    }

    public double nightWeight() {
        return nightWeight;
    }

    public double windowSeconds() {
        return windowSeconds;
    }

    public String effect() {
        return effect;
    }

    public int price() {
        return price;
    }

    public String note() {
        return note;
    }

    /** Seasons it bites in, sorted; empty means all year. A copy. */
    public List<String> seasons() {
        return new ArrayList<>(seasons);
    }

    /** Spots it visits, sorted; empty means a native fish of its island's water. A copy. */
    public List<String> spots() {
        return new ArrayList<>(spots);
    }

    public boolean duskOnly() {
        return duskOnly;
    }

    /** True when it feeds differently at night. */
    public boolean feedsAtNight() {
        return nightWeight > 0;
    }

    /** The bite weight that applies by day or by night (the demo's {@code (isNight() && night_weight) || weight}). */
    public double weightAt(boolean night) {
        return night && nightWeight > 0 ? nightWeight : weight;
    }

    /** True when it bites in {@code season} (always, for an all-year fish). */
    public boolean inSeason(String season) {
        return seasons.isEmpty() || seasons.contains(season.toLowerCase(Locale.ROOT));
    }

    /** True for a native lake fish (no spot list). */
    public boolean isNative() {
        return spots.isEmpty();
    }

    /** True when this visitor fish is found at {@code spot}. Native fish answer false: they come from the island. */
    public boolean visits(String spot) {
        return spots.contains(spot.toLowerCase(Locale.ROOT));
    }

    @Override
    public String toString() {
        return name + " (" + rarity + ")";
    }
}
