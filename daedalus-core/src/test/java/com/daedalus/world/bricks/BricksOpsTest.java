// SPDX-License-Identifier: MIT

package com.daedalus.world.bricks;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.gate.GateOps;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The Bricks ground (ADR-034): a two-thick baseplate, a spawn pad, a runway on gate 0's line, and an obby
 * that is always beatable: every jump inside the avatar's reach, never more than one cube up, nothing
 * overhead, checkpoints on the way, a gold finish at the end, lava below.
 */
class BricksOpsTest {

    @Test
    void theBaseplateSpawnAndRunway() {
        BricksOps.Plan plan = BricksOps.plan(1);
        Map<BlockCoordinate, BlockType> c = plan.cubes();
        for (int x = BricksOps.MIN_X; x < BricksOps.MIN_X + BricksOps.SIDE; x += 7) {
            for (int z = BricksOps.MIN_Z; z < BricksOps.MIN_Z + BricksOps.SIDE; z += 7) {
                assertThat(c.get(new BlockCoordinate(x, 0, z))).isEqualTo(BlockType.BASEPLATE);
                assertThat(c.get(new BlockCoordinate(x, -1, z))).isEqualTo(BlockType.BASEPLATE);
            }
        }
        BlockCoordinate spawn = BricksOps.spawn();
        assertThat(c.get(new BlockCoordinate(spawn.x(), spawn.y() - 1, spawn.z()))).isEqualTo(BlockType.SPAWN);
        assertThat(c).doesNotContainKey(spawn);
        BlockCoordinate hangar = BricksOps.hangarBerth();
        assertThat(hangar.x()).isEqualTo(GateOps.center(0).x());
        assertThat(c.get(new BlockCoordinate(hangar.x() + 1, hangar.y() - 1, hangar.z()))).isEqualTo(BlockType.BRICK_WHITE);
        assertThat(c.get(new BlockCoordinate(hangar.x(), 1, -18))).isEqualTo(BlockType.BRICK_YELLOW);
        assertThat(BricksOps.runway().overlaps(BricksOps.corridor())).isFalse();
    }

    @Test
    void everyObbyIsBeatable() {
        for (long seed = 0; seed < 200; seed++) {
            BricksOps.Plan plan = BricksOps.plan(seed);
            List<BricksOps.Platform> run = new java.util.ArrayList<>(plan.obby());
            run.add(plan.finish());
            BricksOps.Platform from = new BricksOps.Platform(BricksOps.spawnPad().minX(), BricksOps.spawnPad().minZ(),
                    BricksOps.spawnPad().maxX(), BricksOps.spawnPad().maxZ(), 1, BlockType.SPAWN, true);
            int checkpoints = 0;
            for (BricksOps.Platform to : run) {
                assertThat(from.gapTo(to)).as("seed %d: a jump within reach", seed).isBetween(1.0, BricksOps.MAX_REACH);
                assertThat(to.y() - from.y()).as("seed %d: at most one up", seed).isLessThanOrEqualTo(1);
                assertThat(to.y()).isLessThan(BricksOps.HEIGHT - 4);
                // Room to land: nothing within two cubes above the top.
                for (int x = to.minX(); x <= to.maxX(); x++) {
                    for (int z = to.minZ(); z <= to.maxZ(); z++) {
                        assertThat(plan.cubes().get(new BlockCoordinate(x, to.y(), z))).isNotNull();
                        if (!(to == plan.finish() && x == to.standOn().x() && z == to.standOn().z() - 1)) {
                            assertThat(plan.cubes()).doesNotContainKey(new BlockCoordinate(x, to.y() + 1, z));
                            assertThat(plan.cubes()).doesNotContainKey(new BlockCoordinate(x, to.y() + 2, z));
                        }
                    }
                }
                assertThat(BricksOps.corridor().contains(new BlockCoordinate(to.minX(), to.y(), to.minZ()))).isTrue();
                assertThat(BricksOps.corridor().contains(new BlockCoordinate(to.maxX(), to.y(), to.maxZ()))).isTrue();
                if (to.checkpoint()) {
                    checkpoints++;
                }
                from = to;
            }
            assertThat(checkpoints).isEqualTo(BricksOps.PLATFORMS / BricksOps.CHECKPOINT_EVERY);
            assertThat(plan.obby().get(plan.obby().size() - 1).checkpoint()).as("the last jump starts from a checkpoint").isTrue();
        }
    }

    @Test
    void lavaLiesUnderTheWholeRunAndRespawnFindsTheLastCheckpoint() {
        BricksOps.Plan plan = BricksOps.plan(9);
        for (BricksOps.Platform p : plan.obby()) {
            assertThat(plan.cubes().get(new BlockCoordinate(p.minX(), 1, p.minZ()))).isEqualTo(BlockType.LAVA);
        }
        assertThat(plan.respawnAfter(-1)).isEqualTo(BricksOps.spawn());
        assertThat(plan.respawnAfter(4)).isEqualTo(BricksOps.spawn());
        assertThat(plan.respawnAfter(5)).isEqualTo(plan.obby().get(5).standOn());
        assertThat(plan.respawnAfter(10)).isEqualTo(plan.obby().get(5).standOn());
        assertThat(plan.respawnAfter(99)).isEqualTo(plan.obby().get(17).standOn());
    }

    @Test
    void theSandboxKeepsThePlateTheObbyAndTheRunwaySafe() {
        assertThat(BricksOps.protects(new BlockCoordinate(80, 1, -100))).as("open plate").isFalse();
        assertThat(BricksOps.protects(new BlockCoordinate(80, BricksOps.HEIGHT, -100))).isFalse();
        assertThat(BricksOps.protects(new BlockCoordinate(80, BricksOps.HEIGHT + 1, -100))).as("above the limit").isTrue();
        assertThat(BricksOps.protects(new BlockCoordinate(80, 0, -100))).as("the plate itself").isTrue();
        assertThat(BricksOps.protects(new BlockCoordinate(20, 5, -60))).as("the obby").isTrue();
        assertThat(BricksOps.protects(BricksOps.spawn())).as("the spawn").isTrue();
        assertThat(BricksOps.protects(new BlockCoordinate(48, 9, -40))).as("over the runway").isTrue();
        assertThat(BricksOps.protects(new BlockCoordinate(-17, 1, -100))).as("off the plate").isTrue();
        assertThat(BricksOps.protects(new BlockCoordinate(80, 1, BricksOps.MIN_Z + BricksOps.SIDE))).isTrue();
    }

    @Test
    void theSeedChangesTheObbyAndTheGatesStillFit() {
        assertThat(BricksOps.plan(3).cubes()).isEqualTo(BricksOps.plan(3).cubes());
        assertThat(BricksOps.plan(3).obby()).isNotEqualTo(BricksOps.plan(4).obby());
        World w = new World(new WorldId("bricks"));
        assertThat(BricksOps.build(w, BricksOps.plan(3))).isTrue();
        assertThat(BricksOps.build(w, BricksOps.plan(3))).isFalse();
        for (int g = 0; g < GateOps.MAX_GATES; g++) {
            assertThat(GateOps.fits(w, g)).as("gate %d", g).isTrue();
        }
    }
}
