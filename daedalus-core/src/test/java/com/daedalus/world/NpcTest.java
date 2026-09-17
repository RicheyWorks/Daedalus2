// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class NpcTest {

    @Test
    void talkAndHushAreNamedResults() {
        World world = World.zero();
        assertThat(world.npc().id()).isEqualTo(Npc.ZERO_ID);
        assertThat(world.npc().state()).isEqualTo(NpcState.IDLE);
        assertThat(world.talkNpc()).isEqualTo(NpcResult.SPOKE);
        assertThat(world.npc().state()).isEqualTo(NpcState.SPEAKING);
        assertThat(world.talkNpc()).isEqualTo(NpcResult.ALREADY_SPEAKING);
        assertThat(world.hushNpc()).isEqualTo(NpcResult.HUSHED);
        assertThat(world.hushNpc()).isEqualTo(NpcResult.ALREADY_IDLE);
    }

    @Test
    void talkingToTheNpcBumpsRevisionAndInspectDoesNot() {
        World world = World.zero();
        long before = world.revision().value();
        world.npc();
        assertThat(world.revision().value()).isEqualTo(before);
        world.talkNpc();
        assertThat(world.revision().value()).isEqualTo(before + 1);
        world.talkNpc();
        assertThat(world.revision().value()).isEqualTo(before + 1);
    }
}
