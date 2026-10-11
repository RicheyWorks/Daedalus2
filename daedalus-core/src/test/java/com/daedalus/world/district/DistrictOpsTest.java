// SPDX-License-Identifier: MIT

package com.daedalus.world.district;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.gate.GateOps;
import org.junit.jupiter.api.Test;

import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The Parcels district (ADR-033): sixty claimable plots around a plaza, the same layout in every world,
 * streets with sidewalks, a helipad on gate 0's line, show plots that never leave their plot or pass the
 * height limit, and sky gates that still fit above it all.
 */
class DistrictOpsTest {

    @Test
    void sixtyPlotsOfSixteenAroundAPlaza() {
        assertThat(DistrictOps.SIDE).isEqualTo(148);
        int plots = 0;
        Set<BlockCoordinate> footprint = new HashSet<>();
        for (int n = 0; n < 64; n++) {
            final int plaza = n;
            if (!DistrictOps.isPlot(n)) {
                assertThat(DistrictOps.isPlaza(n)).as("plot %d", n).isTrue();
                assertThatThrownBy(() -> DistrictOps.plotBounds(plaza)).isInstanceOf(IllegalArgumentException.class);
                continue;
            }
            plots++;
            ParcelBounds b = DistrictOps.plotBounds(n);
            assertThat(b.maxX() - b.minX() + 1).isEqualTo(16);
            assertThat(b.maxZ() - b.minZ() + 1).isEqualTo(16);
            assertThat(b.minY()).isEqualTo(DistrictOps.GROUND_Y);
            assertThat(b.maxY()).isEqualTo(DistrictOps.HEIGHT);
            assertThat(b.minX()).isGreaterThanOrEqualTo(DistrictOps.MIN_X + DistrictOps.ROAD);
            assertThat(b.maxX()).isLessThan(DistrictOps.MIN_X + DistrictOps.SIDE - DistrictOps.ROAD);
            for (int x = b.minX(); x <= b.maxX(); x++) {
                for (int z = b.minZ(); z <= b.maxZ(); z++) {
                    assertThat(footprint.add(new BlockCoordinate(x, 0, z))).as("plots never overlap").isTrue();
                    assertThat(DistrictOps.plotAt(x, z)).isEqualTo(n);
                }
            }
            assertThat(b.overlaps(DistrictOps.plaza())).isFalse();
        }
        assertThat(plots).isEqualTo(DistrictOps.CLAIMABLE).isEqualTo(60);
        assertThat(DistrictOps.isPlot(-1)).isFalse();
        assertThat(DistrictOps.isPlot(64)).isFalse();
        // Row along +Z, column along +X.
        assertThat(DistrictOps.plotBounds(1).minX()).isEqualTo(DistrictOps.plotBounds(0).minX() + 16);
        assertThat(DistrictOps.plotBounds(8).minZ()).isEqualTo(DistrictOps.plotBounds(0).minZ() + 16);
        assertThat(DistrictOps.plotBounds(2).minX()).as("a street between blocks").isEqualTo(DistrictOps.plotBounds(1).maxX() + 5);
    }

    @Test
    void theHelipadIsOnThePlazaOnGateZerosLine() {
        BlockCoordinate pad = DistrictOps.padBerth();
        assertThat(pad.x()).isEqualTo(GateOps.center(0).x());
        assertThat(DistrictOps.plaza().contains(new BlockCoordinate(pad.x(), 0, pad.z()))).isTrue();
        assertThat(DistrictOps.plotAt(pad.x(), pad.z())).isEqualTo(-1);
        DistrictOps.Plan plan = DistrictOps.plan(7);
        assertThat(plan.cubes().get(new BlockCoordinate(pad.x() - 5, 0, pad.z() - 5))).isEqualTo(BlockType.HELIPAD);
        assertThat(plan.cubes().get(new BlockCoordinate(pad.x() - 3, 0, pad.z()))).as("the H").isEqualTo(BlockType.PAVING);
        assertThat(plan.cubes()).doesNotContainKey(pad);
        assertThat(DistrictOps.PAD_SLOT).isGreaterThan(GateOps.GATE_BASE + GateOps.MAX_GATES);
    }

    @Test
    void groundIsThreeDeepWithStreetsAndSidewalks() {
        DistrictOps.Plan plan = DistrictOps.plan(1);
        Map<BlockType, Integer> top = new EnumMap<>(BlockType.class);
        for (int x = DistrictOps.MIN_X; x < DistrictOps.MIN_X + DistrictOps.SIDE; x++) {
            for (int z = DistrictOps.MIN_Z; z < DistrictOps.MIN_Z + DistrictOps.SIDE; z++) {
                assertThat(plan.cubes().get(new BlockCoordinate(x, -2, z))).isEqualTo(BlockType.STONE);
                assertThat(plan.cubes().get(new BlockCoordinate(x, -1, z))).isNotNull();
                top.merge(plan.cubes().get(new BlockCoordinate(x, 0, z)), 1, Integer::sum);
            }
        }
        assertThat(top).containsKeys(BlockType.GRASS, BlockType.ROAD, BlockType.PAVING, BlockType.HELIPAD);
        // The ring road: sidewalk on its outer edge, asphalt inside.
        assertThat(plan.cubes().get(new BlockCoordinate(DistrictOps.MIN_X, 0, -60))).isEqualTo(BlockType.PAVING);
        assertThat(plan.cubes().get(new BlockCoordinate(DistrictOps.MIN_X + 1, 0, -60))).isEqualTo(BlockType.ROAD);
        assertThat(plan.cubes()).doesNotContainKey(new BlockCoordinate(DistrictOps.MIN_X - 1, 0, -60));
    }

    @Test
    void showPlotsStayInsideTheirPlotAndUnderTheLimit() {
        for (long seed = 0; seed < 20; seed++) {
            DistrictOps.Plan plan = DistrictOps.plan(seed);
            for (Map.Entry<BlockCoordinate, BlockType> e : plan.cubes().entrySet()) {
                BlockCoordinate at = e.getKey();
                assertThat(at.y()).isBetween(-2, DistrictOps.HEIGHT);
                if (at.y() > 0) {
                    assertThat(DistrictOps.plotAt(at.x(), at.z())).as("%s above ground belongs to a plot", at).isNotNegative();
                }
            }
        }
    }

    @Test
    void theSeedDecidesTheShowsAndOnlyTheShows() {
        DistrictOps.Plan a = DistrictOps.plan(42);
        assertThat(DistrictOps.plan(42).cubes()).isEqualTo(a.cubes());
        DistrictOps.Plan b = DistrictOps.plan(43);
        assertThat(b.cubes()).isNotEqualTo(a.cubes());
        assertThat(b.plots()).extracting(DistrictOps.Plot::bounds).isEqualTo(a.plots().stream().map(DistrictOps.Plot::bounds).toList());
        Map<DistrictOps.Show, Integer> shows = new EnumMap<>(DistrictOps.Show.class);
        for (long seed = 0; seed < 30; seed++) {
            for (DistrictOps.Plot p : DistrictOps.plan(seed).plots()) {
                shows.merge(p.show(), 1, Integer::sum);
            }
        }
        assertThat(shows).containsOnlyKeys(DistrictOps.Show.values());
        assertThat(shows.get(DistrictOps.Show.LAWN)).as("about half wait for an owner")
                .isBetween(30 * 60 * 40 / 100, 30 * 60 * 56 / 100);
    }

    @Test
    void theDistrictBuildsWholeAndTheGatesStillFitAboveIt() {
        World w = new World(new WorldId("parcels"));
        DistrictOps.Plan plan = DistrictOps.plan(5);
        assertThat(DistrictOps.build(w, plan)).isTrue();
        assertThat(w.get(new BlockCoordinate(0, -2, -10))).isEqualTo(BlockType.STONE);
        assertThat(DistrictOps.build(w, plan)).as("not twice").isFalse();
        for (int g = 0; g < GateOps.MAX_GATES; g++) {
            assertThat(GateOps.fits(w, g)).as("gate %d", g).isTrue();
        }
        for (BlockCoordinate at : GateOps.plan(0).keySet()) {
            assertThat(at.y()).as("the gates are out of reach of the height limit").isGreaterThan(DistrictOps.HEIGHT);
        }
    }
}
