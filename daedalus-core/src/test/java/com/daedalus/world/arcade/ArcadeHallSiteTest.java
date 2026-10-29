// SPDX-License-Identifier: MIT

package com.daedalus.world.arcade;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandPlan;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class ArcadeHallSiteTest {

    /** Same pin as IslandGeneratorTest.GOLDEN_SEED_11: hall placement must never change island output. */
    static final String GOLDEN_SEED_11 = "bcd94a28cb5b3f744259568bc0039debd95db70c01d506bd56594f6987ef35d5";

    @Test
    void flagIsOffByDefault() {
        assertThat(System.getProperty(ArcadeHallSite.FLAG)).isNull();
        assertThat(ArcadeHallSite.enabled()).isFalse();
        IslandPlan p = IslandGenerator.generate(11);
        assertThat(ArcadeHallSite.siteIfEnabled(p, ArcadeHall.layout("corner_arcade").orElseThrow())).isEmpty();
    }

    @Test
    void islandsStayByteIdenticalWithTheFlagOnAndAfterSiting() {
        String before = IslandGenerator.generate(11).digest();
        String old = System.getProperty(ArcadeHallSite.FLAG);
        System.setProperty(ArcadeHallSite.FLAG, "true");
        try {
            IslandPlan p = IslandGenerator.generate(11);
            for (ArcadeHall.Layout l : ArcadeHall.layouts()) {
                ArcadeHallSite.siteIfEnabled(p, l);
            }
            assertThat(p.digest()).isEqualTo(before).isEqualTo(GOLDEN_SEED_11);
            assertThat(IslandGenerator.generate(11).digest()).isEqualTo(GOLDEN_SEED_11);
        } finally {
            if (old == null) {
                System.clearProperty(ArcadeHallSite.FLAG);
            } else {
                System.setProperty(ArcadeHallSite.FLAG, old);
            }
        }
    }

    @Test
    void sitesAreOnFlatLandWithAClearPathAndDeterministic() {
        int found = 0;
        for (long seed = 1; seed <= 40; seed++) {
            IslandPlan p = IslandGenerator.generate(seed);
            Map<BlockCoordinate, BlockType> blocks = p.blocks();
            for (ArcadeHall.Layout l : ArcadeHall.layouts()) {
                Optional<ArcadeHallSite.Site> s = ArcadeHallSite.find(p, l);
                assertThat(ArcadeHallSite.find(p, l)).isEqualTo(s);
                if (s.isEmpty()) {
                    continue;
                }
                found++;
                ArcadeHallSite.Site t = s.get();
                assertThat(t.width()).isEqualTo(l.widthM());
                assertThat(t.depth()).isEqualTo(l.depthM());
                // the cube under every footprint column's top is land, and nothing stands on the floor level
                for (int z = t.minZ(); z < t.minZ() + t.depth(); z++) {
                    for (int x = t.minX(); x < t.minX() + t.width(); x++) {
                        assertThat(blocks.get(new BlockCoordinate(x, t.floorY(), z))).as("clear at %d,%d", x, z).isNull();
                    }
                }
                assertThat(t.doorAnchor().z()).isEqualTo(t.minZ());
                assertThat(t.doorAnchor().z() - t.pathStart().z()).isEqualTo(ArcadeHallSite.approachLength());
                assertThat(t.doorAnchor().x()).isBetween(t.minX(), t.minX() + t.width() - 1);
            }
        }
        assertThat(found).as("at least one seed in 1..40 has room for a hall").isPositive();
    }
}
