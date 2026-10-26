// SPDX-License-Identifier: MIT

package com.daedalus.world;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ParcelLeaseTest {

    @TempDir
    Path tmp;

    @Test
    void leasingAParcelBumpsRevisionAndTheSameLeaseDoesNot() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        ParcelId id = world.parcels().get(0).id();
        long before = world.revision().value();
        assertThat(world.parcels().get(0).leaseId()).isEmpty();
        assertThat(world.leaseParcel(id, "  tenant-willow  ")).isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(world.parcels().get(0).leaseId()).isEqualTo("tenant-willow");
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThat(world.leaseParcel(id, "tenant-willow")).isEqualTo(ParcelLeaseResult.ALREADY_LEASED);
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThatThrownBy(() -> world.leaseParcel(id, "   "))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void aLeaseIdSurvivesRestartAndKeepsThePlaceName() throws Exception {
        World live = World.zero();
        StampOps.apply(live, new StampRequest(live.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        ParcelId id = live.parcels().get(0).id();
        live.nameParcel(id, "Willow Walk");
        live.leaseParcel(id, "tenant-willow");
        Path file = tmp.resolve("leased.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.parcels().get(0).placeName()).isEqualTo("Willow Walk");
        assertThat(reloaded.parcels().get(0).leaseId()).isEqualTo("tenant-willow");
    }
}
