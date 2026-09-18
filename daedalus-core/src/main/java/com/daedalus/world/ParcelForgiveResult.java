// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable extra-forgive outcomes. Silence is not success. Actor ids
 * are account keys — never a wallet.
 */
public enum ParcelForgiveResult {
    FORGIVEN,
    NOT_DENIED,
    NO_PARCEL,
    UNKNOWN_VERB
}
