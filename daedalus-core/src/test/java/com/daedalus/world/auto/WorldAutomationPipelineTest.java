// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Door;
import com.daedalus.world.DoorResult;
import com.daedalus.world.Npc;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelVerb;
import com.daedalus.world.Portal;
import com.daedalus.world.Trap;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Discover → address → drive → observe → trace → account.
 */
class WorldAutomationPipelineTest {

    @Test
    void driveIsObservedAndTracedWithoutMovingRevisionOnObserve() {
        World world = World.zero();
        AutomationSession session = new AutomationSession(world);
        BlockCoordinate at = new BlockCoordinate(2, 0, 1);
        WorldAddress addressed = session.address(at);

        assertThat(addressed.worldId()).isEqualTo(WorldId.ZERO);
        assertThat(addressed.at()).isEqualTo(at);
        assertThat(session.address()).isEqualTo(addressed);

        session.drive("block.place", BlockType.STONE);
        Observation afterPlace = session.observe();
        long revisionAfterPlace = world.revision().value();
        assertThat(afterPlace.worldId()).isEqualTo("world-zero");
        assertThat(afterPlace.blockType()).isEqualTo("STONE");
        assertThat(afterPlace.doorState()).isEqualTo("CLOSED");
        assertThat(afterPlace.place()).isEmpty();
        assertThat(afterPlace.lot()).isEmpty();
        assertThat(afterPlace.occupant()).isEmpty();
        assertThat(afterPlace.acl()).isEmpty();
        assertThat(afterPlace.drive()).isEqualTo("block.place AIR");
        assertThat(afterPlace.driveActor()).isEqualTo(Parcel.SYSTEM_OWNER);
        assertThat(afterPlace.driveAt()).isEqualTo("2,0,1");
        assertThat(afterPlace.x()).isEqualTo(2);
        assertThat(afterPlace.y()).isZero();
        assertThat(afterPlace.z()).isEqualTo(1);
        assertThat(afterPlace.revision()).isEqualTo(revisionAfterPlace);
        assertThat(session.observe().revision()).isEqualTo(revisionAfterPlace);

        session.drive("block.remove", null);
        Observation afterRemove = session.observe();
        assertThat(afterRemove.blockType()).isEqualTo("AIR");
        assertThat(afterRemove.revision()).isGreaterThan(revisionAfterPlace);

        assertThat(session.trace()).hasSize(2);
        assertThat(session.trace().get(0).capability()).isEqualTo("block.place");
        assertThat(session.trace().get(0).result()).isEqualTo("AIR");
        assertThat(session.trace().get(0).revisionAfter()).isEqualTo(revisionAfterPlace);
        assertThat(session.trace().get(1).capability()).isEqualTo("block.remove");
    }

    @Test
    void driveWithoutAddressIsRejected() {
        AutomationSession session = new AutomationSession(World.zero());
        assertThatThrownBy(() -> session.drive("world.inspect", null))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Address");
        assertThatThrownBy(session::observe)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Address");
    }

    @Test
    void observeNamesTheOccupantOnThatCube() {
        World world = World.zero();
        AutomationSession session = new AutomationSession(world);
        session.address(Door.ZERO_AT);
        assertThat(session.observe().occupant()).isEqualTo("door");
        session.address(Trap.ZERO_AT);
        assertThat(session.observe().occupant()).isEqualTo("trap");
        session.address(Portal.ZERO_AT);
        assertThat(session.observe().occupant()).isEqualTo("portal");
        session.address(Npc.ZERO_AT);
        assertThat(session.observe().occupant()).isEqualTo("npc");
        session.address(new BlockCoordinate(9, 0, 9));
        assertThat(session.observe().occupant()).isEmpty();
        assertThat(session.observe().acl()).isEmpty();
        assertThat(world.occupantAt(Door.ZERO_AT)).isEqualTo("door");
        assertThat(world.occupantAt(Trap.ZERO_AT)).isEqualTo("trap");
        assertThat(world.occupantAt(Portal.ZERO_AT)).isEqualTo("portal");
        assertThat(world.occupantAt(Npc.ZERO_AT)).isEqualTo("npc");
        assertThat(world.occupantAt(new BlockCoordinate(99, 0, 99))).isEmpty();
        assertThat(world.occupantAt(null)).isEmpty();
        assertThat(WorldOps.occupantAt(world, Door.ZERO_AT)).isEqualTo(world.occupantAt(Door.ZERO_AT));
        assertThat(WorldOps.occupantAt(null, Door.ZERO_AT)).isEmpty();
        WorldOps.drive(world, "stamp.apply", new BlockCoordinate(0, 0, 0), null);
        session.address(Door.ZERO_AT);
        assertThat(session.observe().acl()).isEmpty();
        world.grant(world.parcels().get(0).id(), "bob", ParcelVerb.BLOCK_PLACE);
        assertThat(session.observe().acl()).isEqualTo("bob block.place");
        session.address(new BlockCoordinate(9, 0, 9));
        assertThat(session.observe().acl()).isEmpty();
    }

    @Test
    void observeRejectsAnAddressFromAnotherWorld() {
        World world = World.zero();
        WorldAddress other = new WorldAddress(new WorldId("other-world"),
                new BlockCoordinate(0, 0, 0));
        assertThatThrownBy(() -> Observation.take(world, other))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("other-world");
    }

    @Test
    void aFullPipelineLeavesUnaccountedAtZero() {
        CapabilityRegistry discovered = WorldZeroCapabilities.registry();
        AutomationSession session = new AutomationSession(World.zero());
        session.address(new BlockCoordinate(1, 0, 0));
        for (String capability : WorldZeroDrive.DRIVEN) {
            session.drive(capability, BlockType.DIRT);
        }
        assertThat(WorldOps.asDoorResult(session.drive("door.close", null)))
                .isIn(DoorResult.CLOSED, DoorResult.ALREADY_CLOSED);
        AccountingReport report = AccountingHarness.account(discovered, WorldZeroDrive.DRIVEN);
        AccountingHarness.requireAccounted(report);
        assertThat(session.observe().doorState()).isEqualTo("CLOSED");
        assertThat(session.trace().size()).isGreaterThanOrEqualTo(WorldZeroDrive.DRIVEN.size());
        assertThat(session.trace())
                .extracting(DriveTrace.Step::capability)
                .containsAll(WorldZeroDrive.DRIVEN);
    }
}
