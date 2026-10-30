// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * A signed permission to mint one island deed (ADR-028): pass {@code (to, slot, seed, radius,
 * deadline)} and {@code signature} to {@code RealmIslands.mint} on {@code chainId} at {@code contract}.
 * {@code seed} is a decimal string: it is a uint64 and does not fit a JavaScript number.
 */
public record DeedVoucherResponse(String to, int slot, String seed, int radius, long deadline, long chainId,
                                  String contract, String signature) {
}
