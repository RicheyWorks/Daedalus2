// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The day-book tables of {@code tools/economy/colony_ledger.py} (ADR-066), copied in the same order, because the
 * seeded draws depend on order. If the Python tables change, regenerate the parity fixture
 * ({@code tools/economy/daybook_parity.py}) and {@code DayBookParityTest} shows what moved.
 */
public final class ColonyTables {
    private ColonyTables() {
    }

    public static final Map<String, List<String>> FISH_SEASON = ordered(
            "rillperch", List.of("spring", "summer"), "glassfin", List.of("summer", "autumn"),
            "skytrout", List.of("autumn", "winter"), "ember_koi", List.of("winter", "spring"));

    public static final Map<Integer, List<String>> BUGS_BY_SERAL = Map.of(
            0, List.of("fireweed_moth", "yarrow_beetle"), 1, List.of("meadow_bee", "blue_butterfly"),
            2, List.of("scrub_cricket", "hen_thief_wasp"), 3, List.of("stag_beetle", "oak_lanternfly"));

    public static final List<String> FOSSILS = List.of("shard_fossil", "ammonite", "starmetal_shard", "old_ark_plank");

    /** Cast role -> what that NPC asks for on the news board (insertion order kept; sorted() is applied by callers). */
    public static final Map<String, List<String>> NPC_WANTS = ordered(
            "Baker", List.of("wheat", "egg", "milk"), "Cook", List.of("carrot", "cabbage", "egg"),
            "Smith", List.of("iron", "copper", "coal"), "Miner", List.of("coal", "plank"),
            "Herbalist", List.of("dawnleaf", "rillprism", "cinderbud", "stillmoss", "stridefern", "clearbell"),
            "Apothecary", List.of("clearbell", "stillmoss", "honey"), "Healer", List.of("honey", "clearbell"),
            "Jeweller", List.of("gold", "crystal", "silver"), "Tinker", List.of("gearbox", "rotor", "copper"),
            "Carpenter", List.of("plank"), "Farmer", List.of("wheat", "corn"), "Shepherd", List.of("wool"),
            "Miller", List.of("wheat"), "Innkeeper", List.of("apple", "cherry", "plum", "egg", "milk"),
            "Fisher", List.of("rillperch", "glassfin", "skytrout", "ember_koi"), "Weaver", List.of("wool"),
            "Tailor", List.of("wool"), "Keymaker", List.of("iron", "gold"), "DragonKeeper", List.of("coal", "gold"),
            "UnicornGuide", List.of("clearbell", "dawnleaf", "apple"), "UnicornMedic", List.of("stillmoss", "honey"),
            "UnicornQuestgiver", List.of("rillprism", "clearbell", "starmetal"), "UnicornSentinel", List.of("crystal"),
            "RainbowWarden", List.of("crystal", "gold"), "WellKeeper", List.of("plank", "iron"),
            "King", List.of("gold", "starmetal"), "Queen", List.of("cherry", "crystal"), "Steward", List.of("wheat", "gold"));

    private static final Set<String> ORE = Set.of("coal", "copper", "iron", "gold", "starmetal", "silver", "tin", "cobalt");
    private static final Set<String> CRYSTAL = Set.of("crystal", "crystal2", "geode");
    private static final Set<String> ENERGY = Set.of("energy", "rotor", "gearbox", "battery", "shaft", "torch_oil", "plane_fuel");

    /** M.U.L.E. price family of an item: ORE, CRYSTAL, ENERGY or FOOD (everything else). */
    public static String familyOf(String item) {
        if (ORE.contains(item)) {
            return "ORE";
        }
        if (CRYSTAL.contains(item)) {
            return "CRYSTAL";
        }
        if (ENERGY.contains(item)) {
            return "ENERGY";
        }
        return "FOOD";
    }

    @SuppressWarnings("unchecked")
    private static <K, V> Map<K, V> ordered(Object... kv) {
        Map<K, V> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((K) kv[i], (V) kv[i + 1]);
        }
        return Collections.unmodifiableMap(m);
    }
}
