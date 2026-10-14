// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.world.*;
import com.daedalus.world.export.Glb;
import com.daedalus.world.export.WorldMesher;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import com.daedalus.engine.MazeGrid;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.HashSet;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.assertj.core.api.Assertions.*;

class LabyrinthTerrainTest {
    @TempDir Path temp;

    @Test void physicalWalkHasFloorHeadroomAndReachesExitForDifferentSeeds() {
        for (long seed : new long[]{0, 42, -1, Long.MIN_VALUE, Long.MAX_VALUE}) {
            World world=new World(new WorldId("labyrinth"));
            assertThat(LabyrinthTerrain.build(world,seed).ok()).isTrue();
            var queue=new ArrayDeque<BlockCoordinate>();var seen=new HashSet<BlockCoordinate>();
            queue.add(LabyrinthTerrain.spawn());seen.add(LabyrinthTerrain.spawn());
            while(!queue.isEmpty()) {
                var at=queue.remove();
                assertThat(world.get(new BlockCoordinate(at.x(),0,at.z()))).isEqualTo(BlockType.STONE);
                for (int[] d:new int[][]{{1,0},{-1,0},{0,1},{0,-1}}) {
                    var next=new BlockCoordinate(at.x()+d[0],1,at.z()+d[1]);
                    if (world.get(new BlockCoordinate(next.x(),0,next.z()))==BlockType.STONE
                            &&world.get(next)==BlockType.AIR
                            &&world.get(new BlockCoordinate(next.x(),2,next.z()))==BlockType.AIR&&seen.add(next)) queue.add(next);
                }
            }
            assertThat(seen).contains(LabyrinthTerrain.exit());
            int walkable=0;
            for(int z=LabyrinthTerrain.ORIGIN.z();z<LabyrinthTerrain.ORIGIN.z()+LabyrinthTerrain.SIDE;z++) {
                for(int x=LabyrinthTerrain.ORIGIN.x();x<LabyrinthTerrain.ORIGIN.x()+LabyrinthTerrain.SIDE;x++) {
                    assertThat(world.get(new BlockCoordinate(x,0,z))).isEqualTo(BlockType.STONE);
                    if(world.get(new BlockCoordinate(x,1,z))==BlockType.AIR)walkable++;
                    else assertThat(world.get(new BlockCoordinate(x,3,z))).isEqualTo(BlockType.STONE);
                }
            }
            assertThat(seen).hasSize(walkable);
        }
    }

    @Test void deterministicTerrainSurvivesSaveAndProtectsExistingEdits() throws Exception {
        World first=new World(new WorldId("labyrinth"));World second=new World(new WorldId("labyrinth"));
        LabyrinthTerrain.build(first,42);LabyrinthTerrain.build(second,42);
        Path a=temp.resolve("a.daew"),b=temp.resolve("b.daew");
        WorldStore.save(first,a);WorldStore.save(second,b);
        assertThat(Files.readAllBytes(a)).isEqualTo(Files.readAllBytes(b));
        World loaded=WorldStore.load(a);long revision=loaded.revision().value();
        assertThat(LabyrinthTerrain.build(loaded,43).ok()).isFalse();
        assertThat(loaded.revision().value()).isEqualTo(revision);
        WorldStore.save(loaded,b);assertThat(Files.readAllBytes(a)).isEqualTo(Files.readAllBytes(b));
        World occupied=new World(new WorldId("occupied"));
        occupied.place(LabyrinthTerrain.spawn(),BlockType.GLASS);
        assertThat(LabyrinthTerrain.build(occupied,42).ok()).isFalse();
        assertThat(occupied.get(LabyrinthTerrain.spawn())).isEqualTo(BlockType.GLASS);
        World reserved=new World(new WorldId("reserved"));
        reserved.claimParcel(new ParcelBounds(0,0,0,1,1,1),"builder","kept");
        assertThat(LabyrinthTerrain.build(reserved,42).ok()).isFalse();
    }

    @Test void seededMazeExportsThroughTheExistingRenderer() {
        World world=new World(new WorldId("labyrinth"));LabyrinthTerrain.build(world,42);
        var meshes=WorldMesher.meshGreedy(world);
        assertThat(meshes).isNotEmpty();
        byte[] glb=Glb.write(meshes,"Labyrinth starter");
        var header=ByteBuffer.wrap(glb).order(ByteOrder.LITTLE_ENDIAN);
        assertThat(header.getInt()).isEqualTo(0x46546c67);
        assertThat(header.getInt()).isEqualTo(2);
        assertThat(header.getInt()).isEqualTo(glb.length);
    }

    @Test void scaledStampPreservesTheDefaultAndRejectsInvalidScale() {
        MazeGrid maze=new MazeGrid(1,1);var origin=new BlockCoordinate(0,0,0);var id=new WorldId("scaled");
        assertThat(new StampRequest(id,origin,maze,0,3).tileScale()).isEqualTo(1);
        assertThat(StampOps.boundsOf(origin,maze,3,3)).isEqualTo(new ParcelBounds(0,0,0,8,3,8));
        for(int bad:new int[]{0,5}) {
            assertThatIllegalArgumentException().isThrownBy(()->new StampRequest(id,origin,maze,0,3,bad));
            assertThatIllegalArgumentException().isThrownBy(()->StampOps.boundsOf(origin,maze,3,bad));
        }
        assertThatExceptionOfType(ArithmeticException.class).isThrownBy(()->StampOps.boundsOf(
                new BlockCoordinate(Integer.MAX_VALUE,0,0),maze,3,3));
    }
}
