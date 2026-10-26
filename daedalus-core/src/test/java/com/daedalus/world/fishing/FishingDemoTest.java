// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class FishingDemoTest {

    @Test
    void reportCoversDayNightStormAndAParlay() {
        String r = FishingDemo.run(FishTestData.read("prism-fish.json"), 7, 800);
        assertThat(r).startsWith("Fishing odds: prism, 6 fish, seed 7");
        assertThat(r).contains("day, reaction", "night, reaction", "storm, reaction", "simulated 800 casts",
                "Storm Parlay [Reedling, Prismscale Koi]");
        assertThat(FishingDemo.run(FishTestData.read("prism-fish.json"), 7, 800)).isEqualTo(r);
    }

    @Test
    void printReadsATableFromDisk() throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (PrintStream out = new PrintStream(bytes, true, StandardCharsets.UTF_8)) {
            FishingDemo.print(out, new String[] {"../data/rpg/skyisland-fish.json", "3", "200"});
        }
        String r = bytes.toString(StandardCharsets.UTF_8);
        assertThat(r).startsWith("Fishing odds: shattered-planet, 6 fish, seed 3");
        assertThat(r).contains("Storm Parlay [rillperch, basin_ray]");
    }
}
