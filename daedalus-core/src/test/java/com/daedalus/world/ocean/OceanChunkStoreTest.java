// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import com.daedalus.world.*;
import java.io.IOException;
import java.nio.file.*;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.assertj.core.api.Assertions.*;

class OceanChunkStoreTest {
    @TempDir Path tmp;
    private final ChunkCoordinate at = new ChunkCoordinate(-1,-1,0);

    @Test void generationEditsAndClearedChunksSurviveReopen() throws Exception {
        Path root=tmp.resolve("sea");
        try(var store=new OceanChunkStore(root,9)) {
            Chunk chunk=store.loadOrGenerate(at);
            assertThat(chunk).isEqualTo(OceanTerrain.chunk(9,at));
            chunk.set(2,3,4,BlockType.GLASS);store.save(at,chunk);
        }
        try(var store=new OceanChunkStore(root,9)) {
            assertThat(store.loadOrGenerate(at).get(2,3,4)).isEqualTo(BlockType.GLASS);
            Chunk cleared=store.loadOrGenerate(at);
            for(int x=0;x<16;x++)for(int y=0;y<16;y++)for(int z=0;z<16;z++)cleared.set(x,y,z,BlockType.AIR);
            store.save(at,cleared);
        }
        try(var store=new OceanChunkStore(root,9)) {
            assertThat(store.loadOrGenerate(at).isEmpty()).isTrue();
            assertThat(store.loadOrGenerate(at).revision()).isGreaterThan(4096);
            assertThat(Files.exists(root.resolve("-1_-1_0.daew"))).isTrue();
        }
    }

    @Test void missingAirChunksAreRecordedAndReturnedChunksDoNotMutateStorage() throws Exception {
        Path root=tmp.resolve("sea");
        try(var store=new OceanChunkStore(root,0)) {
            var air=new ChunkCoordinate(0,2,0);
            assertThat(store.loadOrGenerate(air).isEmpty()).isTrue();
            assertThat(Files.exists(root.resolve("0_2_0.daew"))).isTrue();
            Chunk copy=store.loadOrGenerate(at);copy.set(0,0,0,BlockType.GLASS);
            assertThat(store.loadOrGenerate(at).get(0,0,0)).isEqualTo(BlockType.WATER);
        }
    }

    @Test void directoryHasOneWriterAndCanBeReopenedAfterClose() throws Exception {
        Path root=tmp.resolve("sea");
        var first=new OceanChunkStore(root,1);
        try {
            assertThatThrownBy(()->new OceanChunkStore(root,1)).isInstanceOf(IOException.class).hasMessageContaining("owned");
        } finally { first.close(); }
        first.close();
        assertThatThrownBy(()->first.loadOrGenerate(at)).isInstanceOf(IOException.class);
        assertThatThrownBy(()->first.save(at,new Chunk())).isInstanceOf(IOException.class);
        try(var second=new OceanChunkStore(root,1)){assertThat(second.loadOrGenerate(at)).isNotNull();}
    }

    @Test void seedVersionAndMissingMetadataNeverSilentlyAdoptOldChunks() throws Exception {
        Path root=tmp.resolve("sea");
        try(var store=new OceanChunkStore(root,1)){store.loadOrGenerate(at);}
        assertThatThrownBy(()->new OceanChunkStore(root,2)).isInstanceOf(IOException.class).hasMessageContaining("mismatch");
        Files.writeString(root.resolve("ocean.properties"),"format=1\ngenerator=99\nseed=1\n");
        assertThatThrownBy(()->new OceanChunkStore(root,1)).isInstanceOf(IOException.class).hasMessageContaining("mismatch");
        Files.delete(root.resolve("ocean.properties"));
        assertThatThrownBy(()->new OceanChunkStore(root,1)).isInstanceOf(IOException.class).hasMessageContaining("without metadata");
    }

    @Test void corruptAndForeignRecordsRefuseWithoutRegenerationOrOverwrite() throws Exception {
        Path root=tmp.resolve("sea");
        try(var store=new OceanChunkStore(root,1)) {
            Path record=root.resolve("-1_-1_0.daew");
            Files.writeString(record,"corrupt");byte[] before=Files.readAllBytes(record);
            assertThatThrownBy(()->store.loadOrGenerate(at)).isInstanceOf(IOException.class);
            assertThatThrownBy(()->store.save(at,new Chunk())).isInstanceOf(IOException.class);
            assertThat(Files.readAllBytes(record)).isEqualTo(before);
            World foreign=World.from(new WorldSnapshot(new WorldId("ocean"),new WorldRevision(0),
                    Map.of(new ChunkCoordinate(2,2,2),OceanTerrain.chunk(1,at))));
            WorldStore.save(foreign,record);
            assertThatThrownBy(()->store.loadOrGenerate(at)).isInstanceOf(IOException.class).hasMessageContaining("identity");
            Files.write(record,new byte[65537]);
            assertThatThrownBy(()->store.loadOrGenerate(at)).isInstanceOf(IOException.class).hasMessageContaining("Invalid");
        }
    }

    @Test void invalidAddressesNeverCreateChunkRecords() throws Exception {
        try(var store=new OceanChunkStore(tmp.resolve("sea"),1)) {
            assertThatThrownBy(()->store.loadOrGenerate(new ChunkCoordinate(Integer.MAX_VALUE,0,0))).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(()->store.save(new ChunkCoordinate(0,Integer.MIN_VALUE,0),new Chunk())).isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test void revisionRollbackAndConflictingReplacementCannotEraseSavedEdits() throws Exception {
        try(var store=new OceanChunkStore(tmp.resolve("sea"),1)) {
            Chunk original=store.loadOrGenerate(at);
            Chunk edited=original.copy();edited.set(0,0,0,BlockType.GLASS);store.save(at,edited);
            assertThatThrownBy(()->store.save(at,original)).isInstanceOf(IOException.class).hasMessageContaining("revision");
            Chunk conflicting=original.copy();conflicting.set(0,0,0,BlockType.WOOD);
            assertThatThrownBy(()->store.save(at,conflicting)).isInstanceOf(IOException.class).hasMessageContaining("conflicted");
            assertThat(store.loadOrGenerate(at).get(0,0,0)).isEqualTo(BlockType.GLASS);
        }
    }
}
