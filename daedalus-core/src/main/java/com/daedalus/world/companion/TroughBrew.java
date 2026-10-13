// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import com.daedalus.world.companion.TonicBook.Recipe;

/**
 * A brew sitting in a Brew_Trough. It is spent after the book's decay drink count, or goes flat after the
 * decay minutes, whichever comes first. Time is passed in by the caller (game seconds), so it stays deterministic.
 */
public final class TroughBrew {
    private final Recipe recipe;
    private final long brewedAtSec;
    private final long flatAtSec;
    private int drinksLeft;

    /** Starts a brew at {@code nowSec}. */
    public TroughBrew(TonicBook book, Recipe recipe, long nowSec) {
        this.recipe = recipe;
        this.brewedAtSec = nowSec;
        this.flatAtSec = nowSec + book.decayMinutes() * 60L;
        this.drinksLeft = book.decayDrinks();
    }

    /** True while the brew can still be drunk at {@code nowSec}. */
    public boolean drinkable(long nowSec) {
        return drinksLeft > 0 && nowSec >= brewedAtSec && nowSec < flatAtSec;
    }

    /** Takes one drink; returns false (and changes nothing) when spent or flat. */
    public boolean drink(long nowSec) {
        if (!drinkable(nowSec)) {
            return false;
        }
        drinksLeft--;
        return true;
    }

    /** Drinks remaining. */
    public int drinksLeft() {
        return drinksLeft;
    }

    /** The tonic in the trough. */
    public Recipe recipe() {
        return recipe;
    }
}
