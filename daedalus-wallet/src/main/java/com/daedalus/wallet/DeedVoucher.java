// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import org.web3j.crypto.Credentials;
import org.web3j.crypto.Hash;
import org.web3j.crypto.Sign;
import org.web3j.utils.Numeric;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.Objects;

/**
 * A permission to mint one island deed (ADR-028), signed by the realm and redeemed on chain by
 * {@code RealmIslands.mint(Deed, signature)}. The realm only signs for the address that owns the
 * island's claim, so a deed on chain always starts with the realm's owner. Anyone may submit a
 * voucher, but the token goes only to {@code to}.
 *
 * <p>EIP-712, hashed here by hand so every byte can be checked against the contract:
 * <pre>
 * Deed(address to,uint256 slot,uint64 seed,uint8 radius,uint256 deadline)
 * domain: EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)
 *         name "RealmIslands", version "1"
 * </pre>
 * The seed travels as its unsigned 64-bit pattern: a negative Java seed and its uint64 twin grow the
 * same island.
 */
public record DeedVoucher(String to, int slot, long seed, int radius, long deadline, long chainId,
                          String contract) {

    public static final String NAME = "RealmIslands";
    public static final String VERSION = "1";
    static final String DEED_TYPE = "Deed(address to,uint256 slot,uint64 seed,uint8 radius,uint256 deadline)";
    static final String DOMAIN_TYPE =
            "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)";

    public DeedVoucher {
        to = EthereumAddress.normalize(to).orElseThrow(() -> new IllegalArgumentException("to must be an address"));
        contract = EthereumAddress.normalize(contract)
                .orElseThrow(() -> new IllegalArgumentException("contract must be an address"));
        if (slot < 0) {
            throw new IllegalArgumentException("slot must be >= 0");
        }
        if (radius < 0 || radius > 255) {
            throw new IllegalArgumentException("radius must fit uint8");
        }
        if (deadline < 1 || chainId < 1) {
            throw new IllegalArgumentException("deadline and chainId must be positive");
        }
    }

    public String seedUint64() {
        return Long.toUnsignedString(seed);
    }

    byte[] domainSeparator() {
        return Hash.sha3(concat(
                Hash.sha3(DOMAIN_TYPE.getBytes(StandardCharsets.UTF_8)),
                Hash.sha3(NAME.getBytes(StandardCharsets.UTF_8)),
                Hash.sha3(VERSION.getBytes(StandardCharsets.UTF_8)),
                word(BigInteger.valueOf(chainId)),
                word(Numeric.toBigInt(contract))));
    }

    byte[] structHash() {
        return Hash.sha3(concat(
                Hash.sha3(DEED_TYPE.getBytes(StandardCharsets.UTF_8)),
                word(Numeric.toBigInt(to)),
                word(BigInteger.valueOf(slot)),
                word(new BigInteger(seedUint64())),
                word(BigInteger.valueOf(radius)),
                word(BigInteger.valueOf(deadline))));
    }

    /** {@code keccak256("\x19\x01" ‖ domainSeparator ‖ structHash)}: what the signer signs. */
    public byte[] digest() {
        return Hash.sha3(concat(new byte[] {0x19, 0x01}, domainSeparator(), structHash()));
    }

    /** Sign with the realm's deed key; the 65-byte hex the contract's ECDSA.recover expects. */
    public String sign(Credentials signer) {
        Objects.requireNonNull(signer, "signer");
        Sign.SignatureData sig = Sign.signMessage(digest(), signer.getEcKeyPair(), false);
        return WalletSignature.toHex(sig);
    }

    /** Who signed this voucher, lowercase, or empty if the signature is malformed. */
    public java.util.Optional<String> signer(String signatureHex) {
        return WalletSignature.parse(signatureHex).flatMap(sig -> {
            try {
                return java.util.Optional.of("0x" + org.web3j.crypto.Keys.getAddress(
                        Sign.signedMessageHashToKey(digest(), sig)));
            } catch (java.security.SignatureException | RuntimeException e) {
                return java.util.Optional.empty();
            }
        });
    }

    private static byte[] word(BigInteger v) {
        return Numeric.toBytesPadded(v, 32);
    }

    private static byte[] concat(byte[]... parts) {
        int n = 0;
        for (byte[] p : parts) {
            n += p.length;
        }
        byte[] out = new byte[n];
        int at = 0;
        for (byte[] p : parts) {
            System.arraycopy(p, 0, out, at, p.length);
            at += p.length;
        }
        return out;
    }
}
