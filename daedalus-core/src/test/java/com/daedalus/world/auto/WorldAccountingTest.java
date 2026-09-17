// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.DoorResult;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Discover and drive are different lists. UNACCOUNTED &gt; 0 fails the harness.
 */
class WorldAccountingTest {

    @Test
    void worldZeroCapabilitiesAreDrivenAndUnaccountedIsZero() {
        CapabilityRegistry discovered = WorldZeroCapabilities.registry();
        AccountingReport report = AccountingHarness.account(discovered, WorldZeroDrive.DRIVEN);
        AccountingHarness.requireAccounted(report);
        assertThat(report.unaccountedCount()).isZero();
        assertThat(report.discovered()).containsExactlyInAnyOrderElementsOf(WorldZeroDrive.DRIVEN);

        AutomationSession session = new AutomationSession(World.zero());
        session.address(new BlockCoordinate(1, 0, 0));
        session.drive("world.inspect", null);
        session.drive("chunk.inspect", null);
        session.drive("block.inspect", null);
        session.drive("block.place", BlockType.STONE);
        session.drive("block.remove", null);
        session.drive("door.inspect", null);
        assertThat(WorldOps.asDoorResult(session.drive("door.open", null)))
                .isEqualTo(DoorResult.OPENED);
        assertThat(WorldOps.asDoorResult(session.drive("door.close", null)))
                .isEqualTo(DoorResult.CLOSED);
        session.drive("trap.inspect", null);
        assertThat(WorldOps.asTrapResult(session.drive("trap.arm", null)))
                .isEqualTo(TrapResult.ARMED);
        assertThat(WorldOps.asTrapResult(session.drive("trap.disarm", null)))
                .isEqualTo(TrapResult.DISARMED);
        assertThat(session.observe().doorState()).isEqualTo("CLOSED");
        assertThat(session.trace()).hasSize(11);
    }

    @Test
    void anUndrivenCapabilityFailsTheHarness() {
        CapabilityRegistry discovered = WorldZeroCapabilities.registry(java.util.List.of("portal.open"));
        AccountingReport report = AccountingHarness.account(discovered, WorldZeroDrive.DRIVEN);
        assertThat(report.unaccountedCount()).isEqualTo(1);
        assertThat(report.unaccounted()).containsExactly("portal.open");
        assertThatThrownBy(() -> AccountingHarness.requireAccounted(report))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("UNACCOUNTED=1");
    }
}
