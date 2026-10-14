// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.world.Chunk;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;

/** Discover provider routes without mounting a second copy of a provider's terrain. */
@Service
public class RealmDirectoryService {
    public enum Protocol { WORLD_V1, OCEAN_V1 }
    public record Realm(String id, String title, Protocol protocol, String manifestPath,
                        String chunkPathTemplate, boolean blockEditsSupported) { }
    public record Directory(int schemaVersion, int chunkSize, String coordinates, List<Realm> realms) {
        public Directory { realms = List.copyOf(realms); }
    }
    private final WorldHub worlds;
    private final ObjectProvider<OceanHostService> ocean;

    public RealmDirectoryService(WorldHub worlds, ObjectProvider<OceanHostService> ocean) {
        this.worlds = worlds;
        this.ocean = ocean;
    }

    public Directory directory() {
        List<Realm> entries = new ArrayList<>();
        HashSet<String> ids = new HashSet<>();
        for (WorldHub.WorldEntry world : worlds.worlds()) {
            if (!ids.add(world.id())) throw new IllegalStateException("Duplicate realm id");
            String path = "/api/v1/world/" + world.id();
            entries.add(new Realm(world.id(), world.title(), Protocol.WORLD_V1, path,
                    path + "/chunk/blocks?x={x}&y={y}&z={z}", true));
        }
        OceanHostService hostedOcean = ocean.getIfAvailable();
        if (hostedOcean != null) {
            String id = hostedOcean.manifest().realm();
            if (!ids.add(id)) throw new IllegalStateException("Duplicate realm id");
            entries.add(new Realm(id, "Ocean", Protocol.OCEAN_V1, "/api/v1/ocean/v1",
                    "/api/v1/ocean/v1/chunk?x={x}&y={y}&z={z}", false));
        }
        return new Directory(1, Chunk.SIZE, "xyz-y-up-metres", entries);
    }
}
