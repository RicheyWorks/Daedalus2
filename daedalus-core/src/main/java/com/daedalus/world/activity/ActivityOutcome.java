// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

/** Terminal outcome of one activity session. Only COMPLETED and FAILED can carry an award. */
public enum ActivityOutcome {
    COMPLETED(true), FAILED(true), ABANDONED(false), DISCONNECTED(false);

    private final boolean settleable;

    ActivityOutcome(boolean settleable) { this.settleable = settleable; }

    /** True when an accepted award policy may settle this outcome; abandonment and disconnects never pay. */
    public boolean settleable() { return settleable; }
}
