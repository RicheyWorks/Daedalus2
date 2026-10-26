// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable parcel release outcomes. Silence is not success. Lease ids
 * are account keys — never a wallet.
 */
public enum ParcelReleaseResult {
    RELEASED,
    NOT_LEASED,
    NO_PARCEL
}
