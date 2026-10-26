// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

/** How the player picks the next enemy to shoot at. */
public enum TargetPolicy {
    /** The listed order: first unit that is still up. */
    FIRST_LISTED,
    /** The weakest unit that is still up (focus fire: fewest enemies as fast as possible). */
    LOWEST_HEALTH,
    /** The unit with the highest damage per second against the player. */
    HIGHEST_THREAT
}