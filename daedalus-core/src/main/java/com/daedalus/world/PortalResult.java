// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable portal outcomes. Silence is not success — already-open is a result.
 */
public enum PortalResult {
    OPENED,
    SEALED,
    ALREADY_OPEN,
    ALREADY_SEALED,
    DENIED
}
