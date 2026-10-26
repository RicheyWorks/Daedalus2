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
     *
     * <p>Moved once on purpose: ADR-019 gave every island a pier (old digest ed45f7d3…).
     */
    static final String GOLDEN_SEED_11 =
            "bcd94a28cb5b3f744259568bc0039debd95db70c01d506bd56594f6987ef35d5";

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
            // The rim can sit 22% past the radius (noise) and the pier runs PIER_LENGTH beyond it.
            int reach = (int) Math.ceil(radius * 1.22) + IslandGenerator.PIER_LENGTH + 2;
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
    void everyIslandHasAPierAnArkCanMoorAt() {
        for (long seed : new long[] {1, 11, 42, 99, 2026}) {
            IslandPlan plan = IslandGenerator.generate(seed);
            IslandTraits t = plan.traits();
            BlockCoordinate tip = new BlockCoordinate(t.dockX(), t.dockY(), t.dockZ());
            assertThat(plan.blocks().get(tip)).as("plank at the pier tip, seed %d", seed)
                    .isEqualTo(BlockType.WOOD);
            // The tip is clear above — an ark's passengers step onto open planks.
            assertThat(plan.blocks().get(new BlockCoordinate(t.dockX(), t.dockY() + 1, t.dockZ())))
                    .isNull();
            // Bollards stand either side of the tip.
            assertThat(plan.blocks().get(new BlockCoordinate(t.dockX() - 1, t.dockY() + 1, t.dockZ())))
                    .isEqualTo(BlockType.LOG);
            // The pier reaches past the island's ground: nothing solid under the tip's far end.
            assertThat(plan.blocks().get(new BlockCoordinate(t.dockX(), t.dockY() - 1, t.dockZ())))
                    .isNull();
            // No tree trunk stands on the pier.
            for (int z = t.dockZ() - IslandGenerator.PIER_LENGTH; z <= t.dockZ(); z++) {
                assertThat(plan.blocks().get(new BlockCoordinate(t.dockX(), t.dockY() + 1, z)))
                        .as("cube above pier at z=%d, seed %d", z, seed).isNotEqualTo(BlockType.LOG);
            }
        }
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
