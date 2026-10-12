// SPDX-License-Identifier: MIT

package com.daedalus.world.crafting;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Pure station crafting: validate and preflight every quantity before producing a new inventory.
 * Hosts provide recipes and handle timing, capacity policy and committing successful results. */
public final class Crafting {
    private Crafting() { }

    public static CraftResult craft(Recipe recipe, Map<String, Integer> inventory, String station) {
        return craft(recipe, inventory, station, 1);
    }

    public static CraftResult craft(Recipe recipe, Map<String, Integer> inventory, String station, int batches) {
        if (recipe == null) throw new IllegalArgumentException("recipe must not be null");
        station = Recipe.requireId(station, "station");
        if (batches <= 0) throw new IllegalArgumentException("batches must be positive");
        Map<String, Integer> original = snapshot(inventory, true);
        if (!recipe.station().equals(station)) {
            return result(CraftResult.Status.WRONG_STATION, recipe, batches, original, Map.of());
        }

        Map<String, Integer> inputs;
        Map<String, Integer> outputs;
        try {
            inputs = scaled(recipe.inputs(), batches);
            outputs = scaled(recipe.outputs(), batches);
        } catch (ArithmeticException overflow) {
            return result(CraftResult.Status.OVERFLOW, recipe, batches, original, Map.of());
        }
        Map<String, Integer> missing = new LinkedHashMap<>();
        inputs.forEach((item, required) -> {
            int available = original.getOrDefault(item, 0);
            if (available < required) missing.put(item, required - available);
        });
        if (!missing.isEmpty()) {
            return result(CraftResult.Status.INSUFFICIENT_INGREDIENTS, recipe, batches, original, missing);
        }
        for (Map.Entry<String, Integer> output : outputs.entrySet()) {
            String item = output.getKey();
            long finalCount = (long) original.getOrDefault(item, 0) - inputs.getOrDefault(item, 0) + output.getValue();
            if (finalCount > Integer.MAX_VALUE) {
                return result(CraftResult.Status.OVERFLOW, recipe, batches, original, Map.of());
            }
        }

        Map<String, Integer> updated = new LinkedHashMap<>(original);
        inputs.forEach((item, required) -> {
            int remaining = original.getOrDefault(item, 0) - required;
            if (remaining == 0) updated.remove(item);
            else updated.put(item, remaining);
        });
        outputs.forEach((item, produced) -> updated.put(item, Math.addExact(updated.getOrDefault(item, 0), produced)));
        return result(CraftResult.Status.CRAFTED, recipe, batches, updated, Map.of());
    }

    static Map<String, Integer> snapshot(Map<String, Integer> inventory, boolean allowZero) {
        if (inventory == null) throw new IllegalArgumentException("quantities must not be null");
        Map<String, Integer> copy = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : inventory.entrySet()) {
            if (!(entry.getKey() instanceof String item)) {
                throw new IllegalArgumentException("item ids must be strings");
            }
            Recipe.requireId(item, "item");
            if (!(entry.getValue() instanceof Integer count) || count < 0 || (!allowZero && count == 0)) {
                throw new IllegalArgumentException("quantities must be " + (allowZero ? "nonnegative" : "positive") + " integers");
            }
            copy.put(item, count);
        }
        return Collections.unmodifiableMap(copy);
    }

    private static Map<String, Integer> scaled(List<Recipe.Component> components, int batches) {
        Map<String, Integer> quantities = new LinkedHashMap<>();
        components.forEach(component -> quantities.put(component.item(), Math.multiplyExact(component.n(), batches)));
        return quantities;
    }

    private static CraftResult result(CraftResult.Status status, Recipe recipe, int batches,
                                      Map<String, Integer> inventory, Map<String, Integer> missing) {
        return new CraftResult(status, recipe.id(), batches, inventory, missing);
    }
}
