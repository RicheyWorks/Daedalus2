// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import com.daedalus.world.*;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.assertj.core.api.Assertions.*;

class OceanTerrainTest {
    @TempDir Path tmp;

    @Test void oceanHasWaterOverSandAndDeepRockWithoutLand() {
        for (long seed : new long[]{0, 1, -1, Long.MAX_VALUE, Long.MIN_VALUE}) {
            for (int x = -200; x <= 200; x += 7) for (int z = -200; z <= 200; z += 11) {
                int floor = OceanTerrain.floorY(seed, x, z);
                assertThat(floor).isBetween(-55, -24);
                assertThat(OceanTerrain.block(seed, x, floor, z)).isEqualTo(BlockType.SAND);
                assertThat(OceanTerrain.block(seed, x, floor - 3, z)).isEqualTo(BlockType.STONE);
                assertThat(OceanTerrain.block(seed, x, floor + 1, z)).isEqualTo(BlockType.WATER);
                assertThat(OceanTerrain.block(seed, x, 0, z)).isEqualTo(BlockType.WATER);
                assertThat(OceanTerrain.block(seed, x, 2, z)).isEqualTo(BlockType.AIR);
                assertThat(Math.abs(floor - OceanTerrain.floorY(seed, x + 1, z))).isLessThanOrEqualTo(1);
                assertThat(Math.abs(floor - OceanTerrain.floorY(seed, x, z + 1))).isLessThanOrEqualTo(1);
            }
        }
    }

    @Test void dockSpawnAndVesselBerthsHaveClearance() {
        var spawn = OceanTerrain.spawn();
        assertThat(OceanTerrain.block(3, spawn.x(), spawn.y() - 1, spawn.z())).isEqualTo(BlockType.WOOD);
        assertThat(OceanTerrain.block(3, spawn.x(), spawn.y(), spawn.z())).isEqualTo(BlockType.AIR);
        for (var berth : List.of(OceanTerrain.boatBerth(), OceanTerrain.submarineBerth())) {
            for (int x = -2; x <= 2; x++) for (int y = -1; y <= 1; y++) for (int z = -2; z <= 2; z++) {
                assertThat(OceanTerrain.block(3, berth.x()+x, berth.y()+y, berth.z()+z))
                        .isIn(BlockType.AIR, BlockType.WATER);
            }
        }
    }

    @Test void chunksMatchAbsoluteCoordinatesAcrossNegativeSeams() {
        for (var at : List.of(new ChunkCoordinate(-1,-1,-1), new ChunkCoordinate(0,-2,0), new ChunkCoordinate(1,0,1))) {
            Chunk chunk = OceanTerrain.chunk(127, at);
            for (int x=0;x<16;x++) for(int y=0;y<16;y++) for(int z=0;z<16;z++) {
                assertThat(chunk.get(x,y,z)).isEqualTo(OceanTerrain.block(127,at.x()*16+x,at.y()*16+y,at.z()*16+z));
            }
            assertThat(chunk).isEqualTo(OceanTerrain.chunk(127,at));
        }
        assertThat(OceanTerrain.chunk(1,new ChunkCoordinate(0,1,0)).isEmpty()).isTrue();
        assertThat(OceanTerrain.chunk(1,new ChunkCoordinate(0,-10,0)).get(0,0,0)).isEqualTo(BlockType.STONE);
    }

    @Test void seedChangesTerrainAndChunkResultsAreIndependent() {
        assertThat(OceanTerrain.chunk(1,new ChunkCoordinate(4,-3,5)))
                .isNotEqualTo(OceanTerrain.chunk(2,new ChunkCoordinate(4,-3,5)));
        Chunk changed=OceanTerrain.chunk(1,new ChunkCoordinate(0,-1,0));
        changed.set(0,0,0,BlockType.GLASS);
        assertThat(OceanTerrain.chunk(1,new ChunkCoordinate(0,-1,0)).get(0,0,0)).isEqualTo(BlockType.WATER);
    }

    @Test void worldRoundTripsThroughExistingSaveFormatAndKeepsPlayerEdits() throws Exception {
        var addresses=List.of(new ChunkCoordinate(-1,-1,-1),new ChunkCoordinate(0,-1,0),new ChunkCoordinate(0,0,0));
        World world=OceanTerrain.newWorld(new WorldId("ocean"),42,addresses);
        var dug=new BlockCoordinate(0,-1,0);var built=new BlockCoordinate(0,3,0);
        world.remove(dug);world.place(built,BlockType.GLASS);
        Path file=tmp.resolve("ocean.daew");WorldStore.save(world,file);
        World restored=WorldStore.load(file);
        assertThat(restored.id()).isEqualTo(world.id());
        assertThat(restored.revision()).isEqualTo(world.revision());
        assertThat(restored.get(dug)).isEqualTo(BlockType.AIR);
        assertThat(restored.get(built)).isEqualTo(BlockType.GLASS);
        for(var at:world.chunkKeys())assertThat(restored.chunk(at)).isEqualTo(world.chunk(at));
    }

    @Test void boundsAndBatchValidationRefuseBeforeCreatingAWorld() {
        var at=new ChunkCoordinate(0,-1,0);
        assertThatThrownBy(()->OceanTerrain.newWorld(new WorldId("ocean"),0,List.of(at,at))).isInstanceOf(IllegalArgumentException.class);
        var many=new ArrayList<ChunkCoordinate>();for(int i=0;i<65;i++)many.add(new ChunkCoordinate(i,-1,0));
        assertThatThrownBy(()->OceanTerrain.newWorld(new WorldId("ocean"),0,many)).isInstanceOf(IllegalArgumentException.class);
        for(int axis:new int[]{Integer.MIN_VALUE,Integer.MAX_VALUE}) {
            assertThatThrownBy(()->OceanTerrain.chunk(0,new ChunkCoordinate(axis,0,0))).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(()->OceanTerrain.chunk(0,new ChunkCoordinate(0,axis,0))).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(()->OceanTerrain.chunk(0,new ChunkCoordinate(0,0,axis))).isInstanceOf(IllegalArgumentException.class);
        }
        assertThat(OceanTerrain.chunk(0,new ChunkCoordinate(Integer.MAX_VALUE/16,0,0))).isNotNull();
        assertThat(OceanTerrain.chunk(0,new ChunkCoordinate(Integer.MIN_VALUE/16,0,0))).isNotNull();
        assertThat(OceanTerrain.newWorld(new WorldId("ocean"),0,List.of(new ChunkCoordinate(0,1,0))).chunkCount()).isZero();
    }
}
