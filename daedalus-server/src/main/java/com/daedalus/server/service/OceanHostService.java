// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.api.dto.ChunkBlocksResponse;
import com.daedalus.world.*;
import com.daedalus.world.ocean.*;
import java.io.IOException;
import java.nio.file.Path;
import java.util.*;

/** One configured Ocean sector. Trusted Java callers enforce edit ownership; HTTP exposes reads only. */
public final class OceanHostService implements AutoCloseable {
    public record Bounds(int minX,int maxX,int minY,int maxY,int minZ,int maxZ) {
        public Bounds {
            long volume=1;
            for(int[] axis:new int[][]{{minX,maxX},{minY,maxY},{minZ,maxZ}}) {
                long length=(long)axis[1]-axis[0]+1;
                if(length<1||length>4096||axis[0]<Integer.MIN_VALUE/16||axis[1]>Integer.MAX_VALUE/16) {
                    throw new IllegalArgumentException("Invalid Ocean sector bounds");
                }
                volume*=length;
            }
            if(volume>4096)throw new IllegalArgumentException("Ocean sector exceeds 4096 chunks");
        }
        public boolean contains(ChunkCoordinate at) {
            return at.x()>=minX&&at.x()<=maxX&&at.y()>=minY&&at.y()<=maxY&&at.z()>=minZ&&at.z()<=maxZ;
        }
    }
    public record Manifest(String realm,String seed,int generatorVersion,int chunkSize,Bounds bounds,
                           int residentCapacity,BlockCoordinate spawn,BlockCoordinate boatBerth,BlockCoordinate submarineBerth) { }
    private final OceanChunkWindow window;
    private final Manifest manifest;
    private static final List<String> PALETTE=Arrays.stream(BlockType.values()).map(Enum::name).toList();

    public OceanHostService(Path directory,long seed,int capacity,Bounds bounds) throws IOException {
        Objects.requireNonNull(bounds,"bounds");
        window=new OceanChunkWindow(directory,seed,capacity);
        manifest=new Manifest("ocean",Long.toString(seed),OceanTerrain.VERSION,Chunk.SIZE,bounds,capacity,
                OceanTerrain.spawn(),OceanTerrain.boatBerth(),OceanTerrain.submarineBerth());
    }
    public Manifest manifest() { return manifest; }
    public ChunkBlocksResponse chunk(int x,int y,int z) throws IOException {
        var at=new ChunkCoordinate(x,y,z);requireSector(at);
        Chunk chunk=window.snapshot(at);
        return new ChunkBlocksResponse(x,y,z,!chunk.isEmpty(),chunk.revision(),PALETTE,
                chunk.isEmpty()?"":Base64.getEncoder().encodeToString(chunk.ordinals()));
    }
    /** Trusted host path only; not an HTTP mutation endpoint. */
    public void set(BlockCoordinate at,BlockType type) throws IOException {
        requireSector(at.chunk());window.set(at,type);
    }
    private void requireSector(ChunkCoordinate at) {
        if(!manifest.bounds().contains(at))throw new NoSuchElementException("Chunk is outside hosted Ocean sector");
    }
    @Override public void close() throws IOException { window.close(); }
}
