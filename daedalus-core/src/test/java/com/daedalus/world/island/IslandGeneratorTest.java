// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class IslandGeneratorTest {

    /**
     * Seed 11 at the default radius, as SHA-256 over every cube. Changing the generator so this
     * moves is allowed — it is a decision, and the new digest goes in the same commit with a line
     * in the CHANGELOG saying which islands changed shape.
     */
    static final String GOLDEN_SEED_11 =
            "ed45f7d3eceaaf8d132dad2d35cfbd0bdd14dc8a475709ae185e506cb5ee1670";

    @Test
    void sameSeedSameIslandOnEveryCall() {
        IslandPlan a = IslandGenerator.generate(11);
        IslandPlan b = IslandGenerator.generate(11);
        assertThat(a.digest()).isEqualTo(b.digest());
        assertThat(a.traits()).isEqualTo(b.traits());
        assertThat(a.blocks()).isEqualTo(b.blocks());
    }

    @Test
    void seedElevenIsPinned() {
        assertThat(IslandGenerator.generate(11).digest()).isEqualTo(GOLDEN_SEED_11);
    }

    @Test
    void differentSeedsAreDifferentIslands() {
        assertThat(IslandGenerator.generate(11).digest())
                .isNotEqualTo(IslandGenerator.generate(12).digest());
    }

    @Test
    void anIslandHasEveryLayerAndFeature() {
        IslandPlan plan = IslandGenerator.generate(11);
        Set<BlockType> kinds = EnumSet.noneOf(BlockType.class);
        kinds.addAll(plan.blocks().values());
        assertThat(kinds).contains(BlockType.GRASS, BlockType.DIRT, BlockType.STONE,
                BlockType.SAND, BlockType.WATER, BlockType.LOG, BlockType.LEAVES,
                BlockType.CRYSTAL, BlockType.CLOUD);
        assertThat(kinds).doesNotContain(BlockType.AIR);
        IslandTraits t = plan.traits();
        assertThat(t.blocks()).isEqualTo(plan.blocks().size());
        assertThat(t.trees()).isGreaterThanOrEqualTo(3);
        assertThat(t.blossomTrees()).isPositive().isLessThanOrEqualTo(t.trees());
        assertThat(t.pondColumns()).isPositive();
        assertThat(t.crystals()).isBetween(5, 10);
        assertThat(t.top()).isGreaterThan(0);
        assertThat(t.bottom()).isLessThan(-10);
    }

    @Test
    void theIslandStaysInsideItsFootprint() {
        for (int radius : new int[] {IslandGenerator.MIN_RADIUS, 18, IslandGenerator.MAX_RADIUS}) {
            IslandPlan plan = IslandGenerator.generate(7, radius);
            int reach = radius + 6 + 3 + 3;
            for (BlockCoordinate c : plan.blocks().keySet()) {
                assertThat(Math.abs(c.x())).as("x of %s at radius %d", c, radius)
                        .isLessThanOrEqualTo(reach);
                assertThat(Math.abs(c.z())).as("z of %s at radius %d", c, radius)
                        .isLessThanOrEqualTo(reach);
                assertThat(c.y()).isBetween(-40, 40);
            }
            // Fits the island lane: neighbours are SLOT_SPACING apart.
            assertThat(2 * reach).isLessThan(IslandOps.SLOT_SPACING);
        }
    }

    @Test
    void groundIsLayeredGrassOverDirtOverStone() {
        IslandPlan plan = IslandGenerator.generate(11);
        Map<BlockCoordinate, BlockType> blocks = plan.blocks();
        int checked = 0;
        for (Map.Entry<BlockCoordinate, BlockType> e : blocks.entrySet()) {
            if (e.getValue() != BlockType.GRASS) {
                continue;
            }
            BlockCoordinate c = e.getKey();
            BlockType below = blocks.get(new BlockCoordinate(c.x(), c.y() - 1, c.z()));
            assertThat(below).as("under grass at %s", c).isEqualTo(BlockType.DIRT);
            checked++;
        }
        assertThat(checked).isGreaterThan(200);
    }

    @Test
    void radiusOutsideTheRangeIsRefused() {
        assertThatThrownBy(() -> IslandGenerator.generate(1, IslandGenerator.MIN_RADIUS - 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("radius");
        assertThatThrownBy(() -> IslandGenerator.generate(1, IslandGenerator.MAX_RADIUS + 1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void noiseIsAPureFunctionOfSeedAndPosition() {
        IslandNoise a = new IslandNoise(99);
        IslandNoise b = new IslandNoise(99);
        for (int i = 0; i < 200; i++) {
            double x = i * 0.37 - 30;
            double z = i * -0.21 + 11;
            double v = a.fractal(x, z, 1, 3);
            assertThat(v).isEqualTo(b.fractal(x, z, 1, 3)).isBetween(-1.0, 1.0);
        }
        assertThat(new IslandNoise(99).value(3.3, 4.4, 0))
                .isNotEqualTo(new IslandNoise(100).value(3.3, 4.4, 0));
    }
}
