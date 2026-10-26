// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The demo encounter tells its story and is deterministic; the benchmark runs. */
class BattlefieldDemoTest {

    @Test
    void encounterPicksWoodThenMovesAwayFromFireThenRegrows(@TempDir Path dir) throws Exception {
        List<BattlefieldDemo.Frame> f = BattlefieldDemo.run(42);
        assertThat(f).hasSize(4);
        BattlefieldEcology scene = BattlefieldDemo.scene(42);
        double[] first = f.get(0).cover();
        assertThat(scene.at(first[0], first[1])).isIn(Vegetation.OAK, Vegetation.PINE);
        assertThat(BattlefieldDemo.text(f.get(2))).contains("*");
        double[] during = f.get(2).cover();
        assertThat(during).isNotNull();
        assertThat(during[0] != first[0] || during[1] != first[1]).as("cover moved off the blast").isTrue();
        assertThat(BattlefieldDemo.text(f.get(3))).doesNotContain("*");
        assertThat(BattlefieldDemo.text(BattlefieldDemo.run(42).get(2))).isEqualTo(BattlefieldDemo.text(f.get(2)));
        Path png = dir.resolve("demo.png");
        BattlefieldDemo.png(f, png);
        assertThat(Files.size(png)).isGreaterThan(1000);
    }

    @Test
    void benchmarkRuns() {
        BattlefieldBench.Stat[] s = BattlefieldBench.run(64, 20);
        assertThat(s).hasSize(4);
        assertThat(s[0].medianUs()).isPositive();
    }
}