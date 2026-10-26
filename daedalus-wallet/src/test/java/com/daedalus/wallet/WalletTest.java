// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import org.junit.jupiter.api.Test;
import org.web3j.crypto.Credentials;

import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The wallet provider against another implementation (ADR-028). Every signature and EIP-712 digest
 * below was produced by ethers 6.17.0 — what browser wallets and the fast-food-punks pipeline use —
 * with Hardhat's public test account 0, so Java is checked against what a wallet really signs.
 */
class WalletTest {

    /** Hardhat test account 0: published, dev and testnet only. */
    static final String TEST_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
    static final String TEST_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266";

    static final String SIWE = "realm.example wants you to sign in with your Ethereum account:\n"
            + TEST_ADDRESS + "\n\nSign in to the Daedalus Realm.\n\nURI: https://realm.example\nVersion: 1\n"
            + "Chain ID: 11155111\nNonce: 3f9c1d0b7a6e4c2d\nIssued At: 2026-10-11T15:00:00Z\n"
            + "Expiration Time: 2026-10-11T15:10:00Z";
    static final String SIWE_SIG_ETHERS = "0xdef031f4519d6f36b9fd719c610f542c71cc229ea399ac9d9d3e9a4247686b8d"
            + "7c828efe2f10408e5fdeed6ccd2fc6075085e4b2456c21f8430fb3c5d8c7811d1b";

    static final DeedVoucher DEED = new DeedVoucher("0x70997970C51812dc3A010C7d01b50e0d17dc79C8", 3, -11L, 18,
            1_791_700_000L, 11_155_111L, "0x5FbDB2315678afecb367f032d93F642f64180aa3");
    static final String DEED_DIGEST_ETHERS = "f15575548f85633027775e7ce77930e294ea0388f9b84e8c903cf599d3e7cd51";
    static final String DEED_SIG_ETHERS = "0x4f27ca5a71be4e8194dd7a53c4fe57ec188fb0e9a58347d118df295bd49643bf"
            + "67156c562ea3aa33f447241dae54f3e063946f60ad1ae5b401efcfc6d56368da1b";

    private static final Instant T0 = Instant.parse("2026-10-11T15:00:30Z");

    @Test
    void addressesNormalizeAndCheckTheirChecksum() {
        assertThat(EthereumAddress.normalize(" 0XF39FD6E51AAD88F6F4CE6AB8827279CFFFB92266 "))
                .contains("0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266");
        assertThat(EthereumAddress.normalize("0x")).isEmpty();
        assertThat(EthereumAddress.normalize(null)).isEmpty();
        assertThat(EthereumAddress.normalize("0x123")).isEmpty();
        assertThat(EthereumAddress.equalsNormalized("0x", "0x")).isFalse();
        assertThat(EthereumAddress.checksummed(TEST_ADDRESS.toLowerCase())).isEqualTo(TEST_ADDRESS);
        assertThat(EthereumAddress.checksumValid(TEST_ADDRESS)).isTrue();
        assertThat(EthereumAddress.checksumValid(TEST_ADDRESS.toLowerCase())).isTrue();
        assertThat(EthereumAddress.checksumValid(TEST_ADDRESS.replace("f39F", "F39f"))).isFalse();
        assertThat(EthereumAddress.checksumValid(null)).isFalse();
        assertThatThrownBy(() -> EthereumAddress.checksummed("nope")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void personalSignRecoversWhoSignedAsEthersDoes() {
        assertThat(WalletSignature.recoverAddress(SIWE, SIWE_SIG_ETHERS)).contains(TEST_ADDRESS.toLowerCase());
        assertThat(WalletSignature.recoverAddress(SIWE + " ", SIWE_SIG_ETHERS)).isNotEqualTo(
                java.util.Optional.of(TEST_ADDRESS.toLowerCase()));
        assertThat(WalletSignature.recoverAddress(SIWE, "0x1234")).isEmpty();
        assertThat(WalletSignature.recoverAddress(SIWE, SIWE_SIG_ETHERS.substring(0, 130) + "05")).isEmpty();
        assertThat(WalletSignature.recoverAddress("", SIWE_SIG_ETHERS)).isEmpty();
        assertThat(WalletSignature.recoverAddress(SIWE, null)).isEmpty();
        // v as 0/1 (some hardware wallets) is the same signature as 27/28.
        String v0 = SIWE_SIG_ETHERS.substring(0, 130) + "00";
        assertThat(WalletSignature.recoverAddress(SIWE, v0)).contains(TEST_ADDRESS.toLowerCase());
    }

    @Test
    void siweTextRoundTripsExactly() {
        SiweMessage m = SiweMessage.parse(SIWE).orElseThrow();
        assertThat(m.domain()).isEqualTo("realm.example");
        assertThat(m.address()).isEqualTo(TEST_ADDRESS);
        assertThat(m.chainId()).isEqualTo(11_155_111L);
        assertThat(m.nonce()).isEqualTo("3f9c1d0b7a6e4c2d");
        assertThat(m.toText()).isEqualTo(SIWE);
        assertThat(SiweMessage.parse(SIWE.replace("\n", "\r\n"))).contains(m);
        assertThat(SiweMessage.parse(SIWE.replace("Version: 1", "Version: 2"))).isEmpty();
        assertThat(SiweMessage.parse(SIWE.replace(TEST_ADDRESS, TEST_ADDRESS.replace("f39F", "F39f")))).isEmpty();
        assertThat(SiweMessage.parse(SIWE.replace("3f9c1d0b7a6e4c2d", "short"))).isEmpty();
        assertThat(SiweMessage.parse(SIWE + "\nResources:")).isEmpty();
        assertThat(SiweMessage.parse(null)).isEmpty();
        assertThatThrownBy(() -> new SiweMessage("bad host/", TEST_ADDRESS, "", "u", 1, "abcdefgh",
                T0, T0.plusSeconds(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new SiweMessage("a.b", TEST_ADDRESS, "", "u", 1, "abcdefgh",
                T0, T0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void signInChecksEveryRuleAndNoncesAreSingleUse() {
        SiweVerifier v = new SiweVerifier("realm.example", 11_155_111L, Duration.ofMinutes(1));
        WalletNonces nonces = new SiweNoncesFixture("3f9c1d0b7a6e4c2d").nonces;

        assertThat(new SiweVerifier("other.example", 11_155_111L, Duration.ofMinutes(1))
                .verify(SIWE, SIWE_SIG_ETHERS, nonces, T0).reason()).isEqualTo("WRONG_DOMAIN");
        assertThat(new SiweVerifier("realm.example", 1L, Duration.ofMinutes(1))
                .verify(SIWE, SIWE_SIG_ETHERS, nonces, T0).reason()).isEqualTo("WRONG_CHAIN");
        assertThat(v.verify(SIWE, SIWE_SIG_ETHERS, nonces, Instant.parse("2026-10-11T14:58:00Z")).reason())
                .isEqualTo("NOT_YET_VALID");
        assertThat(v.verify(SIWE, SIWE_SIG_ETHERS, nonces, Instant.parse("2026-10-11T15:10:00Z")).reason())
                .isEqualTo("EXPIRED");
        assertThat(v.verify(SIWE, DEED_SIG_ETHERS, nonces, T0).reason()).isEqualTo("BAD_SIGNATURE");
        assertThat(v.verify("hello", SIWE_SIG_ETHERS, nonces, T0).reason()).isEqualTo("MALFORMED");
        assertThat(nonces.outstanding()).as("refusals do not burn the nonce").isEqualTo(1);

        SiweVerifier.Outcome ok = v.verify(SIWE, SIWE_SIG_ETHERS, nonces, T0);
        assertThat(ok.ok()).isTrue();
        assertThat(ok.address()).isEqualTo(TEST_ADDRESS.toLowerCase());
        assertThat(v.verify(SIWE, SIWE_SIG_ETHERS, nonces, T0).reason()).as("replay").isEqualTo("STALE_NONCE");
    }

    @Test
    void noncesExpireAndAreBounded() {
        WalletNonces n = new WalletNonces(Duration.ofMinutes(5), 3);
        String a = n.issue(T0);
        assertThat(a).matches("[0-9a-f]{32}");
        assertThat(n.consume(a, T0.plus(Duration.ofMinutes(6)))).isFalse();
        String b = n.issue(T0);
        n.issue(T0);
        n.issue(T0);
        n.issue(T0);
        assertThat(n.outstanding()).isEqualTo(3);
        assertThat(n.consume(b, T0)).as("the oldest was dropped").isFalse();
        assertThat(n.consume(null, T0)).isFalse();
        n.issue(T0.plus(Duration.ofMinutes(10)));
        assertThat(n.outstanding()).as("expired ones are pruned").isEqualTo(1);
        assertThatThrownBy(() -> new WalletNonces(Duration.ZERO, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new WalletNonces(Duration.ofSeconds(1), 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void deedVouchersHashAndSignExactlyAsEthersDoes() {
        assertThat(DEED.seedUint64()).isEqualTo("18446744073709551605");
        assertThat(HexFormat.of().formatHex(DEED.digest())).isEqualTo(DEED_DIGEST_ETHERS);
        assertThat(DEED.sign(Credentials.create(TEST_KEY))).isEqualTo(DEED_SIG_ETHERS);
        assertThat(DEED.signer(DEED_SIG_ETHERS)).contains(TEST_ADDRESS.toLowerCase());
        assertThat(DEED.signer("0xdead")).isEmpty();
        DeedVoucher other = new DeedVoucher(DEED.to(), 4, DEED.seed(), DEED.radius(), DEED.deadline(),
                DEED.chainId(), DEED.contract());
        assertThat(other.signer(DEED_SIG_ETHERS)).isNotEqualTo(java.util.Optional.of(TEST_ADDRESS.toLowerCase()));
        assertThatThrownBy(() -> new DeedVoucher("x", 0, 1, 1, 1, 1, DEED.contract()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DeedVoucher(DEED.to(), -1, 1, 1, 1, 1, DEED.contract()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DeedVoucher(DEED.to(), 0, 1, 256, 1, 1, DEED.contract()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DeedVoucher(DEED.to(), 0, 1, 1, 0, 1, DEED.contract()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void theContractFixtureIsStillWhatJavaSigns() throws Exception {
        // chain/test/fixtures/java-deed-voucher.json is redeemed by RealmIslands in the Hardhat tests.
        // If this Java code changes the bytes it signs, this fails here; if the contract changes how it
        // hashes, that test fails there. Either way the two sides cannot drift apart unnoticed.
        java.nio.file.Path fx = java.nio.file.Path.of("..", "chain", "test", "fixtures", "java-deed-voucher.json");
        String json = java.nio.file.Files.readString(fx);
        DeedVoucher d = new DeedVoucher("0x70997970C51812dc3A010C7d01b50e0d17dc79C8", 7, -11L, 18, 4_102_444_800L,
                31_337L, "0x5FbDB2315678afecb367f032d93F642f64180aa3");
        String sig = d.sign(Credentials.create("5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"));
        assertThat(json).contains("\"signature\": \"" + sig + "\"");
        assertThat(json).contains("\"digest\": \"0x" + HexFormat.of().formatHex(d.digest()) + "\"");
        assertThat(json).contains("\"seed\": \"18446744073709551605\"");
    }

    @Test
    void theDeedSignerSignsAsCredentialsDoAndNeverPrintsItsKey() {
        DeedSigner s = DeedSigner.fromHex("0x" + TEST_KEY);
        assertThat(s.address()).isEqualTo(TEST_ADDRESS);
        assertThat(s.sign(DEED)).isEqualTo(DEED_SIG_ETHERS);
        assertThat(s.toString()).isEqualTo("DeedSigner[" + TEST_ADDRESS + "]").doesNotContain(TEST_KEY);
        assertThatThrownBy(() -> DeedSigner.fromHex("abc")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DeedSigner.fromHex(null)).isInstanceOf(IllegalArgumentException.class);
    }

    /** A nonce store holding one known nonce, as if the server had issued it. */
    static final class SiweNoncesFixture {
        final WalletNonces nonces = new WalletNonces(Duration.ofMinutes(10), 8);

        SiweNoncesFixture(String nonce) {
            nonces.adopt(nonce, Instant.parse("2026-10-11T15:00:00Z"));
        }
    }
}
