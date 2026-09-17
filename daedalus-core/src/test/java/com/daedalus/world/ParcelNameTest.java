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

class ParcelNameTest {

    @TempDir
    Path tmp;

    @Test
    void namingAParcelBumpsRevisionAndTheSameNameDoesNot() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        ParcelId id = world.parcels().get(0).id();
        long before = world.revision().value();
        assertThat(world.parcels().get(0).placeName()).isEmpty();
        assertThat(world.nameParcel(id, "  Willow Walk  ")).isEqualTo(ParcelNameResult.NAMED);
        assertThat(world.parcels().get(0).placeName()).isEqualTo("Willow Walk");
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThat(world.nameParcel(id, "Willow Walk")).isEqualTo(ParcelNameResult.ALREADY_NAMED);
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThatThrownBy(() -> world.nameParcel(id, "   "))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void aPlaceNameSurvivesRestart() throws Exception {
        World live = World.zero();
        StampOps.apply(live, new StampRequest(live.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        live.nameParcel(live.parcels().get(0).id(), "Willow Walk");
        Path file = tmp.resolve("named.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.parcels().get(0).placeName()).isEqualTo("Willow Walk");
    }
}
