// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.config.JukeboxProperties;
import com.daedalus.server.jukebox.JsonRpc;
import com.daedalus.server.jukebox.JukeboxService;
import com.daedalus.server.jukebox.StudioArranger;
import com.daedalus.server.jukebox.radio.RadioService;
import com.daedalus.server.jukebox.radio.RadioStation;
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
    private boolean radioDown;
    private StudioArranger arranger = StudioArranger.STUB;

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
                case "0xa3864397" -> "0x" + "ab".repeat(32);
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
        RadioService radio = new RadioService(path -> {
            if (radioDown) throw new IllegalStateException("down");
            return List.of(
                    new RadioStation("far", "Radio Eins", "https://eins/stream", "", "Berlin", "Berlin", "", "DE", 52.5, 13.4),
                    new RadioStation("am", "KSUH 1450 AM", "http://ksuh/stream", "", "Washington", "Washington", "", "US", 47.31, -122.33),
                    new RadioStation("fm", "KEXP 90.3 FM", "https://kexp/stream", "", "Washington", "Washington", "", "US", 47.62, -122.35),
                    new RadioStation("ssrf", "Sneaky FM 99.9", "http://169.254.169.254/latest", "", "Nowhere", "", "", "ZZ", null, null));
        }, () -> 0);
        return MockMvcBuilders.standaloneSetup(new JukeboxController(new JukeboxService(p, p.hasContract() ? chain : null,
                arranger, radio))).setControllerAdvice(new ApiExceptionHandler()).build();
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
        assertThat(a.get("note").asText()).contains("original");
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

    @Test
    void tokenHashIsReadFromTheChainOnlyAfterReveal() throws Exception {
        JsonNode h = read(mvc.perform(get("/api/v1/jukebox/tokens/1/hash")).andReturn().getResponse());
        assertThat(h.get("hash").asText()).isEqualTo("0x" + "ab".repeat(32));
        assertThat(mvc.perform(get("/api/v1/jukebox/tokens/3/hash")).andReturn().getResponse().getStatus()).isEqualTo(404);
        chainDown = true;
        assertThat(mvc.perform(get("/api/v1/jukebox/tokens/2/hash")).andReturn().getResponse().getStatus()).isEqualTo(502);
    }

    @Test
    void radioListsLocalFmFirstAndPlaysHttpsDirectHttpThroughTheRelay() throws Exception {
        JsonNode r = read(mvc.perform(get("/api/v1/jukebox/radio/stations").param("lat", "47.6062").param("lon", "-122.3321"))
                .andReturn().getResponse());
        JsonNode st = r.get("stations");
        assertThat(st.get(0).get("id").asText()).isEqualTo("fm");
        assertThat(st.get(0).get("tier").asText()).isEqualTo("LOCAL_FM");
        assertThat(st.get(0).get("band").asText()).isEqualTo("FM");
        assertThat(st.get(0).get("play").asText()).isEqualTo("/api/v1/jukebox/radio/stream/fm");   // same-origin: WebAudio can route it
        assertThat(st.get(1).get("tier").asText()).isEqualTo("LOCAL");
        assertThat(st.get(1).get("play").asText()).isEqualTo("/api/v1/jukebox/radio/stream/am");
        assertThat(st.get(2).get("tier").asText()).isEqualTo("ELSEWHERE");
    }

    @Test
    void radioWithNoLocationStillAnswersAndSaysSo() throws Exception {
        JsonNode r = read(mvc.perform(get("/api/v1/jukebox/radio/stations")).andReturn().getResponse());
        assertThat(r.get("note").asText()).contains("No location");
        assertThat(r.get("stations")).hasSize(4);
        radioDown = true;
        mvc = boot(true, RDSONG);
        assertThat(mvc.perform(get("/api/v1/jukebox/radio/stations").param("place", "Nowhere"))
                .andReturn().getResponse().getStatus()).isEqualTo(502);
    }

    @Test
    void theRelayNeverFetchesAUrlItDidNotList() throws Exception {
        for (String id : List.of("never-listed", "http:%2F%2Fevil", "fm")) {
            assertThat(mvc.perform(get("/api/v1/jukebox/radio/stream/" + id)).andReturn().getResponse().getStatus())
                    .as(id).isEqualTo(404);       // "fm" was not listed by this controller instance yet
        }
    }

    @Test
    void studioRelaysAnswer404WhenNoStudioIsConnected() throws Exception {
        assertThat(mvc.perform(get("/api/v1/jukebox/studio/audio/e00015__jazz__studio__v1.mp3")).andReturn().getResponse().getStatus()).isEqualTo(404);
        assertThat(mvc.perform(get("/api/v1/jukebox/coat.png").param("hash", "0x" + "ab".repeat(32))).andReturn().getResponse().getStatus()).isEqualTo(404);
        assertThat(mvc.perform(get("/api/v1/jukebox/coat").param("hash", "0x" + "ab".repeat(32))).andReturn().getResponse().getStatus()).isEqualTo(404);
    }

    @Test
    void aListedStationThatPointsAtPrivateSpaceIsStillNeverFetched() throws Exception {
        mvc.perform(get("/api/v1/jukebox/radio/stations")).andReturn();               // lists "ssrf" (cloud metadata URL)
        MockHttpServletResponse r = mvc.perform(get("/api/v1/jukebox/radio/stream/ssrf")).andReturn().getResponse();
        assertThat(r.getStatus()).isEqualTo(502);
        assertThat(r.getContentAsString()).doesNotContain("169.254");
    }

    @Test
    void radioInputsAreValidated() throws Exception {
        String[][] bad = {{"lat", "91", "lon", "0"}, {"lat", "0", "lon", "-181"}, {"lat", "NaN", "lon", "0"}, {"lat", "10"},
                {"place", "<script>alert(1)</script>"}, {"place", "x".repeat(101)}, {"country", "USA"}, {"country", "1"}};
        for (String[] q : bad) {
            var req = get("/api/v1/jukebox/radio/stations");
            for (int i = 0; i < q.length; i += 2) req = req.param(q[i], q[i + 1]);
            assertThat(mvc.perform(req).andReturn().getResponse().getStatus()).as(String.join("=", q)).isEqualTo(400);
        }
        assertThat(mvc.perform(get("/api/v1/jukebox/radio/stations").param("place", "São Paulo, BR")).andReturn().getResponse().getStatus())
                .isEqualTo(200);
    }

    @Test
    void aRenderingArrangementCarriesItsJobAndRetryAfter() throws Exception {
        arranger = (source, genre, studio) -> new StudioArranger.Arrangement(source, genre, studio, false, null, "rendering",
                StudioArranger.Status.RENDERING, "job-7", 2500L);
        mvc = boot(true, RDSONG);
        MockHttpServletResponse r = mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "seed:e00084").param("genre", "rock"))
                .andReturn().getResponse();
        assertThat(r.getHeader("Retry-After")).isEqualTo("3");
        assertThat(r.getHeader("Cache-Control")).contains("no-store");
        JsonNode a = read(r);
        assertThat(a.get("status").asText()).isEqualTo("RENDERING");
        assertThat(a.get("jobId").asText()).isEqualTo("job-7");
        assertThat(a.get("retryAfterMs").asLong()).isEqualTo(2500);
    }

    @Test
    void configReportsStudioHealthAndWhereHoldersComeFrom() throws Exception {
        JsonNode c = read(mvc.perform(get("/api/v1/jukebox/config")).andReturn().getResponse());
        assertThat(c.get("studioHealth").get("state").asText()).isEqualTo("OFF");
        assertThat(c.get("holders").get("source").asText()).isEqualTo("scan");
    }

    /** Random junk into every jukebox endpoint: answers are 2xx/3xx/4xx or a deliberate 502/503, never a 500. */
    @Test
    void fuzzedInputsNeverCrashAnEndpoint() throws Exception {
        java.util.Random rnd = new java.util.Random(4663);
        String alphabet = "abcAZ09:/._-%~!@#$^&*()[]{}<>|\\\"' \t\u00e9\u4e2d\u0000+=?,;";
        String[] paths = {"/api/v1/jukebox/arrangement?source=%s&genre=%s&studio=%s", "/api/v1/jukebox/tokens/%s/html",
                "/api/v1/jukebox/tokens/%s/hash", "/api/v1/jukebox/coat.png?hash=%s&size=%s", "/api/v1/jukebox/coat?hash=%s",
                "/api/v1/jukebox/radio/stations?place=%s&country=%s&lat=%s&lon=%s", "/api/v1/jukebox/radio/stream/%s",
                "/api/v1/jukebox/studio/audio/%s", "/api/v1/jukebox/seeds/%s"};
        int runs = 0;
        for (int i = 0; i < 1500; i++) {
            String tpl = paths[i % paths.length];
            Object[] args = new Object[4];
            for (int a = 0; a < 4; a++) {
                StringBuilder b = new StringBuilder();
                int n = rnd.nextInt(rnd.nextInt(10) == 0 ? 300 : 24);
                for (int k = 0; k < n; k++) b.append(alphabet.charAt(rnd.nextInt(alphabet.length())));
                if (rnd.nextInt(6) == 0) b.setLength(0);
                if (rnd.nextInt(8) == 0) b.append(rnd.nextInt(3) == 0 ? "-1" : String.valueOf(rnd.nextLong()));
                args[a] = java.net.URLEncoder.encode(b.toString(), java.nio.charset.StandardCharsets.UTF_8);
            }
            String url = String.format(tpl, args);
            int status;
            try {
                status = mvc.perform(get(java.net.URI.create(url))).andReturn().getResponse().getStatus();
            } catch (IllegalArgumentException e) {
                continue;     // MockMvc itself refused the URI; a real container would 400 it
            }
            runs++;
            assertThat(status).as(url).isNotEqualTo(500).isLessThan(600);
            assertThat(status == 502 || status == 503 || status < 500).as(url).isTrue();
        }
        assertThat(runs).isGreaterThan(1200);
    }

    @Test
    void r4RenderParamsAreValidatedAndPassedToTheStudio() throws Exception {
        List<StudioArranger.Render> seen = new ArrayList<>();
        arranger = new StudioArranger() {
            @Override public Arrangement arrange(String source, String genre, boolean studio) {
                return arrange(source, genre, studio, Render.DEFAULT);
            }
            @Override public Arrangement arrange(String source, String genre, boolean studio, Render render) {
                seen.add(render);
                return new Arrangement(source, genre, studio, false, null, "stub");
            }
        };
        mvc = boot(true, RDSONG);
        MockHttpServletResponse ok = mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "token:1").param("genre", "jazz")
                .param("format", "flac").param("preset", "crossfeed").param("vinyl", "40").param("noise", "-50")).andReturn().getResponse();
        assertThat(ok.getStatus()).isEqualTo(200);
        assertThat(seen).containsExactly(new StudioArranger.Render("flac", "crossfeed", 40, "-50"));
        mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "token:1")).andReturn();
        assertThat(seen.get(1)).isEqualTo(StudioArranger.Render.DEFAULT);                 // surface noise is off by default
        for (String[] bad : new String[][]{{"format", "wav"}, {"preset", "loudness"}, {"vinyl", "150"}, {"vinyl", "x"},
                {"noise", "-10"}, {"noise", "on"}}) {
            assertThat(mvc.perform(get("/api/v1/jukebox/arrangement").param("source", "token:1").param(bad[0], bad[1]))
                    .andReturn().getResponse().getStatus()).as(bad[0] + "=" + bad[1]).isEqualTo(400);
        }
        assertThat(seen).hasSize(2);
    }
}
