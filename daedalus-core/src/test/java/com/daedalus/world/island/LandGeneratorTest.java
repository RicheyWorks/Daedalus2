// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelBounds;

import java.util.EnumMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

/** Lands (ADR-050): big, deep, inside the claim box, layered, with ores by depth and a richness roll. */
class LandGeneratorTest {

    @Test
    void sameSeedSameLand() {
        assertThat(LandGenerator.generate(7, 46).digest()).isEqualTo(LandGenerator.generate(7, 46).digest());
        assertThat(LandGenerator.generate(7, 46).digest()).isNotEqualTo(LandGenerator.generate(8, 46).digest());
    }

    @Test
    void radiusDispatchKeepsIslandsAndAddsLands() {
        assertThat(IslandGenerator.generate(3, 46).digest()).isEqualTo(LandGenerator.generate(3, 46).digest());
        assertThat(IslandGenerator.generate(3, 18).traits().columns()).isLessThan(2000);
        assertThatThrownBy(() -> IslandGenerator.generate(3, 30)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LandGenerator.generate(3, 47)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void bigAndDeepAndInsideTheClaimBox() {
        for (long seed = 1; seed <= 6; seed++) {
            IslandPlan plan = LandGenerator.generate(seed, LandGenerator.MAX_RADIUS);
            ParcelBounds claim = IslandOps.claimBounds(0);
            BlockCoordinate o = IslandOps.slot(0);
            int minX = Integer.MAX_VALUE, maxX = Integer.MIN_VALUE, minZ = Integer.MAX_VALUE, maxZ = Integer.MIN_VALUE;
            for (BlockCoordinate c : plan.blocks().keySet()) {
                BlockCoordinate w = new BlockCoordinate(o.x() + c.x(), o.y() + c.y(), o.z() + c.z());
                assertThat(claim.contains(w)).as("seed %d cube %s inside the claim", seed, c).isTrue();
                minX = Math.min(minX, c.x());
                maxX = Math.max(maxX, c.x());
                minZ = Math.min(minZ, c.z());
                maxZ = Math.max(maxZ, c.z());
            }
            assertThat(maxX - minX).as("seed %d width", seed).isGreaterThanOrEqualTo(70);
            assertThat(maxZ - minZ).as("seed %d length", seed).isGreaterThanOrEqualTo(70);
            assertThat(plan.traits().bottom()).as("seed %d depth", seed).isLessThanOrEqualTo(-38);
            assertThat(plan.traits().columns()).as("seed %d area", seed).isGreaterThan(3500);
        }
    }

    @Test
    void layeredWithOresAtTheirDepths() {
        IslandPlan plan = LandGenerator.generate(11, 44);
        Map<BlockType, int[]> band = new EnumMap<>(BlockType.class);   // min y, max y, count
        for (Map.Entry<BlockCoordinate, BlockType> e : plan.blocks().entrySet()) {
            int[] b = band.computeIfAbsent(e.getValue(), t -> new int[] {Integer.MAX_VALUE, Integer.MIN_VALUE, 0});
            b[0] = Math.min(b[0], e.getKey().y());
            b[1] = Math.max(b[1], e.getKey().y());
            b[2]++;
        }
        for (BlockType t : new BlockType[] {BlockType.GRASS, BlockType.DIRT, BlockType.STONE, BlockType.DEEPSTONE,
                BlockType.HEARTSTONE, BlockType.COAL_ORE, BlockType.COPPER_ORE, BlockType.IRON_ORE, BlockType.WATER}) {
            assertThat(band).as("has %s", t).containsKey(t);
        }
        assertThat(band.get(BlockType.COAL_ORE)[1]).as("coal is shallow").isGreaterThan(band.get(BlockType.IRON_ORE)[1]);
        assertThat(band.get(BlockType.DEEPSTONE)[1]).as("deepstone is below stone's top").isLessThan(band.get(BlockType.STONE)[1]);
        assertThat(band.get(BlockType.HEARTSTONE)[0]).as("heart at the bottom").isLessThan(-25);
        assertThat(plan.traits().waterfall()).isTrue();
    }

    @Test
    void richnessRollsAndLegendaryLandsHoldStarmetal() {
        int[] tally = new int[3];
        long legendary = -1;
        for (long seed = 1; seed <= 400; seed++) {
            LandGenerator.Richness r = LandGenerator.richness(seed);
            tally[r.ordinal()]++;
            if (r == LandGenerator.Richness.LEGENDARY && legendary < 0) {
                legendary = seed;
            }
        }
        assertThat(tally[0]).as("most lands are common").isBetween(240, 320);
        assertThat(tally[1]).as("a quarter are rich").isBetween(70, 130);
        assertThat(tally[2]).as("one in twenty legendary").isBetween(8, 35);
        assertThat(LandGenerator.survey(LandGenerator.generate(legendary, 44))).containsKey(BlockType.STARMETAL);
        long common = 1;
        while (LandGenerator.richness(common) != LandGenerator.Richness.COMMON) {
            common++;
        }
        assertThat(LandGenerator.survey(LandGenerator.generate(common, 44))).doesNotContainKey(BlockType.STARMETAL);
    }
}
