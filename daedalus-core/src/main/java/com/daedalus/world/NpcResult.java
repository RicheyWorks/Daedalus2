// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable NPC outcomes. Silence is not success — already-speaking is a result.
 */
public enum NpcResult {
    SPOKE,
    HUSHED,
    ALREADY_SPEAKING,
    ALREADY_IDLE
}
