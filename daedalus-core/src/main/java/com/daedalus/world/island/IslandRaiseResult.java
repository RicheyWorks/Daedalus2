// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

/** Named outcome of raising an island. Never silent success. */
public enum IslandRaiseResult {
    /** Every cube of the plan is now in the world. */
    RAISED,
    /** At least one target cube already held matter; nothing was placed. */
    OVERLAP
}
