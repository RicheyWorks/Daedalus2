// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class TrapTest {

    @Test
    void armAndDisarmAreNamedResults() {
        World world = World.zero();
        assertThat(world.trap().id()).isEqualTo(Trap.ZERO_ID);
        assertThat(world.trap().state()).isEqualTo(TrapState.DISARMED);
        assertThat(world.armTrap()).isEqualTo(TrapResult.ARMED);
        assertThat(world.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(world.armTrap()).isEqualTo(TrapResult.ALREADY_ARMED);
        assertThat(world.disarmTrap()).isEqualTo(TrapResult.DISARMED);
        assertThat(world.disarmTrap()).isEqualTo(TrapResult.ALREADY_DISARMED);
    }

    @Test
    void armingTheTrapBumpsRevisionAndInspectDoesNot() {
        World world = World.zero();
        long before = world.revision().value();
        world.trap();
        assertThat(world.revision().value()).isEqualTo(before);
        world.armTrap();
        assertThat(world.revision().value()).isEqualTo(before + 1);
        world.armTrap();
        assertThat(world.revision().value()).isEqualTo(before + 1);
    }
}
