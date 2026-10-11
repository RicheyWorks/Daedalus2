// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * What a client needs to sign in and mint (ADR-028): the chain, the deed contract (empty until it is
 * deployed) and the address the realm signs vouchers with (empty when vouchers are off).
 */
public record WalletConfigResponse(long chainId, String deedContract, String deedSigner, boolean deeds) {
}
