// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.config.JukeboxProperties;
import com.daedalus.server.jukebox.JsonRpc;
import com.daedalus.server.jukebox.JukeboxService;
import com.daedalus.server.jukebox.StudioArranger;
import com.daedalus.server.web.ApiExceptionHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

class JukeboxControllerTest {

    static final String HOLDER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266";
    static final String OTHER = "0x70997970c51812dc3b10e7aa25ab8ee8af0d5e20";
    static final String RDSONG = "0x286562588c32692e49befd2f7ec628a6cbef7162";

    @TempDir Path seeds;
    private final ObjectMapper json = new ObjectMapper();
    private MockMvc mvc;
    private boolean chainDown;

    /** Tokens 0..3: holder owns 1 and 3; 0..2 are revealed. */
    private final JsonRpc chain = (to, data) -> {
        if (chainDown) throw new IllegalStateException("down");
        assertThat(to).isEqualTo(RDSONG);
        List<String> owners = List.of(OTHER, HOLDER, OTHER, HOLDER);
        List<String> out = new ArrayList<>();
        for (String d : data) {
            String sel = d.substring(0, 10);
            long id = d.length() > 10 ? Long.parseLong(d.substring(10), 16) : 0;
            String w = String.format("%064x", sel.equals("0x18160ddd") ? 4 : sel.equals("0x5055fbc3") ? (id < 3 ? 1 : 0) : 0);
            out.add(switch (sel) {
                case "0x18160ddd", "0x5055fbc3" -> "0x" + w;
                case "0x6352211e" -> "0x" + "0".repeat(24) + owners.get((int) id).substring(2);
                case "0xb79bebaf" -> {
                    String hex = HexFormat.of().formatHex("<html>song</html>".getBytes());
                    yield "0x" + String.format("%064x", 32) + String.format("%064x", 17) + hex + "0".repeat(64 - hex.length());
                }
                default -> null;
            });
        }
        return out;
    };

    @BeforeEach
    void setUp() throws Exception {
        Files.writeString(seeds.resolve("celtic-pipes.mp3"), "ID3");
        Files.writeString(seeds.resolve("celtic-pipes.webp"), "RIFF");
        Files.writeString(seeds.resolve("alpine.mp3"), "ID3");
        Files.writeString(seeds.resolve("NOT_A_SLUG.mp3"), "x");
        mvc = boot(true, RDSONG);
    }

    private MockMvc boot(boolean enabled, String contract) {
        JukeboxProperties p = new JukeboxProperties(enabled, 46630, "", contract, seeds.toString(), 2, 0, 30, "");
        return MockMvcBuilders.standaloneSetup(new JukeboxController(new JukeboxService(p, p.hasContract() ? chain : null,
                StudioArranger.STUB))).setControllerAdvice(new ApiExceptionHandler()).build();
    }

    private JsonNode read(MockHttpServletResponse r) throws Exception {
        return json.readTree(r.getContentAsString());
    }

    @Test
    void configNamesTheChainContractAndGenres() throws Exception {
        JsonNode c = read(mvc.perform(get("/api/v1/jukebox/config")).andReturn().getResponse());
        assertThat(c.get("enabled").asBoolean()).isTrue();
        assertThat(c.get("onChain").asBoolean()).isTrue();
        assertThat(c.get("chainId").asLong()).isEqualTo(46630);
        assertThat(c.get("contract").asText()).isEqualTo(RDSONG);
        assertThat(c.get("genres").toString()).contains("rock", "jazz", "reggae", "orchestral");
    }

    @Test
    void aHolderGetsTheirOwnTokensFromTheirSignIn() throws Exception {
        MockHttpServletResponse r = mvc.perform(get("/api/v1/jukebox/owned").principal(() -> HOLDER)).andReturn().getResponse();
        assertThat(r.getStatus()).isEqualTo(200);
        assertThat(read(r).get("tokens").toString()).isEqualTo("[1,3]");
    }

    @Test
    void ownedNeedsAWalletSignIn() throws Exception {
        assertThat(mvc.perform(get("/api/v1/jukebox/owned")).andReturn().getResponse().getStatus()).isEqualTo(403);
        assertThat(mvc.perform(get("/api/v1/jukebox/owned").principal(() -> "admin")).andReturn().getResponse().getStatus())
                .isEqualTo(403);
    }

    @Test
    void aChainOutageIsA502NotACrash() throws Exception {
        chainDown = true;
        assertThat(mvc.perform(get("/api/v1/jukebox/owned").principal(() -> HOLDER)).andReturn().getResponse().getStatus())
                .isEqualTo(502);
    }

    @Test
    void tokenHtmlIsServedSandboxedAndOnlyAfterReveal() throws Exception {
        MockHttpServletResponse r = mvc.perform(get("/api/v1/jukebox/tokens/1/html")).andReturn().getResponse();
        assertThat(r.getStatus()).isEqualTo(200);
        assertThat(r.getContentAsString()).isEqualTo("<html>song</html>");
        assertThat(r.getHeader("Content-Security-Policy")).isEqualTo("sandbox allow-scripts");
        assertThat(r.getHeader("X-Frame-Options")).isEqualTo("SAMEORIGIN");
        MockHttpServletResponse unrevealed = mvc.perform(get("/api/v1/jukebox/tokens/3/html")).andReturn().getResponse();
        assertThat(unrevealed.getStatus()).isEqualTo(404);
        assertThat(read(unrevealed).path("status").asInt()).isEqualTo(404);   // the JSON error contract, not an empty 404
    }

    @Test
    void guestsGetTheSeedSongsAndNothingElseFromTheDirectory() throws Exception {
        JsonNode s = read(mvc.perform(get("/api/v1/jukebox/seeds")).andReturn().getResponse()).get("seeds");
        assertThat(s).hasSize(2);
        assertThat(s.get(1).get("title").asText()).isEqualTo("Celtic Pipes");
        assertThat(s.get(1).get("cover").asText()).endsWith("celtic-pipes.webp");
        assertThat(s.get(0).get("cover").isNull()).isTrue();
        MockHttpServletResponse mp3 = mvc.perform(get("/api/v1/jukebox/seeds/alpine.mp3")).andReturn().getResponse();
        assertThat(mp3.getStatus()).isEqualTo(200);
        assertThat(mp3.getContentType()).isEqualTo("audio/mpeg");
        for (String bad : List.of("NOT_A_SLUG.mp3", "..%2Fsecret.mp3", "alpine.txt", "missing.mp3")) {
            assertThat(mvc.perform(get("/api/v1/jukebox/seeds/" + bad)).andReturn().getResponse().getStatus()).as(bad).isEqualTo(404);
        }
    }

    @Test
    void theArrangementSeamIsStubbedAndValidated() throws Exception {
        JsonNode a = read(mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "token:1").param("genre", "jazz")
                .param("studio", "true")).andReturn().getResponse());
        assertThat(a.get("available").asBoolean()).isFalse();
        assertThat(a.get("genre").asText()).isEqualTo("jazz");
        assertThat(mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "token:1").param("genre", "polka"))
                .andReturn().getResponse().getStatus()).isEqualTo(400);
        assertThat(mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "file:/etc/passwd"))
                .andReturn().getResponse().getStatus()).isEqualTo(400);
    }

    @Test
    void offMeansNoSongsAndNoChainReads() throws Exception {
        mvc = boot(false, RDSONG);
        JsonNode c = read(mvc.perform(get("/api/v1/jukebox/config")).andReturn().getResponse());
        assertThat(c.get("onChain").asBoolean()).isFalse();
        assertThat(read(mvc.perform(get("/api/v1/jukebox/seeds")).andReturn().getResponse()).get("seeds")).isEmpty();
        assertThat(mvc.perform(get("/api/v1/jukebox/tokens/1/html")).andReturn().getResponse().getStatus()).isEqualTo(404);
    }

    @Test
    void noContractConfiguredMeansAnEmptyHolderListNotAnError() throws Exception {
        mvc = boot(true, "");       // e.g. mainnet 4663 before RDSong is deployed there
        JsonNode r = read(mvc.perform(get("/api/v1/jukebox/owned").principal(() -> HOLDER)).andReturn().getResponse());
        assertThat(r.get("onChain").asBoolean()).isFalse();
        assertThat(r.get("tokens")).isEmpty();
    }
}
