// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Observable extra-revoke outcomes. Silence is not success. Actor ids
 * are account keys — never a wallet.
 */
public enum ParcelRevokeResult {
    REVOKED,
    NOT_GRANTED,
    NO_PARCEL,
    UNKNOWN_VERB
}
