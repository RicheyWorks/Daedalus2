// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Wallet sign-in and island deeds (ADR-028), bound from {@code daedalus.wallet.*}. Off by default:
 * with {@code enabled=false} none of the wallet routes exist.
 *
 * @param enabled         mount the wallet routes
 * @param domain          host[:port] players reach the realm on; a sign-in message must name it
 * @param uri             the realm's URL, shown in the message the wallet asks its holder to sign
 * @param chainId         the chain sign-in and deeds are for (Sepolia 11155111 by default)
 * @param deedContract    the RealmIslands contract; empty until it is deployed
 * @param deedSignerKey   hex private key the realm signs deed vouchers with; holds no funds. Empty
 *                        disables vouchers. A secret: set it from the environment, never in a file
 * @param voucherMinutes  how long a voucher stays redeemable
 */
@ConfigurationProperties("daedalus.wallet")
public record WalletProperties(boolean enabled, String domain, String uri, long chainId, String deedContract,
                               String deedSignerKey, int voucherMinutes) {

    public WalletProperties {
        domain = domain == null || domain.isBlank() ? "localhost:8088" : domain.trim();
        uri = uri == null || uri.isBlank() ? "http://" + domain : uri.trim();
        chainId = chainId <= 0 ? 11_155_111L : chainId;
        deedContract = deedContract == null ? "" : deedContract.trim();
        deedSignerKey = deedSignerKey == null ? "" : deedSignerKey.trim();
        voucherMinutes = voucherMinutes <= 0 ? 30 : voucherMinutes;
    }

    /** Never print the key, even in a debugger. */
    @Override
    public String toString() {
        return "WalletProperties[enabled=" + enabled + ", domain=" + domain + ", uri=" + uri + ", chainId=" + chainId
                + ", deedContract=" + deedContract + ", deedSignerKey=" + (deedSignerKey.isEmpty() ? "unset" : "set")
                + ", voucherMinutes=" + voucherMinutes + "]";
    }
}
