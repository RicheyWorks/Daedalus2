// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.config.JwtAuthProperties;
import com.daedalus.server.config.WalletProperties;
import com.daedalus.server.security.JwtTokenService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.wallet.DeedVoucher;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.web3j.crypto.Credentials;
import org.web3j.crypto.Sign;
import org.web3j.utils.Numeric;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Wallet sign-in and deed vouchers over HTTP (ADR-028), with Hardhat's public test keys: a player
 * signs the server's message and gets a token whose subject is their address; the token claims an
 * island; the island's owner — and only the owner — gets a voucher the realm key signed.
 */
class WalletControllerTest {

    /** Hardhat test accounts 0 (player), 1 (another player), 2 (the realm's deed key). Public; dev only. */
    static final String PLAYER_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
    static final String PLAYER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266";
    static final String OTHER_KEY = "59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
    static final String REALM_KEY = "5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a";
    static final String CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
    static final Instant NOW = Instant.parse("2026-10-11T15:00:00Z");

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private WorldService worlds;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        worlds = new WorldService(tmp.resolve("world-zero.daew"), e -> { });
        worlds.raiseIsland("world-zero", 11, 18);
        mvc = boot(REALM_KEY, CONTRACT);
    }

    private MockMvc boot(String key, String contract) {
        WalletProperties props = new WalletProperties(true, "realm.example", "https://realm.example", 31_337L,
                contract, key, 30);
        JwtTokenService tokens = new JwtTokenService(new JwtAuthProperties("wallet-test-secret-32-bytes-long!!", "daedalus", 60));
        WalletController c = new WalletController(props, tokens, worlds);
        c.useClock(() -> NOW);
        this.tokens = tokens;
        return MockMvcBuilders.standaloneSetup(c).setControllerAdvice(new ApiExceptionHandler()).build();
    }

    private JwtTokenService tokens;

    static String personalSign(String message, String key) {
        Sign.SignatureData s = Sign.signPrefixedMessage(message.getBytes(StandardCharsets.UTF_8),
                Credentials.create(key).getEcKeyPair());
        byte[] out = new byte[65];
        System.arraycopy(s.getR(), 0, out, 0, 32);
        System.arraycopy(s.getS(), 0, out, 32, 32);
        out[64] = s.getV()[0];
        return Numeric.toHexString(out);
    }

    private JsonNode body(MockHttpServletResponse r) throws Exception {
        return json.readTree(r.getContentAsString());
    }

    private String message(String address) throws Exception {
        return body(mvc.perform(get("/api/v1/auth/wallet/nonce").param("address", address)).andReturn().getResponse())
                .get("message").asText();
    }

    private MockHttpServletResponse signIn(String message, String signature) throws Exception {
        return mvc.perform(post("/api/v1/auth/wallet").contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsString(java.util.Map.of("message", message, "signature", signature))))
                .andReturn().getResponse();
    }

    private String token(String key) throws Exception {
        String address = Credentials.create(key).getAddress();
        String m = message(address);
        return body(signIn(m, personalSign(m, key))).get("token").asText();
    }

    @Test
    void aWalletSignsTheServersMessageAndGetsATokenForItsAddress() throws Exception {
        String m = message(PLAYER.toUpperCase().replace("0X", "0x"));
        assertThat(m).startsWith("realm.example wants you to sign in with your Ethereum account:\n"
                + "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266\n\nSign in to the Daedalus Realm.\n\n"
                + "URI: https://realm.example\nVersion: 1\nChain ID: 31337\nNonce: ");
        assertThat(m).contains("Issued At: 2026-10-11T15:00:00Z\nExpiration Time: 2026-10-11T15:10:00Z");

        MockHttpServletResponse ok = signIn(m, personalSign(m, PLAYER_KEY));
        assertThat(ok.getStatus()).isEqualTo(200);
        String token = body(ok).get("token").asText();
        assertThat(tokens.decoder().decode(token).getSubject()).isEqualTo(PLAYER);

        MockHttpServletResponse replay = signIn(m, personalSign(m, PLAYER_KEY));
        assertThat(replay.getStatus()).isEqualTo(401);
        assertThat(replay.getHeader("X-Wallet-Refused")).isEqualTo("STALE_NONCE");
    }

    @Test
    void signInRefusalsSayWhy() throws Exception {
        String m = message(PLAYER);
        MockHttpServletResponse someoneElse = signIn(m, personalSign(m, OTHER_KEY));
        assertThat(someoneElse.getHeader("X-Wallet-Refused")).isEqualTo("BAD_SIGNATURE");
        String otherSite = m.replace("realm.example wants", "evil.example wants");
        assertThat(signIn(otherSite, personalSign(otherSite, PLAYER_KEY)).getHeader("X-Wallet-Refused"))
                .isEqualTo("WRONG_DOMAIN");
        String otherChain = m.replace("Chain ID: 31337", "Chain ID: 1");
        assertThat(signIn(otherChain, personalSign(otherChain, PLAYER_KEY)).getHeader("X-Wallet-Refused"))
                .isEqualTo("WRONG_CHAIN");
        assertThat(signIn("hello", personalSign("hello", PLAYER_KEY)).getHeader("X-Wallet-Refused")).isEqualTo("MALFORMED");
        // The refusals did not burn the real nonce.
        assertThat(signIn(m, personalSign(m, PLAYER_KEY)).getStatus()).isEqualTo(200);
        assertThat(mvc.perform(get("/api/v1/auth/wallet/nonce").param("address", "0x12")).andReturn().getResponse()
                .getStatus()).isEqualTo(400);
    }

    @Test
    void theIslandsWalletOwnerGetsAVoucherTheRealmSigned() throws Exception {
        String token = token(PLAYER_KEY);
        assertThat(worlds.claimIsland("world-zero", 0, PLAYER).result()).isEqualTo("CLAIMED");

        MockHttpServletResponse r = mvc.perform(post("/api/v1/world/world-zero/islands/0/deed-voucher")
                .header("Authorization", "Bearer " + token)).andReturn().getResponse();
        assertThat(r.getStatus()).isEqualTo(200);
        JsonNode v = body(r);
        assertThat(v.get("to").asText()).isEqualTo(PLAYER);
        assertThat(v.get("slot").asInt()).isZero();
        assertThat(v.get("seed").asText()).isEqualTo("11");
        assertThat(v.get("radius").asInt()).isEqualTo(18);
        assertThat(v.get("deadline").asLong()).isEqualTo(NOW.plusSeconds(1800).getEpochSecond());
        assertThat(v.get("chainId").asLong()).isEqualTo(31_337L);
        assertThat(v.get("contract").asText()).isEqualTo(CONTRACT.toLowerCase());
        DeedVoucher d = new DeedVoucher(PLAYER, 0, 11, 18, v.get("deadline").asLong(), 31_337L, CONTRACT);
        assertThat(d.signer(v.get("signature").asText())).contains(Credentials.create(REALM_KEY).getAddress());

        JsonNode config = body(mvc.perform(get("/api/v1/auth/wallet/config")).andReturn().getResponse());
        assertThat(config.get("deedSigner").asText()).isEqualToIgnoringCase(Credentials.create(REALM_KEY).getAddress());
        assertThat(config.get("deeds").asBoolean()).isTrue();
    }

    @Test
    void onlyTheOwnersWalletGetsAVoucher() throws Exception {
        worlds.claimIsland("world-zero", 0, PLAYER);
        String other = token(OTHER_KEY);
        assertThat(mvc.perform(post("/api/v1/world/world-zero/islands/0/deed-voucher").header("Authorization", "Bearer " + other))
                .andReturn().getResponse().getHeader("X-Wallet-Refused")).isEqualTo("NOT_OWNER");
        assertThat(mvc.perform(post("/api/v1/world/world-zero/islands/0/deed-voucher")).andReturn().getResponse()
                .getStatus()).isEqualTo(401);
        assertThat(mvc.perform(post("/api/v1/world/world-zero/islands/0/deed-voucher")
                .header("Authorization", "Bearer forged.token.here")).andReturn().getResponse().getStatus()).isEqualTo(401);
        // An admin-login token ("alice") is not a wallet: no voucher.
        String alice = tokens.issue("alice").token();
        assertThat(mvc.perform(post("/api/v1/world/world-zero/islands/0/deed-voucher").header("Authorization", "Bearer " + alice))
                .andReturn().getResponse().getHeader("X-Wallet-Refused")).isEqualTo("SIGN_IN");
        String mine = token(PLAYER_KEY);
        assertThat(mvc.perform(post("/api/v1/world/world-zero/islands/5/deed-voucher").header("Authorization", "Bearer " + mine))
                .andReturn().getResponse().getStatus()).isEqualTo(404);
        assertThat(mvc.perform(post("/api/v1/world/nope/islands/0/deed-voucher").header("Authorization", "Bearer " + mine))
                .andReturn().getResponse().getStatus()).isEqualTo(404);
    }

    @Test
    void withoutAKeyOrAContractThereAreNoVouchers() throws Exception {
        worlds.claimIsland("world-zero", 0, PLAYER);
        for (MockMvc off : new MockMvc[] {boot("", CONTRACT), boot(REALM_KEY, "")}) {
            mvc = off;
            String t = token(PLAYER_KEY);
            MockHttpServletResponse r = mvc.perform(post("/api/v1/world/world-zero/islands/0/deed-voucher")
                    .header("Authorization", "Bearer " + t)).andReturn().getResponse();
            assertThat(r.getStatus()).isEqualTo(503);
            assertThat(r.getHeader("X-Wallet-Refused")).isEqualTo("DEEDS_OFF");
            assertThat(body(mvc.perform(get("/api/v1/auth/wallet/config")).andReturn().getResponse()).get("deeds").asBoolean())
                    .isFalse();
        }
    }

    @Test
    void thePropertiesNeverPrintTheKey() {
        WalletProperties p = new WalletProperties(true, null, null, 0, null, REALM_KEY, 0);
        assertThat(p.toString()).doesNotContain(REALM_KEY).contains("deedSignerKey=set");
        assertThat(p.domain()).isEqualTo("localhost:8088");
        assertThat(p.uri()).isEqualTo("http://localhost:8088");
        assertThat(p.chainId()).isEqualTo(11_155_111L);
        assertThat(p.voucherMinutes()).isEqualTo(30);
    }
}
