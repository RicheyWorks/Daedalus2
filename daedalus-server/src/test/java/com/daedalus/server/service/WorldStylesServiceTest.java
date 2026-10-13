// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.BlockType;
import com.daedalus.world.WorldStyle;
import com.daedalus.world.gate.GateOps;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Each style's raise refuses the wrong world and a second laying; gates link both ways and drop cleanly. */
class WorldStylesServiceTest {

    @TempDir
    Path tmp;

    private WorldHub hub() {
        return new WorldHub(new WorldService(tmp.resolve("world-zero.daew"), e -> { }), e -> { });
    }

    @Test
    void eachRaiseRefusesTheWrongStyleAndASecondLaying() {
        WorldHub hub = hub();
        WorldService zero = hub.get("world-zero");
        assertThat(zero.raiseDistrict("world-zero", 1).result()).isEqualTo("NOT_A_DISTRICT");
        assertThat(zero.raiseBricks("world-zero", 1).result()).isEqualTo("NOT_BRICKS");
        assertThat(zero.raiseGallery("world-zero", 1).result()).isEqualTo("NOT_A_GALLERY");
        assertThat(zero.raiseDistrict("elsewhere", 1)).isNull();
        assertThat(zero.raiseBricks("elsewhere", 1)).isNull();
        assertThat(zero.raiseGallery("elsewhere", 1)).isNull();

        hub.create("par", WorldStyle.PARCELS, 3, "Par");
        hub.create("bri", WorldStyle.BRICKS, 3, "Bri");
        hub.create("gal", WorldStyle.GALLERY, 3, "Gal");
        // a world of each style was laid when it was created, so laying it again is refused, revision unchanged
        WorldService par = hub.get("par");
        long before = par.revision("par");
        WorldService.DistrictWrite again = par.raiseDistrict("par", 3);
        assertThat(again.result()).isEqualTo("ALREADY_LAID");
        assertThat(again.revision()).isEqualTo(before);
        assertThat(again.plots()).isPositive();
        assertThat(hub.get("bri").raiseBricks("bri", 3).result()).isEqualTo("ALREADY_LAID");
        assertThat(hub.get("gal").raiseGallery("gal", 3).result()).isEqualTo("ALREADY_LAID");
        assertThat(hub.get("bri").raiseDistrict("bri", 3).result()).isEqualTo("NOT_A_DISTRICT");
    }

    @Test
    void gatesLinkBothWaysAndDroppingOneClearsItsCubes() {
        WorldHub hub = hub();
        hub.create("isle-two", WorldStyle.SKY_ISLANDS, 42, "Isle Two");
        assertThat(hub.openGate("world-zero", "nowhere").result()).isEqualTo("NO_SUCH_WORLD");
        assertThat(hub.openGate("world-zero", "world-zero").result()).isEqualTo("SAME_WORLD");
        WorldHub.GateWrite w = hub.openGate("world-zero", "isle-two");
        assertThat(w.result()).isEqualTo("OPENED");
        assertThat(hub.openGate("isle-two", "world-zero").result()).isEqualTo("ALREADY_LINKED");
        WorldService zero = hub.get("world-zero");
        assertThat(zero.gates("world-zero")).hasSize(1);
        var portalCube = GateOps.plan(w.fromGate()).entrySet().iterator().next();
        assertThat(zero.copy("world-zero").get(portalCube.getKey())).isEqualTo(portalCube.getValue());
        long rev = zero.revision("world-zero");
        zero.dropGate("world-zero", w.fromGate());
        assertThat(zero.gates("world-zero")).isEmpty();
        assertThat(zero.copy("world-zero").get(portalCube.getKey())).isEqualTo(BlockType.AIR);
        assertThat(zero.revision("world-zero")).isGreaterThan(rev);
        long after = zero.revision("world-zero");
        zero.dropGate("world-zero", w.fromGate());      // already gone: nothing changes
        zero.dropGate("elsewhere", w.fromGate());       // not this world: nothing changes
        assertThat(zero.revision("world-zero")).isEqualTo(after);
    }
}
