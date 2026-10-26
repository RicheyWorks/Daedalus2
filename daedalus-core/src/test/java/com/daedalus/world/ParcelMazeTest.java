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

class ParcelMazeTest {

    @TempDir
    Path tmp;

    @Test
    void bindingAMazeRefBumpsRevisionAndTheSameRefDoesNot() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        ParcelId id = world.parcels().get(0).id();
        long before = world.revision().value();
        assertThat(world.parcels().get(0).mazeRef()).isEmpty();
        assertThat(world.bindMaze(id, "  00000000-0000-4000-8000-000000000007  "))
                .isEqualTo(ParcelMazeResult.BOUND);
        assertThat(world.parcels().get(0).mazeRef())
                .isEqualTo("00000000-0000-4000-8000-000000000007");
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThat(world.bindMaze(id, "00000000-0000-4000-8000-000000000007"))
                .isEqualTo(ParcelMazeResult.ALREADY_BOUND);
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThatThrownBy(() -> world.bindMaze(id, "   "))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void aMazeRefSurvivesRestart() throws Exception {
        World live = World.zero();
        StampOps.apply(live, new StampRequest(live.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        live.bindMaze(live.parcels().get(0).id(), "00000000-0000-4000-8000-000000000007");
        Path file = tmp.resolve("maze-ref.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.parcels().get(0).mazeRef())
                .isEqualTo("00000000-0000-4000-8000-000000000007");
    }
}
