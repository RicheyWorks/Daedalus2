// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Predicate;

/**
 * What bites in one body of water: an ordered list of {@link FishSpecies} and the weighted pick that decides which one
 * takes the hook. The pick is the browser demo's {@code pickFish} exactly (walk the table subtracting weights from
 * {@code u * total}), so a Java host and the Prismheart demo agree fish for fish given the same uniform draw. Immutable.
 */
public final class FishTable {

    private final String realm;
    private final List<FishSpecies> fish;

    public FishTable(String realm, List<FishSpecies> fish) {
        if (fish == null || fish.isEmpty()) {
            throw new IllegalArgumentException("a fish table needs at least one fish");
        }
        Set<String> seen = new HashSet<>();
        for (FishSpecies f : fish) {
            if (f == null) {
                throw new IllegalArgumentException("null fish in table");
            }
            if (!seen.add(f.name())) {
                throw new IllegalArgumentException("duplicate fish '" + f.name() + "'");
            }
        }
        this.realm = realm == null || realm.isBlank() ? "unknown" : realm;
        this.fish = List.copyOf(fish);
    }

    /** Reads a {@code daedalus.rpg-fish/v1} document such as {@code data/rpg/prism-fish.json}. */
    public static FishTable fromJson(String json) {
        return FishJson.table(json);
    }

    public String realm() {
        return realm;
    }

    /** The fish in table order. */
    public List<FishSpecies> fish() {
        return new ArrayList<>(fish);
    }

    public int size() {
        return fish.size();
    }

    public Optional<FishSpecies> find(String name) {
        for (FishSpecies f : fish) {
            if (f.name().equals(name)) {
                return Optional.of(f);
            }
        }
        return Optional.empty();
    }

    /** {@link #find} that fails loudly for a name not in the table. */
    public FishSpecies require(String name) {
        return find(name).orElseThrow(() -> new IllegalArgumentException("no fish '" + name + "' in the " + realm + " table"));
    }

    public double totalWeight(Conditions c) {
        double t = 0;
        for (FishSpecies f : fish) {
            t += c.weight(f);
        }
        return t;
    }

    /** Chance that the next bite is {@code name}, under {@code c}. */
    public double biteChance(String name, Conditions c) {
        return c.weight(require(name)) / totalWeight(c);
    }

    /** Bite chance of every fish, in table order. */
    public Map<String, Double> biteOdds(Conditions c) {
        double tot = totalWeight(c);
        Map<String, Double> out = new LinkedHashMap<>();
        for (FishSpecies f : fish) {
            out.put(f.name(), c.weight(f) / tot);
        }
        return out;
    }

    /**
     * The fish a uniform draw {@code u} in [0, 1) hooks under {@code c}.
     *
     * @throws IllegalArgumentException if {@code u} is outside [0, 1)
     */
    public FishSpecies pick(double u, Conditions c) {
        if (!(u >= 0 && u < 1)) {
            throw new IllegalArgumentException("pick needs u in [0, 1), got " + u);
        }
        double r = u * totalWeight(c);
        for (FishSpecies f : fish) {
            r -= c.weight(f);
            if (r < 0) {
                return f;
            }
        }
        return fish.get(fish.size() - 1);
    }

    /** The fish {@code keep} accepts, in order, or empty when none are left. */
    public Optional<FishTable> filter(Predicate<FishSpecies> keep) {
        List<FishSpecies> out = new ArrayList<>();
        for (FishSpecies f : fish) {
            if (keep.test(f)) {
                out.add(f);
            }
        }
        return out.isEmpty() ? Optional.empty() : Optional.of(new FishTable(realm, out));
    }
}
