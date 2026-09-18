// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable extra-grant outcomes. Silence is not success. Actor ids
 * are account keys — never a wallet.
 */
public enum ParcelGrantResult {
    GRANTED,
    ALREADY_GRANTED,
    NO_PARCEL,
    UNKNOWN_VERB
}
