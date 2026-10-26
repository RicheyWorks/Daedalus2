// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import org.web3j.crypto.Credentials;

/**
 * The realm's deed-voucher key (ADR-028). It holds no funds and signs nothing but {@link DeedVoucher}s;
 * rotating it is {@code RealmIslands.setSigner}. The key never leaves this object: {@link #toString()}
 * shows only the address.
 */
public final class DeedSigner {

    private final Credentials credentials;

    private DeedSigner(Credentials credentials) {
        this.credentials = credentials;
    }

    /** From a 32-byte hex private key, with or without 0x. */
    public static DeedSigner fromHex(String privateKeyHex) {
        if (privateKeyHex == null || !privateKeyHex.trim().matches("^(0x)?[0-9a-fA-F]{64}$")) {
            throw new IllegalArgumentException("deed signer key must be 32 bytes of hex");
        }
        return new DeedSigner(Credentials.create(privateKeyHex.trim()));
    }

    /** EIP-55 address of the key: what {@code RealmIslands.signer()} must be. */
    public String address() {
        return EthereumAddress.checksummed(credentials.getAddress());
    }

    public String sign(DeedVoucher voucher) {
        return voucher.sign(credentials);
    }

    @Override
    public String toString() {
        return "DeedSigner[" + address() + "]";
    }
}
