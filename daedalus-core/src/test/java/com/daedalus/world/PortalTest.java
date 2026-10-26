// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class PortalTest {

    @Test
    void openAndSealAreNamedResults() {
        World world = World.zero();
        assertThat(world.portal().id()).isEqualTo(Portal.ZERO_ID);
        assertThat(world.portal().state()).isEqualTo(PortalState.SEALED);
        assertThat(world.openPortal()).isEqualTo(PortalResult.OPENED);
        assertThat(world.portal().state()).isEqualTo(PortalState.OPEN);
        assertThat(world.openPortal()).isEqualTo(PortalResult.ALREADY_OPEN);
        assertThat(world.sealPortal()).isEqualTo(PortalResult.SEALED);
        assertThat(world.sealPortal()).isEqualTo(PortalResult.ALREADY_SEALED);
    }

    @Test
    void openingThePortalBumpsRevisionAndInspectDoesNot() {
        World world = World.zero();
        long before = world.revision().value();
        world.portal();
        assertThat(world.revision().value()).isEqualTo(before);
        world.openPortal();
        assertThat(world.revision().value()).isEqualTo(before + 1);
        world.openPortal();
        assertThat(world.revision().value()).isEqualTo(before + 1);
    }
}
