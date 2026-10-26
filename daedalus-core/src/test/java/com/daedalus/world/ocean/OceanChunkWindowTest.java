// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import com.daedalus.world.*;
import java.io.IOException;
import java.nio.file.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.assertj.core.api.Assertions.*;

class OceanChunkWindowTest {
    @TempDir Path tmp;

    @Test void traversalIsBoundedAndEditsSurviveEvictionAndRestart() throws Exception {
        Path root=tmp.resolve("sea");var edited=new BlockCoordinate(-1,-1,0);
        try(var window=new OceanChunkWindow(root,42,4)) {
            assertThat(window.set(edited,BlockType.GLASS)).isEqualTo(BlockType.WATER);
            for(int x=0;x<80;x++) {
                window.get(new BlockCoordinate(x*16,-1,0));
                assertThat(window.residentCount()).isLessThanOrEqualTo(4);
            }
            assertThat(window.get(edited)).isEqualTo(BlockType.GLASS);
            window.evictAll();assertThat(window.residentCount()).isZero();
            assertThat(window.get(edited)).isEqualTo(BlockType.GLASS);
        }
        try(var window=new OceanChunkWindow(root,42,1)){assertThat(window.get(edited)).isEqualTo(BlockType.GLASS);}
    }

    @Test void warmupIsNearestFirstBudgetedAndStableForNegativeCoordinates() throws Exception {
        Path root=tmp.resolve("sea");
        try(var window=new OceanChunkWindow(root,0,4)) {
            var centre=new BlockCoordinate(-1,-1,-1);
            assertThat(window.warmAround(centre,2,1,0)).isZero();
            assertThat(window.residentCount()).isZero();
            assertThat(window.warmAround(centre,2,1,1)).isEqualTo(1);
            assertThat(Files.exists(root.resolve("-1_-1_-1.daew"))).isTrue();
            assertThat(window.warmAround(centre,2,1,2)).isEqualTo(2);
            assertThat(window.warmAround(centre,2,1,64)).isEqualTo(1);
            assertThat(window.warmAround(centre,2,1,64)).isZero();
            assertThat(window.residentCount()).isEqualTo(4);
        }
    }

    @Test void snapshotsCannotMutateCachedOrPersistedChunks() throws Exception {
        try(var window=new OceanChunkWindow(tmp.resolve("sea"),0,2)) {
            var at=new BlockCoordinate(0,-1,0);
            Chunk copy=window.snapshot(at.chunk());copy.set(at.localX(),at.localY(),at.localZ(),BlockType.GLASS);
            assertThat(window.get(at)).isEqualTo(BlockType.WATER);
            assertThat(window.set(at,BlockType.WATER)).isEqualTo(BlockType.WATER);
            window.evictAll();assertThat(window.get(at)).isEqualTo(BlockType.WATER);
        }
    }

    @Test void failedSaveDoesNotPublishCandidateEditAndFailedLoadDoesNotEvict() throws Exception {
        Path root=tmp.resolve("sea");
        try(var window=new OceanChunkWindow(root,0,1)) {
            var at=new BlockCoordinate(0,-1,0);window.get(at);
            Files.writeString(root.resolve("0_-1_0.daew"),"corrupt");
            assertThatThrownBy(()->window.set(at,BlockType.GLASS)).isInstanceOf(IOException.class);
            assertThat(window.get(at)).isEqualTo(BlockType.WATER);
            Files.writeString(root.resolve("1_-1_0.daew"),"corrupt");
            assertThatThrownBy(()->window.get(new BlockCoordinate(16,-1,0))).isInstanceOf(IOException.class);
            assertThat(window.residentCount()).isEqualTo(1);
            assertThat(window.get(at)).isEqualTo(BlockType.WATER);
        }
    }

    @Test void addressEdgesAndInvalidBudgetsAreBounded() throws Exception {
        assertThatThrownBy(()->new OceanChunkWindow(tmp.resolve("bad"),0,0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->new OceanChunkWindow(tmp.resolve("bad"),0,4097)).isInstanceOf(IllegalArgumentException.class);
        assertThat(Files.exists(tmp.resolve("bad"))).isFalse();
        try(var window=new OceanChunkWindow(tmp.resolve("sea"),0,2)) {
            assertThatThrownBy(()->window.warmAround(new BlockCoordinate(0,0,0),9,0,1)).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(()->window.warmAround(new BlockCoordinate(0,0,0),0,5,1)).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(()->window.warmAround(new BlockCoordinate(0,0,0),0,0,65)).isInstanceOf(IllegalArgumentException.class);
            assertThat(window.warmAround(new BlockCoordinate(Integer.MIN_VALUE,Integer.MIN_VALUE,Integer.MIN_VALUE),1,1,2)).isEqualTo(2);
            assertThat(window.warmAround(new BlockCoordinate(Integer.MAX_VALUE,Integer.MAX_VALUE,Integer.MAX_VALUE),1,1,2)).isEqualTo(2);
            assertThat(window.residentCount()).isEqualTo(2);
        }
    }

    @Test void closeReleasesWriterAndRefusesFurtherAccess() throws Exception {
        Path root=tmp.resolve("sea");var window=new OceanChunkWindow(root,0,1);
        window.close();window.close();
        assertThatThrownBy(()->window.get(new BlockCoordinate(0,0,0))).isInstanceOf(IOException.class);
        assertThatThrownBy(window::evictAll).isInstanceOf(IOException.class);
        try(var reopened=new OceanChunkWindow(root,0,1)){assertThat(reopened.residentCount()).isZero();}
    }
}
