// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class MelodyBrewControllerTest {
    private final com.fasterxml.jackson.databind.ObjectMapper json = new com.fasterxml.jackson.databind.ObjectMapper();
    private static final List<String> THIN_AIR = List.of("Doleaf", "Mimint", "Solthorn", "Mimint", "Doleaf");

    private static java.security.Principal host() {
        return UsernamePasswordAuthenticationToken.authenticated("engine", "unused", List.of());
    }

    @Test
    void foundTuneNeedsItsRecordPlayed() throws Exception {
        var c = new MelodyBrewController("engine");
        var learned = c.brew(new MelodyBrewController.Request(THIN_AIR, null, List.of("Item_YTM_Record_Alpine")), host());
        assertThat(learned.item()).isEqualTo("Item_YTM_Tonic_Found_thin_air");
        assertThat(learned.foundTune()).isEqualTo("Tune_thin_air");
        assertThat(learned.recordId()).isEqualTo("Item_YTM_Record_Alpine");
        assertThat(learned.foundTuneBonus()).isEqualTo("stamina drain -40% on cliffs");
        assertThat(learned.cadence()).isTrue();
        assertThat(learned.contour()).isEqualTo("Arch");
        assertThat(learned.quality()).isEqualTo("Seventh");
        assertThat(learned.tier()).isEqualTo(3);
        assertThat(learned.notes()).containsExactly(0, 4, 7, 4, 0);
        var plain = c.brew(new MelodyBrewController.Request(THIN_AIR, null, null), host());
        assertThat(plain.item()).isEqualTo("Item_YTM_Tonic_Seventh_T3");
        assertThat(plain.foundTune()).isNull();
        assertThat(plain.recordId()).isNull();
        assertThat(plain.foundTuneBonus()).isNull();
    }

    @Test
    void contoursQualitiesStagesAndNoise() throws Exception {
        var c = new MelodyBrewController("engine");
        var rise = c.brew(new MelodyBrewController.Request(List.of("Doleaf", "Rebell", "Mimint"), List.of(1, 1, 2), null), host());
        assertThat(rise.contour()).isEqualTo("Rise");
        assertThat(rise.quality()).isEqualTo("Aug");
        assertThat(rise.tier()).isEqualTo(1);
        assertThat(rise.item()).isEqualTo("Item_YTM_Tonic_Aug_T1");
        assertThat(rise.cadence()).isFalse();
        var noise = c.brew(new MelodyBrewController.Request(List.of("Doleaf", "Doleaf", "Mimint"), null, null), host());
        assertThat(noise.contour()).isEqualTo("Noise");
        assertThat(noise.quality()).isEqualTo("Noise");
        assertThat(noise.item()).isEqualTo("Item_YTM_Tonic_Dim_T1");
        assertThat(noise.why()).isNotBlank();
        var lower = c.brew(new MelodyBrewController.Request(List.of("doleaf", "rebell", "mimint"), null, null), host());
        assertThat(lower.item()).isEqualTo("Item_YTM_Tonic_Aug_T3");
    }

    @Test
    void jsonOverHttpIsDeterministic() throws Exception {
        var mvc = MockMvcBuilders.standaloneSetup(new MelodyBrewController("engine")).build();
        String body = json.writeValueAsString(new MelodyBrewController.Request(THIN_AIR, null, List.of("Item_YTM_Record_Alpine")));
        String first = null;
        for (int i = 0; i < 2; i++) {
            var r = mvc.perform(post("/api/v1/brew/melody").principal(host()).contentType("application/json").content(body))
                    .andExpect(status().isOk()).andReturn();
            var tree = json.readTree(r.getResponse().getContentAsString());
            assertThat(tree.get("item").asText()).isEqualTo("Item_YTM_Tonic_Found_thin_air");
            assertThat(tree.get("cadence").asBoolean()).isTrue();
            assertThat(tree.get("recordId").asText()).isEqualTo("Item_YTM_Record_Alpine");
            if (first == null) {
                first = r.getResponse().getContentAsString();
            } else {
                assertThat(r.getResponse().getContentAsString()).isEqualTo(first);
            }
        }
        mvc.perform(post("/api/v1/brew/melody").principal(host()).contentType("application/json")
                .content("{\"herbs\":[\"Doleaf\"]}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/brew/melody").principal(UsernamePasswordAuthenticationToken.authenticated("other", "x", List.of()))
                .contentType("application/json").content(body)).andExpect(status().isForbidden());
    }

    @Test
    void refusesUnauthorizedAndInvalidInputs() throws Exception {
        var c = new MelodyBrewController("engine");
        var ok = new MelodyBrewController.Request(THIN_AIR, null, null);
        for (java.security.Principal p : Arrays.asList(null, (java.security.Principal) () -> "engine",
                UsernamePasswordAuthenticationToken.unauthenticated("engine", "unused"),
                UsernamePasswordAuthenticationToken.authenticated("other", "unused", List.of()),
                new AnonymousAuthenticationToken("key", "engine", List.of(new SimpleGrantedAuthority("ROLE_ANONYMOUS"))))) {
            assertThatThrownBy(() -> c.brew(ok, p)).hasMessageContaining("403");
        }
        assertThatThrownBy(() -> new MelodyBrewController("").brew(ok, host())).hasMessageContaining("403");
        assertThatThrownBy(() -> c.brew(null, host())).hasMessageContaining("400");
        for (var herbs : Arrays.asList(null, List.<String>of(), List.of("Doleaf", "Mimint"),
                List.of("Doleaf", "Mimint", "Solthorn", "Mimint", "Doleaf", "Mimint"), List.of("Doleaf", "Clover", "Mimint"),
                Arrays.asList("Doleaf", null, "Mimint"))) {
            assertThatThrownBy(() -> c.brew(new MelodyBrewController.Request(herbs, null, null), host())).hasMessageContaining("400");
        }
        List<String> three = List.of("Doleaf", "Rebell", "Mimint");
        for (var stages : Arrays.asList(List.of(1, 2), List.of(0, 1, 1), List.of(1, 5, 1), Arrays.asList(1, null, 1))) {
            assertThatThrownBy(() -> c.brew(new MelodyBrewController.Request(three, stages, null), host())).hasMessageContaining("400");
        }
        for (var recs : Arrays.asList(List.of("Item_YTM_Record_Nope"), Arrays.asList((String) null),
                java.util.Collections.nCopies(MelodyBrewController.MAX_RECORDS + 1, "Item_YTM_Record_Alpine"))) {
            assertThatThrownBy(() -> c.brew(new MelodyBrewController.Request(three, null, recs), host())).hasMessageContaining("400");
        }
    }

    @Test
    void contractExamplesMatch() throws Exception {
        var dir = java.nio.file.Path.of("..", "docs", "contracts", "brew-melody-v1");
        var cases = json.readTree(java.nio.file.Files.readString(dir.resolve("http-cases.json")));
        assertThat(cases.size()).isGreaterThanOrEqualTo(3);
        for (var item : cases) {
            var principal = UsernamePasswordAuthenticationToken.authenticated(item.get("auth").asText(), "unused", List.of());
            var r = MockMvcBuilders.standaloneSetup(new MelodyBrewController("engine")).build()
                    .perform(post("/api/v1/brew/melody").principal(principal).contentType("application/json")
                            .content(item.get("request").toString()))
                    .andExpect(status().is(item.get("status").asInt())).andReturn();
            if (item.has("response")) {
                assertThat(json.readTree(r.getResponse().getContentAsString())).isEqualTo(item.get("response"));
            }
        }
    }
}
