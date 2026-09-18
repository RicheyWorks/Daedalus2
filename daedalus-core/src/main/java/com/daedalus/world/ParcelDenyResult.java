// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable extra-deny outcomes. Silence is not success. Actor ids
 * are account keys — never a wallet.
 */
public enum ParcelDenyResult {
    DENIED,
    ALREADY_DENIED,
    NO_PARCEL
}
