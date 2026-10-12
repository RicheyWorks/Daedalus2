// SPDX-License-Identifier: MIT

package com.daedalus.world.crafting;

import java.util.Map;

/** An immutable outcome and inventory snapshot; callers own committing it to their world. */
public record CraftResult(Status status, String recipeId, int batches,
                          Map<String, Integer> inventory, Map<String, Integer> missing) {

    public enum Status {
        CRAFTED, WRONG_STATION, INSUFFICIENT_INGREDIENTS, OVERFLOW
    }

    public CraftResult {
        if (status == null) throw new IllegalArgumentException("status must not be null");
        recipeId = Recipe.requireId(recipeId, "recipe id");
        if (batches <= 0) throw new IllegalArgumentException("batches must be positive");
        inventory = Crafting.snapshot(inventory, true);
        missing = Crafting.snapshot(missing, false);
        boolean hasShortages = !missing.isEmpty();
        if ((status == Status.INSUFFICIENT_INGREDIENTS) != hasShortages) {
            throw new IllegalArgumentException("only insufficient ingredients must report missing quantities");
        }
    }

    public boolean success() {
        return status == Status.CRAFTED;
    }
}
