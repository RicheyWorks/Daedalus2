// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cellar;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.PitchTable;
import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * How long food keeps in the root cellar, and what each way of keeping it costs. Fresh food spoils in days; salt
 * (boiled from the sea), smoke, sun and brine keep it for weeks. Island herbs (the twelve of the
 * {@link PitchTable#ISLAND_CANON}) keep three days fresh and thirty dried.
 */
public final class Preserve {
    public static final String SALT = "salt";
    public static final int HERB_FRESH = 3;
    public static final int HERB_DRIED = 30;

    /** Ways to keep food. FRESH is a jar with nothing done to it. */
    public enum Method { FRESH, SALT, SMOKE, DRY, PICKLE }

    /** Shelf life in days per item and method (absent = that method does not work for that item). */
    public static final Map<String, Map<Method, Integer>> SHELF_DAYS = table();

    private Preserve() {
    }

    private static Map<String, Map<Method, Integer>> table() {
        Map<String, Map<Method, Integer>> m = new LinkedHashMap<>();
        m.put("fish", days(2, 40, 20, 0, 0));
        m.put("Egg", days(6, 0, 0, 0, 25));
        m.put("Bacon", days(3, 30, 25, 0, 0));
        m.put("Milk", days(2, 0, 0, 0, 0));
        m.put("Groat", days(60, 0, 0, 0, 0));
        m.put("Spudlet", days(20, 0, 0, 0, 0));
        m.put("Bitroot", days(12, 0, 0, 0, 30));
        m.put("Moonbean", days(5, 0, 0, 30, 0));
        return Collections.unmodifiableMap(m);
    }

    private static Map<Method, Integer> days(int fresh, int salt, int smoke, int dry, int pickle) {
        Map<Method, Integer> d = new EnumMap<>(Method.class);
        d.put(Method.FRESH, fresh);
        if (salt > 0) {
            d.put(Method.SALT, salt);
        }
        if (smoke > 0) {
            d.put(Method.SMOKE, smoke);
        }
        if (dry > 0) {
            d.put(Method.DRY, dry);
        }
        if (pickle > 0) {
            d.put(Method.PICKLE, pickle);
        }
        return Collections.unmodifiableMap(d);
    }

    /** True for one of the twelve island herbs. */
    public static boolean isHerb(String item) {
        return PitchTable.ISLAND_CANON.pitchOf(item).isPresent();
    }

    /** Days the item keeps when kept this way; 0 when the method does not work for it. */
    public static int shelfDays(String item, Method method) {
        if (item == null || method == null) {
            return 0;
        }
        if (isHerb(item)) {
            return method == Method.FRESH ? HERB_FRESH : method == Method.DRY ? HERB_DRIED : 0;
        }
        Map<Method, Integer> d = SHELF_DAYS.get(item);
        return d == null ? 0 : d.getOrDefault(method, 0);
    }

    /** Store items one jar of this method uses besides the food: salt for SALT, salt and clean water for PICKLE. */
    public static Map<String, Integer> cost(Method method) {
        return switch (method) {
            case SALT -> Map.of(SALT, 1);
            case PICKLE -> Map.of(SALT, 1, BrewBench.WATER, 1);
            default -> Map.of();
        };
    }

    /** Jars per day the rack or smokehouse takes for this method; 0 = no daily limit. */
    public static int perDay(Method method) {
        return switch (method) {
            case SMOKE -> 2;
            case DRY -> 3;
            default -> 0;
        };
    }
}
