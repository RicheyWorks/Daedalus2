// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.world.companion.TonicBook;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class KennelControllerTest {
    private final com.fasterxml.jackson.databind.ObjectMapper json = new com.fasterxml.jackson.databind.ObjectMapper();
    private static final String EXPECTED = "TONIC 1\nbrew tonic_barkbalm 1.0 120 0 overTime 0.0\nmod hearts add 1.0\nend\n";
    private static java.security.Principal host() {
        return UsernamePasswordAuthenticationToken.authenticated("engine", "unused", List.of());
    }
    private static KennelController.Request request() {
        return new KennelController.Request(List.of("Barkbalm"), "None", "cane_corso", 1, false, 0L);
    }
    @Test void exactWireAndRetryAreDeterministic() throws Exception {
        var controller = new KennelController("engine");
        assertThat(controller.brew(request(), host())).isEqualTo(EXPECTED);
        assertThat(controller.brew(request(), host())).isEqualTo(EXPECTED);
        var mvc = MockMvcBuilders.standaloneSetup(controller).build();
        var result = mvc.perform(post("/api/v1/kennel/brew").principal(host()).contentType("application/json")
                .content(json.writeValueAsString(request()))).andExpect(status().isOk()).andReturn();
        assertThat(result.getResponse().getContentAsString()).isEqualTo(EXPECTED);
        assertThat(result.getResponse().getContentType()).startsWith("text/plain");
    }
    @Test void committedNativeFixturesMatchHttpResponses() throws Exception {
        var directory = java.nio.file.Path.of("..", "docs", "contracts", "tonic-v1");
        var cases = json.readTree(java.nio.file.Files.readString(directory.resolve("http-cases.json")));
        for (var item : cases) {
            if (item.get("status").asInt() == 401) continue; // Real prod JWT test covers the filter-chain refusal.
            var controller = new KennelController(item.has("hostConfigured") ? "" : "engine");
            var principal = UsernamePasswordAuthenticationToken.authenticated(
                    item.get("auth").asText().equals("other-user") ? "other" : "engine", "unused", List.of());
            var result = MockMvcBuilders.standaloneSetup(controller).build().perform(post("/api/v1/kennel/brew")
                    .principal(principal).contentType("application/json").content(item.get("request").toString()))
                    .andExpect(status().is(item.get("status").asInt())).andReturn();
            if (item.has("responseFile")) assertThat(result.getResponse().getContentAsString())
                    .isEqualTo(java.nio.file.Files.readString(directory.resolve(item.get("responseFile").asText())));
        }
    }
    @Test void refusesUnauthorizedAndInvalidInputs() throws Exception {
        var controller = new KennelController("engine");
        for (java.security.Principal principal : java.util.Arrays.asList(null, (java.security.Principal) () -> "engine",
                UsernamePasswordAuthenticationToken.unauthenticated("engine", "unused"),
                UsernamePasswordAuthenticationToken.authenticated("other", "unused", List.of()),
                new org.springframework.security.authentication.AnonymousAuthenticationToken("key", "engine",
                        List.of(new org.springframework.security.core.authority.SimpleGrantedAuthority("ROLE_ANONYMOUS"))))) {
            assertThatThrownBy(() -> controller.brew(request(), principal)).hasMessageContaining("403");
        }
        assertThatThrownBy(() -> new KennelController("").brew(request(), host())).hasMessageContaining("403");
        assertThatThrownBy(() -> controller.brew(null, host())).hasMessageContaining("400");
        var base = json.convertValue(request(), new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() { });
        for (String key : List.of("herbs", "coat", "drinker", "stage", "charm", "seed")) {
            var invalid = new java.util.HashMap<>(base);
            invalid.put(key, null);
            assertThatThrownBy(() -> controller.brew(json.convertValue(invalid, KennelController.Request.class), host()))
                    .hasMessageContaining("400");
        }
        for (var herbs : List.of(List.<String>of(), List.of("unknown"), List.of("Barkbalm", "Barkbalm"),
                List.of("a", "b", "c", "d"), java.util.Arrays.asList((String) null))) {
            assertThatThrownBy(() -> controller.brew(new KennelController.Request(herbs, "None", "cane_corso", 1, false, 0L), host()))
                    .hasMessageContaining("400");
        }
        for (int stage : new int[]{0, 4}) assertThatThrownBy(() -> controller.brew(
                new KennelController.Request(List.of("Barkbalm"), "None", "cane_corso", stage, false, 0L), host())).hasMessageContaining("400");
        for (String key : List.of("coat", "drinker")) {
            var invalid = new java.util.HashMap<>(base); invalid.put(key, "unknown");
            assertThatThrownBy(() -> controller.brew(json.convertValue(invalid, KennelController.Request.class), host())).hasMessageContaining("400");
        }
    }
    @Test void everyCanonicalRecipeHasBoundedTokenSafeWireAndFizzleIsExplicit() throws Exception {
        TonicBook book;
        try (var input = getClass().getResourceAsStream("/kennel/tonics.json")) {
            book = TonicBook.parse(new String(input.readAllBytes(), StandardCharsets.UTF_8));
        }
        var controller = new KennelController("engine");
        boolean second = false;
        for (var recipe : book.recipes()) {
            for (long seed = 0; seed < 10; seed++) {
                var wire = controller.brew(new KennelController.Request(recipe.herbs(), "Labyrinth", "packMember", 3, true, seed), host());
                assertThat(wire.length()).isLessThan(4096);
                assertThat(recipe.mods().size()).isLessThanOrEqualTo(32);
                assertThat(recipe.grants().size()).isLessThanOrEqualTo(32);
                assertThat(recipe.id()).matches("[A-Za-z0-9_]{1,64}");
                assertThat(recipe.mode()).isIn("pulse", "overTime");
                assertThat(recipe.breedChancePct()).isBetween(0.0, 100.0);
                for (var mod : recipe.mods()) {
                    assertThat(mod.stat()).matches("[A-Za-z0-9_]{1,64}");
                    assertThat(mod.op()).isIn("add", "mul");
                }
                for (var grant : recipe.grants()) assertThat(grant).matches("[A-Za-z0-9_]{1,64}");
                wire.lines().forEach(line -> assertThat(line.length()).isLessThanOrEqualTo(512));
                assertThat(wire).matches("(?s)[A-Za-z0-9_. \\n-]+").endsWith("end\n");
                assertThat(wire.lines().filter(l -> l.startsWith("mod ")).count()).isEqualTo(recipe.mods().size());
                assertThat(wire.lines().filter(l -> l.startsWith("grant ")).count()).isEqualTo(recipe.grants().size());
                second |= wire.split("\n")[1].split(" ")[4].equals("1");
            }
        }
        assertThat(second).isTrue();
        var herbs = book.herbRoles().keySet().stream().sorted().toList();
        for (String a : herbs) for (String b : herbs) {
            if (!a.equals(b) && book.recipe(List.of(a, b)).isEmpty()) {
                assertThatThrownBy(() -> controller.brew(new KennelController.Request(List.of(a, b), "None", "other", 1, false, 0L), host()))
                        .hasMessageContaining("422");
                return;
            }
        }
        throw new AssertionError("Expected an unmatched herb pair");
    }
}
