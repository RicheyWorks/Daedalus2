// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/** Named outcome of ordering an ark to sail. Never silent success. */
public enum VoyageResult {
    /** The ark left its berth; the voyage is underway. */
    SAILING,
    /** The ark is already moored at that island. */
    ALREADY_THERE,
    /** The ark is mid-voyage; it takes new orders once it arrives. */
    UNDERWAY,
    /** No island is raised in that slot. */
    NO_SUCH_ISLAND
}
