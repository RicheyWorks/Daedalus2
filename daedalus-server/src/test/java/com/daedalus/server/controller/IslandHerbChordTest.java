// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.world.audio.Herb;
import com.daedalus.world.audio.HerbChord;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HRB 1 herb-chord record: bytes, bounds and host boundary. */
class IslandHerbChordTest {
    private static final Path DIR = Path.of("..", "docs", "contracts", "hrb-v1");
    private final com.fasterxml.jackson.databind.ObjectMapper json = new com.fasterxml.jackson.databind.ObjectMapper();

    private static java.security.Principal host() {
        return UsernamePasswordAuthenticationToken.authenticated("engine", "unused", List.of());
    }

    private static IslandAudioController.HerbRequest of(Object... idPotency) {
        var herbs = new ArrayList<IslandAudioController.HerbIn>();
        for (int i = 0; i < idPotency.length; i += 2) {
            herbs.add(new IslandAudioController.HerbIn((String) idPotency[i], (Double) idPotency[i + 1]));
        }
        return new IslandAudioController.HerbRequest(herbs);
    }

    @Test void fixtureMatchesControllerHttpAndGermanLocale() throws Exception {
        var controller = new IslandAudioController("engine");
        var request = json.readValue(Files.readString(DIR.resolve("mint-yarrow-sage-request.json")),
                IslandAudioController.HerbRequest.class);
        var expected = Files.readString(DIR.resolve("mint-yarrow-sage.hrb"));
        var old = Locale.getDefault();
        try {
            Locale.setDefault(Locale.GERMANY);
            assertThat(controller.herbChord(request, host())).isEqualTo(expected);
        } finally {
            Locale.setDefault(old);
        }
        var response = MockMvcBuilders.standaloneSetup(controller).build().perform(post("/api/v1/audio/herb-chord")
                .principal(host()).contentType("application/json").content(Files.readString(DIR.resolve("mint-yarrow-sage-request.json"))))
                .andExpect(status().isOk()).andReturn().getResponse();
        assertThat(response.getContentAsString()).isEqualTo(expected);
        assertThat(response.getContentType()).startsWith("text/plain");
    }

    @Test void wireAgreesWithCoreChordAndIsDeterministic() {
        var controller = new IslandAudioController("engine");
        var wire = controller.herbChord(of("mint", 1.0, "yarrow", 0.5, "sage", 0.75), host());
        var core = HerbChord.sound(List.of(new Herb("mint", 1.0), new Herb("yarrow", 0.5), new Herb("sage", 0.75)));
        var lines = wire.split("\n");
        assertThat(lines[0]).isEqualTo("HRB 1");
        assertThat(lines[1]).isEqualTo(String.format(Locale.ROOT, "chord %d %s %s %.3f", core.root(), core.quality(),
                core.effect().name(), core.strength()));
        assertThat(lines).hasSize(3 + core.frequencies().size());
        assertThat(lines[lines.length - 1]).isEqualTo("end");
        assertThat(wire).endsWith("end\n").isEqualTo(controller.herbChord(of("mint", 1.0, "yarrow", 0.5, "sage", 0.75), host()));
    }

    @Test void singleHerbAndEightHerbsAreAccepted() {
        var controller = new IslandAudioController("engine");
        assertThat(controller.herbChord(of("mint", 0.0), host())).startsWith("HRB 1\nchord ").contains(" unison STEADY ");
        var eight = new Object[16];
        for (int i = 0; i < 8; i++) {
            eight[2 * i] = "herb" + i;
            eight[2 * i + 1] = 1.0;
        }
        assertThat(controller.herbChord(of(eight), host())).startsWith("HRB 1\n").endsWith("end\n");
    }

    @Test void rejectsInvalidInputWithoutClamping() {
        var controller = new IslandAudioController("engine");
        var nine = new Object[18];
        for (int i = 0; i < 9; i++) {
            nine[2 * i] = "h" + i;
            nine[2 * i + 1] = 0.5;
        }
        var cases = new ArrayList<IslandAudioController.HerbRequest>(List.of(
                new IslandAudioController.HerbRequest(null),
                new IslandAudioController.HerbRequest(List.of()),
                of(nine),
                of("Mint", 0.5), of("", 0.5), of("a b", 0.5), of("x".repeat(33), 0.5), of("m\u00e9nt", 0.5),
                of("mint", -0.1), of("mint", 1.1), of("mint", Double.NaN), of("mint", Double.POSITIVE_INFINITY),
                of("mint", (Double) null), of((String) null, 0.5)));
        var withNull = new ArrayList<IslandAudioController.HerbIn>();
        withNull.add(null);
        cases.add(new IslandAudioController.HerbRequest(withNull));
        for (var bad : cases) {
            assertThatThrownBy(() -> controller.herbChord(bad, host())).hasMessageContaining("400");
        }
        assertThatThrownBy(() -> controller.herbChord(null, host())).hasMessageContaining("400");
    }

    @Test void hostBoundaryDeniesSpoofingAndMissingConfiguration() {
        var controller = new IslandAudioController("engine");
        for (java.security.Principal principal : java.util.Arrays.asList(null, (java.security.Principal) () -> "engine",
                UsernamePasswordAuthenticationToken.unauthenticated("engine", "unused"),
                UsernamePasswordAuthenticationToken.authenticated("other", "unused", List.of()),
                new AnonymousAuthenticationToken("key", "engine", List.of(new SimpleGrantedAuthority("ROLE_ANONYMOUS"))))) {
            assertThatThrownBy(() -> controller.herbChord(of("mint", 1.0), principal)).hasMessageContaining("403");
        }
        assertThatThrownBy(() -> new IslandAudioController("").herbChord(of("mint", 1.0), host())).hasMessageContaining("403");
    }

    @Test void malformedJsonIsBadRequestOverHttp() throws Exception {
        var mvc = MockMvcBuilders.standaloneSetup(new IslandAudioController("engine")).build();
        mvc.perform(post("/api/v1/audio/herb-chord").principal(host()).contentType("application/json").content("{\"herbs\":[{\"id\":\"MINT\",\"potency\":1}]}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/audio/herb-chord").principal(host()).contentType("application/json").content("not json"))
                .andExpect(status().isBadRequest());
    }
}