// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.TrapResult;
import com.daedalus.world.TrapState;
import com.daedalus.world.World;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Builder recipes drive {@link WorldOps} only. No agent.* verbs.
 */
class WorldBuilderTest {

    @Test
    void aRecipePlacesAndArmsThroughWorldOps() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        BlockCoordinate at = new BlockCoordinate(3, 0, 1);
        long before = world.revision().value();
        List<DriveTrace.Step> trace = builder.run(List.of(
                new WorldBuilder.Step(at, "block.place", BlockType.STONE),
                new WorldBuilder.Step(at, "block.inspect", null),
                new WorldBuilder.Step(at, "trap.arm", null)));
        assertThat(world.get(at)).isEqualTo(BlockType.STONE);
        assertThat(world.revision().value()).isGreaterThan(before);
        assertThat(world.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(trace)
                .extracting(DriveTrace.Step::capability)
                .containsExactly("block.place", "block.inspect", "trap.arm");
        assertThat(trace.get(2).result()).isEqualTo(TrapResult.ARMED.toString());
        AccountingReport report = AccountingHarness.account(
                WorldZeroCapabilities.registry(), WorldZeroDrive.DRIVEN);
        AccountingHarness.requireAccounted(report);
        assertThat(report.unaccountedCount()).isZero();
    }

    @Test
    void anInventedAgentVerbIsRejected() {
        WorldBuilder builder = new WorldBuilder(World.zero());
        assertThatThrownBy(() -> builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "agent.build", BlockType.WOOD)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unknown capability");
        assertThatThrownBy(() -> builder.run((WorldBuilder.Step) null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Step");
        assertThatThrownBy(() -> builder.run((List<WorldBuilder.Step>) null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Recipe");
    }
}
