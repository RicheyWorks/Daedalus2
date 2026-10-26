// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.week;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.colony.PlotState;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The homestead stove: the recipes of {@code engines/unreal/ytm-island/food_water.json} ("food"), cooked from the plot
 * store. A recipe's {@code clean_water} is the store's {@link BrewBench#WATER}. A cooked meal restores 25 hunger,
 * +10 for each ingredient past the second, +10 more when a note-herb (an island-canon herb) is in the pot; capped
 * at 45 (food_water.json: "cooked restores hunger 25-45 (+herb tonic buff if a note-herb is used)").
 */
public final class Larder {
    public static final String CLEAN_WATER = "clean_water";
    public static final int BASE_RESTORE = 25;
    public static final int MAX_RESTORE = 45;

    /** food_water.json "food", in file order. */
    public static final Map<String, List<String>> RECIPES = recipes();

    private Larder() {
    }

    private static Map<String, List<String>> recipes() {
        Map<String, List<String>> m = new LinkedHashMap<>();
        m.put("Stew", List.of("Bacon", "Spudlet", CLEAN_WATER));
        m.put("Omelet", List.of("Egg", "Egg", "Fasage"));
        m.put("Pie", List.of("Pumplet", "Groat", "Egg"));
        m.put("Porridge", List.of("Groat", "Milk"));
        m.put("Roast", List.of("Bacon", "Gloryroot"));
        m.put("Soup", List.of("Kelpweed", "Bitroot", CLEAN_WATER));
        m.put("Salad", List.of("Clover", "Mimint", "Moonbean"));
        m.put("Bread", List.of("Groat", "Groat", CLEAN_WATER));
        return java.util.Collections.unmodifiableMap(m);
    }

    /** The cooked item a recipe makes, e.g. {@code Item_YTM_Food_Stew_Cooked}. */
    public static String cooked(String recipe) {
        return "Item_YTM_Food_" + recipe + "_Cooked";
    }

    /** Hunger a cooked recipe restores. */
    public static int restore(String recipe) {
        List<String> in = RECIPES.get(recipe);
        if (in == null) {
            return 0;
        }
        boolean noteHerb = in.stream().anyMatch(h -> PitchTable.ISLAND_CANON.pitchOf(h).isPresent());
        return Math.min(MAX_RESTORE, BASE_RESTORE + 10 * Math.max(0, in.size() - 2) + (noteHerb ? 10 : 0));
    }

    /** The recipe a cooked item came from, or null. */
    public static String recipeOf(String cookedItem) {
        for (String r : RECIPES.keySet()) {
            if (cooked(r).equals(cookedItem)) {
                return r;
            }
        }
        return null;
    }

    private static String storeItem(String ingredient) {
        return ingredient.equals(CLEAN_WATER) ? BrewBench.WATER : ingredient;
    }

    /** Cooks a recipe at the stove: takes every ingredient (or nothing) and adds the cooked meal. */
    public static boolean cook(String recipe, PlotState plot) {
        List<String> in = RECIPES.get(recipe);
        if (in == null || plot == null) {
            return false;
        }
        Map<String, Integer> need = new LinkedHashMap<>();
        in.forEach(i -> need.merge(storeItem(i), 1, Integer::sum));
        for (var e : need.entrySet()) {
            if (plot.count(e.getKey()) < e.getValue()) {
                return false;
            }
        }
        need.forEach((k, v) -> plot.take(k, v));
        plot.add(cooked(recipe), 1);
        return true;
    }
}
