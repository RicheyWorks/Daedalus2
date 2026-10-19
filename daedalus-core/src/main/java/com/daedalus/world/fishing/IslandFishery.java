// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;

/**
 * Sky-island fishing spots (ADR-066 colony ledger): what bites at a lake, stream, pier, sky river or ocean basin of one
 * island, in a season, at an hour. The island's seed chemistry decides its native lake fish ({@code water.fish} in
 * {@code tools/blender/island_chemistry.py}); visitor fish come with the spot (the sky river's dusk eel, the basin ray).
 * Bites only come in the morning and evening rise (06-10, 17-21), the same rule as {@code ColonyLedger.fishing}.
 */
public final class IslandFishery {

    public static final List<String> SPOTS = List.of("lake", "stream", "pier", "sky_river", "ocean_basin");
    public static final List<String> SEASONS = List.of("spring", "summer", "autumn", "winter");

    private IslandFishery() {
    }

    /** True in the morning (06-10) and evening (17-21) rise. */
    public static boolean biting(int hour) {
        return (hour >= 6 && hour <= 10) || (hour >= 17 && hour <= 21);
    }

    /** True in the evening rise (17-21), when dusk-only fish come up. */
    public static boolean dusk(int hour) {
        return hour >= 17 && hour <= 21;
    }

    /**
     * The table for one spot: the island's native fish that are in season, plus visitors of this spot (dusk-only ones
     * only at dusk). Empty outside the rise, or when nothing is left.
     *
     * @param catalog    every sky-island fish (e.g. {@code data/rpg/skyisland-fish.json})
     * @param islandFish the island chemistry's native lake fish
     */
    public static Optional<FishTable> at(FishTable catalog, Collection<String> islandFish, String spot, String season,
                                         int hour) {
        String sp = known(spot, SPOTS, "spot");
        String se = known(season, SEASONS, "season");
        if (hour < 0 || hour > 23) {
            throw new IllegalArgumentException("hour must be 0-23, got " + hour);
        }
        Set<String> natives = new TreeSet<>(islandFish == null ? List.of() : islandFish);
        for (String n : natives) {
            if (!catalog.require(n).isNative()) {
                throw new IllegalArgumentException("'" + n + "' is a visitor fish, not an island's lake fish");
            }
        }
        if (!biting(hour)) {
            return Optional.empty();
        }
        return catalog.filter(f -> f.inSeason(se)
                && (natives.contains(f.name()) || (f.visits(sp) && (!f.duskOnly() || dusk(hour)))));
    }

    /**
     * Native fish for an island seed, when no chemistry record is at hand: {@code count} distinct native fish from the
     * catalog, chosen by the {@link OddsRng} stream of the seed, sorted. Deterministic in Java; a host that has the
     * island's chemistry JSON should pass its {@code water.fish} list to {@link #at} instead.
     */
    public static List<String> nativeFish(FishTable catalog, long islandSeed, int count) {
        List<String> pool = new ArrayList<>();
        for (FishSpecies f : catalog.fish()) {
            if (f.isNative()) {
                pool.add(f.name());
            }
        }
        if (count < 0 || count > pool.size()) {
            throw new IllegalArgumentException("can pick 0-" + pool.size() + " native fish, asked for " + count);
        }
        OddsRng rng = new OddsRng(islandSeed);
        for (int i = 0; i < count; i++) {
            int j = i + (int) (rng.nextDouble() * (pool.size() - i));
            Collections.swap(pool, i, j);
        }
        List<String> out = new ArrayList<>(pool.subList(0, count));
        Collections.sort(out);
        return out;
    }

    private static String known(String word, List<String> allowed, String what) {
        String w = word == null ? "" : word.trim().toLowerCase(Locale.ROOT);
        if (!allowed.contains(w)) {
            throw new IllegalArgumentException("unknown " + what + " '" + word + "', expected one of " + allowed);
        }
        return w;
    }
}
