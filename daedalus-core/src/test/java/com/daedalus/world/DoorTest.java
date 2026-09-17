// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class DoorTest {

    @Test
    void openAndCloseAreNamedResults() {
        World world = World.zero();
        assertThat(world.door().id()).isEqualTo(Door.ZERO_ID);
        assertThat(world.door().state()).isEqualTo(DoorState.CLOSED);
        assertThat(world.openDoor()).isEqualTo(DoorResult.OPENED);
        assertThat(world.door().state()).isEqualTo(DoorState.OPEN);
        assertThat(world.openDoor()).isEqualTo(DoorResult.ALREADY_OPEN);
        assertThat(world.closeDoor()).isEqualTo(DoorResult.CLOSED);
        assertThat(world.closeDoor()).isEqualTo(DoorResult.ALREADY_CLOSED);
    }

    @Test
    void openingTheDoorBumpsRevisionAndInspectDoesNot() {
        World world = World.zero();
        long before = world.revision().value();
        world.door();
        assertThat(world.revision().value()).isEqualTo(before);
        world.openDoor();
        assertThat(world.revision().value()).isEqualTo(before + 1);
        world.openDoor();
        assertThat(world.revision().value()).isEqualTo(before + 1);
    }
}
