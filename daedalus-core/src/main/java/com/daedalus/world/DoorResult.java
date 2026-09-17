// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable door outcomes. Silence is not success — already-open is a result.
 */
public enum DoorResult {
    OPENED,
    CLOSED,
    ALREADY_OPEN,
    ALREADY_CLOSED
}
