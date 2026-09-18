// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable trap outcomes. Silence is not success — already-armed is a result.
 */
public enum TrapResult {
    ARMED,
    DISARMED,
    ALREADY_ARMED,
    ALREADY_DISARMED,
    DENIED
}
