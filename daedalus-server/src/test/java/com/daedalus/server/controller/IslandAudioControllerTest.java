// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.world.audio.*;
import java.util.List;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class IslandAudioControllerTest {
    private final com.fasterxml.jackson.databind.ObjectMapper json = new com.fasterxml.jackson.databind.ObjectMapper();
    private static java.security.Principal host() {
        return UsernamePasswordAuthenticationToken.authenticated("engine", "unused", List.of());
    }
    private static IslandAudioController.Request request() {
        return new IslandAudioController.Request(Biome.FOREST, 13.0, 0.0, .5, .2, Species.CANID, "00", IslandAudioController.MusicCue.FIELD);
    }
    @Test void fixtureMatchesHttpAndLocaleDoesNotChangeWire() throws Exception {
        var controller = new IslandAudioController("engine");
        var expected = Files.readString(Path.of("..", "docs", "contracts", "aud-v1", "forest-canid.aud"));
        var old = java.util.Locale.getDefault();
        try {
            java.util.Locale.setDefault(java.util.Locale.GERMANY);
            assertThat(controller.design(request(), host())).isEqualTo(expected);
        } finally { java.util.Locale.setDefault(old); }
        var response = MockMvcBuilders.standaloneSetup(controller).build().perform(post("/api/v1/audio/design")
                .principal(host()).contentType("application/json").content(json.writeValueAsString(request())))
                .andExpect(status().isOk()).andReturn().getResponse();
        assertThat(response.getContentAsString()).isEqualTo(expected);
        assertThat(response.getContentType()).startsWith("text/plain");
    }
    @Test void rejectsMissingAndOutOfRangeDataWithoutClamping() throws Exception {
        var controller = new IslandAudioController("engine");
        var base = json.convertValue(request(), new com.fasterxml.jackson.core.type.TypeReference<java.util.Map<String, Object>>() { });
        for (String key : base.keySet()) {
            var invalid = new java.util.HashMap<>(base); invalid.put(key, null);
            assertThatThrownBy(() -> controller.design(json.convertValue(invalid, IslandAudioController.Request.class), host()))
                    .hasMessageContaining("400");
        }
        for (String key : List.of("hour", "rain", "wind", "waterNear")) {
            for (double value : new double[]{-1, 25, Double.NaN, Double.POSITIVE_INFINITY}) {
                var invalid = new java.util.HashMap<>(base); invalid.put(key, value);
                assertThatThrownBy(() -> controller.design(json.convertValue(invalid, IslandAudioController.Request.class), host()))
                        .hasMessageContaining("400");
            }
        }
        for (String genome : List.of("", "0", "zz", "0x00", "a".repeat(130))) {
            var invalid = new java.util.HashMap<>(base); invalid.put("genome", genome);
            assertThatThrownBy(() -> controller.design(json.convertValue(invalid, IslandAudioController.Request.class), host())).hasMessageContaining("400");
        }
        assertThatThrownBy(() -> controller.design(null, host())).hasMessageContaining("400");
    }
    @Test void committedHttpCasesMatchController() throws Exception {
        var directory = Path.of("..", "docs", "contracts", "aud-v1");
        for (var item : json.readTree(Files.readString(directory.resolve("http-cases.json")))) {
            if (item.get("status").asInt() == 401) continue; // Covered by the real production filter chain test.
            var controller = new IslandAudioController(item.has("hostConfigured") ? "" : "engine");
            var principal = UsernamePasswordAuthenticationToken.authenticated(
                    item.get("auth").asText().equals("other-user") ? "other" : "engine", "unused", List.of());
            var response = MockMvcBuilders.standaloneSetup(controller).build().perform(post("/api/v1/audio/design")
                    .principal(principal).contentType("application/json").content(item.get("request").toString()))
                    .andExpect(status().is(item.get("status").asInt())).andReturn().getResponse();
            if (item.has("responseFile")) assertThat(response.getContentAsString())
                    .isEqualTo(Files.readString(directory.resolve(item.get("responseFile").asText())));
        }
    }
    @Test void hostBoundaryDeniesNameSpoofingAndMissingConfiguration() {
        var controller = new IslandAudioController("engine");
        for (java.security.Principal principal : java.util.Arrays.asList(null, (java.security.Principal) () -> "engine",
                UsernamePasswordAuthenticationToken.unauthenticated("engine", "unused"),
                UsernamePasswordAuthenticationToken.authenticated("other", "unused", List.of()),
                new org.springframework.security.authentication.AnonymousAuthenticationToken("key", "engine",
                        List.of(new org.springframework.security.core.authority.SimpleGrantedAuthority("ROLE_ANONYMOUS"))))) {
            assertThatThrownBy(() -> controller.design(request(), principal)).hasMessageContaining("403");
        }
        assertThatThrownBy(() -> new IslandAudioController("").design(request(), host())).hasMessageContaining("403");
    }
    @Test void allBiomesSpeciesAndJukeboxCuesRemainBounded() {
        var controller = new IslandAudioController("engine");
        for (var biome : Biome.values()) for (var species : Species.values()) for (var cue : IslandAudioController.MusicCue.values()) {
            var req = new IslandAudioController.Request(biome, 24.0, 1.0, 1.0, 1.0, species, "ff".repeat(64), cue);
            var wire = controller.design(req, host());
            assertThat(wire).startsWith("AUD 1\njukebox " + cue + "\n").endsWith("end\n");
            assertThat(wire.length()).isLessThan(4096);
            assertThat(wire).doesNotContain("NaN", "Infinity", "\r");
            String call = wire.lines().filter(l -> l.startsWith("PCS 1 ")).findFirst().orElseThrow();
            assertThat(CallSpec.parse(call).toLine()).isEqualTo(call);
            assertThat(controller.design(req, host())).isEqualTo(wire);
        }
    }
}
