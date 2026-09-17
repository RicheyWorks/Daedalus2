// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable parcel lease outcomes. Silence is not success — the same
 * lease string is a result. Not a wallet and not a chain receipt.
 */
public enum ParcelLeaseResult {
    LEASED,
    ALREADY_LEASED
}
