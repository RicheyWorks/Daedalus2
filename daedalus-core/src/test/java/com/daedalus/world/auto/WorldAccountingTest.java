// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.DoorResult;
import com.daedalus.world.NpcResult;
import com.daedalus.world.ParcelDenyResult;
import com.daedalus.world.ParcelGrantResult;
import com.daedalus.world.ParcelLeaseResult;
import com.daedalus.world.PortalResult;
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
        session.drive("portal.inspect", null);
        assertThat(WorldOps.asPortalResult(session.drive("portal.open", null)))
                .isEqualTo(PortalResult.OPENED);
        assertThat(WorldOps.asPortalResult(session.drive("portal.seal", null)))
                .isEqualTo(PortalResult.SEALED);
        session.drive("npc.inspect", null);
        assertThat(WorldOps.asNpcResult(session.drive("npc.talk", null)))
                .isEqualTo(NpcResult.SPOKE);
        assertThat(WorldOps.asNpcResult(session.drive("npc.hush", null)))
                .isEqualTo(NpcResult.HUSHED);
        assertThat(WorldOps.asLeaseResult(session.drive("parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.NO_PARCEL);
        assertThat(WorldOps.asStampResult(session.drive("stamp.apply", null)).outcome())
                .isEqualTo("APPLIED");
        assertThat(WorldOps.asGrantResult(session.drive("parcel.grant", null)))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.asDenyResult(session.drive("parcel.deny", null)))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(session.observe().doorState()).isEqualTo("CLOSED");
        assertThat(session.trace()).hasSize(21);
    }

    @Test
    void anUndrivenCapabilityFailsTheHarness() {
        CapabilityRegistry discovered = WorldZeroCapabilities.registry(java.util.List.of("shop.open"));
        AccountingReport report = AccountingHarness.account(discovered, WorldZeroDrive.DRIVEN);
        assertThat(report.unaccountedCount()).isEqualTo(1);
        assertThat(report.unaccounted()).containsExactly("shop.open");
        assertThatThrownBy(() -> AccountingHarness.requireAccounted(report))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("UNACCOUNTED=1");
    }
}
