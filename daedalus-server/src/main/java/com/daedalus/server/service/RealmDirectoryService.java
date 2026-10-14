// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.world.Chunk;
import com.daedalus.world.WorldStyle;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;

/** Discover provider routes without mounting a second copy of a provider's terrain. */
@Service
public class RealmDirectoryService {
    public enum Protocol { WORLD_V1, OCEAN_V1 }
    public record Realm(String id, String title, String realm, String catalog, Protocol protocol, String manifestPath,
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
        HashSet<String> sessions = new HashSet<>();
        for (WorldHub.WorldEntry world : worlds.worlds()) {
            if (!ids.add(world.id())) throw new IllegalStateException("Duplicate realm id");
            String path = "/api/v1/world/" + world.id();
            Binding binding = binding(world);
            if (binding != null && !sessions.add(binding.realm())) throw new IllegalStateException("Duplicate session realm");
            entries.add(new Realm(world.id(), world.title(), binding == null ? null : binding.realm(),
                    binding == null ? null : binding.catalog(), Protocol.WORLD_V1, path,
                    path + "/chunk/blocks?x={x}&y={y}&z={z}", true));
        }
        OceanHostService hostedOcean = ocean.getIfAvailable();
        if (hostedOcean != null) {
            String id = hostedOcean.manifest().realm();
            if (!ids.add(id)) throw new IllegalStateException("Duplicate realm id");
            if (!sessions.add("OCEAN")) throw new IllegalStateException("Duplicate session realm");
            entries.add(new Realm(id, "Ocean", "OCEAN", "ocean", Protocol.OCEAN_V1, "/api/v1/ocean/v1",
                    "/api/v1/ocean/v1/chunk?x={x}&y={y}&z={z}", false));
        }
        return new Directory(1, Chunk.SIZE, "xyz-y-up-metres", entries);
    }

    private record Binding(WorldStyle style, String realm, String catalog) { }

    /** Match shipped session identities, never infer a custom world's identity from style alone. */
    private static Binding binding(WorldHub.WorldEntry world) {
        Binding candidate = switch (world.id()) {
            case "world-zero" -> new Binding(WorldStyle.SKY_ISLANDS, "WORLD-ZERO", "world-zero");
            case "gallery", "gallery-city" -> new Binding(WorldStyle.GALLERY, "GALLERY-CITY", "gallery-city");
            case "parcels" -> new Binding(WorldStyle.PARCELS, "PARCELS", "parcels");
            case "bricks" -> new Binding(WorldStyle.BRICKS, "BRICKS", "bricks");
            case "labyrinth" -> new Binding(WorldStyle.LABYRINTH, "LABYRINTH", "labyrinth");
            default -> null;
        };
        return candidate != null && candidate.style() == world.style() ? candidate : null;
    }
}
