// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.companion.TonicBrewer.RolledBrew;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class TonicSecondRollTest {
    private static final List<String> HERBS = List.of("Furfern", "Pawmint", "Barkbalm");
    private static TonicBrewer brewer;

    @BeforeAll
    static void load() throws Exception {
        Path p = Path.of("..", "tools", "islands", "kennel-isle", "tonics.json");
        if (!Files.exists(p)) {
            p = Path.of("tools", "islands", "kennel-isle", "tonics.json");
        }
        brewer = new TonicBrewer(TonicBook.load(p));
    }

    @Test
    void sameSeedSameResult() {
        for (long s = 0; s < 200; s++) {
            assertThat(brewer.brew(HERBS, "Labyrinth", "other", 1, false, s))
                .isEqualTo(brewer.brew(HERBS, "Labyrinth", "other", 1, false, s));
        }
    }

    @Test
    void labyrinthRollsAboutTenPercent() {
        int hits = 0;
        for (long s = 0; s < 10_000; s++) {
            if (TonicBrewer.secondRoll(s, "tonic_barkbalm_pawmint_furfern")) {
                hits++;
            }
        }
        assertThat(hits).isBetween(850, 1150);
    }

    @Test
    void otherCoatsNeverRollAndMatchUnseeded() {
        for (long s = 0; s < 500; s++) {
            RolledBrew rb = brewer.brew(HERBS, "Spots", "other", 1, false, s).orElseThrow();
            assertThat(rb.secondRoll()).isFalse();
            assertThat(rb.brew()).isEqualTo(brewer.brew(HERBS, "Spots", "other", 1, false).orElseThrow());
        }
    }

    @Test
    void secondRollDoublesFactorUnderCap() {
        double base = brewer.brew(HERBS, "Labyrinth", "other", 1, false).orElseThrow().factor();
        boolean sawHit = false;
        for (long s = 0; s < 200; s++) {
            RolledBrew rb = brewer.brew(HERBS, "Labyrinth", "other", 1, false, s).orElseThrow();
            if (rb.secondRoll()) {
                sawHit = true;
                assertThat(rb.brew().factor()).isEqualTo(Math.min(2.0, Math.round(base * 2 * 1e6) / 1e6));
            } else {
                assertThat(rb.brew().factor()).isEqualTo(base);
            }
            assertThat(rb.brew().factor()).isLessThanOrEqualTo(2.0);
        }
        assertThat(sawHit).isTrue();
    }
}
