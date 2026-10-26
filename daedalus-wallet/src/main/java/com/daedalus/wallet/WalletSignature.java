// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import org.web3j.crypto.Keys;
import org.web3j.crypto.Sign;
import org.web3j.utils.Numeric;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.SignatureException;
import java.util.Arrays;
import java.util.Optional;

/**
 * Recovers who signed an Ethereum {@code personal_sign} payload (ported from ComputerPets
 * {@code com.enterprisepet.nft.WalletSignature}). A wallet address is only an identity once its
 * holder has signed something the server chose — here, a Sign-In with Ethereum message.
 */
public final class WalletSignature {

    private WalletSignature() {
    }

    /**
     * @param message      the exact UTF-8 string that was signed
     * @param signatureHex 65-byte {@code 0x}-prefixed r‖s‖v signature
     * @return lowercase {@code 0x} address of the signer, or empty on any parse or crypto failure
     */
    public static Optional<String> recoverAddress(String message, String signatureHex) {
        if (message == null || message.isBlank() || signatureHex == null || signatureHex.isBlank()) {
            return Optional.empty();
        }
        try {
            Optional<Sign.SignatureData> data = parse(signatureHex);
            if (data.isEmpty()) {
                return Optional.empty();
            }
            BigInteger pub = Sign.signedPrefixedMessageToKey(message.getBytes(StandardCharsets.UTF_8), data.get());
            return Optional.of("0x" + Keys.getAddress(pub));
        } catch (SignatureException | RuntimeException e) {
            return Optional.empty();
        }
    }

    /** r‖s‖v from 65 bytes; v 0/1 is accepted as 27/28. Empty for any other shape. */
    static Optional<Sign.SignatureData> parse(String signatureHex) {
        String hex = signatureHex.trim();
        if (!hex.matches("^0x[0-9a-fA-F]{130}$")) {
            return Optional.empty();
        }
        byte[] sig = Numeric.hexStringToByteArray(hex);
        byte v = sig[64];
        if (v < 27) {
            v += 27;
        }
        if (v != 27 && v != 28) {
            return Optional.empty();
        }
        return Optional.of(new Sign.SignatureData(v, Arrays.copyOfRange(sig, 0, 32), Arrays.copyOfRange(sig, 32, 64)));
    }

    /** The 65-byte hex form a wallet returns, for a signature made here (tests, vouchers). */
    static String toHex(Sign.SignatureData sig) {
        byte[] out = new byte[65];
        System.arraycopy(sig.getR(), 0, out, 0, 32);
        System.arraycopy(sig.getS(), 0, out, 32, 32);
        out[64] = sig.getV()[0];
        return Numeric.toHexString(out);
    }
}
