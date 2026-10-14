// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.world.*;
import com.daedalus.world.labyrinth.LabyrinthTerrain;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.assertj.core.api.Assertions.*;

class LabyrinthWorldHostTest {
    @TempDir Path temp;
    @Test void mountGeneratesPersistentChunksAndRestartKeepsEdits() {
        Path file=temp.resolve("world-zero.daew");
        WorldService zero=new WorldService(file,WorldId.ZERO,event->{});
        WorldHub hub=WorldHub.of(zero);
        assertThat(hub.create("labyrinth",WorldStyle.LABYRINTH,42,"The Labyrinth").result()).isEqualTo("CREATED");
        WorldService maze=hub.get("labyrinth");
        assertThat(maze.style()).isEqualTo(WorldStyle.LABYRINTH);
        assertThat(maze.copy("labyrinth").chunkCount()).isGreaterThan(0);
        var anchor=LabyrinthTerrain.spawn();
        assertThat(maze.copy("labyrinth").get(new BlockCoordinate(anchor.x(),0,anchor.z()))).isEqualTo(BlockType.STONE);
        // The same DAEW path used by the server retains edits when the registry is loaded again.
        World copy=maze.copy("labyrinth");copy.place(anchor,BlockType.GLASS);
        try { WorldStore.save(copy,temp.resolve("labyrinth.daew")); }
        catch(java.io.IOException ex) {throw new AssertionError(ex);}
        WorldHub restarted=WorldHub.of(new WorldService(file,WorldId.ZERO,event->{}));
        assertThat(restarted.get("labyrinth").copy("labyrinth").get(anchor)).isEqualTo(BlockType.GLASS);
        assertThat(restarted.get("labyrinth").raiseLabyrinth("labyrinth",123).result()).isEqualTo("ALREADY_LAID");
        assertThat(restarted.get("labyrinth").copy("labyrinth").get(anchor)).isEqualTo(BlockType.GLASS);
        assertThat(zero.raiseLabyrinth("world-zero",42).result()).isEqualTo("NOT_A_LABYRINTH");
        assertThat(zero.raiseLabyrinth("missing",42)).isNull();
        assertThat(hub.create("labyrinth",WorldStyle.LABYRINTH,43,"Second").result()).isEqualTo("EXISTS");
    }
}
