// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.WorldManifest;
import com.daedalus.server.config.WalletProperties;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import com.daedalus.world.WorldStyle;
import com.daedalus.world.district.DistrictOps;
import com.daedalus.world.export.BlockColors;
import com.daedalus.world.export.Glb;
import com.daedalus.world.export.WorldMesher;
import com.daedalus.world.gate.GateOps;
import com.daedalus.world.gate.Mount;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Builds Daedalus World Packages (ADR-032): generate a world once, deploy it into any engine. A package
 * is a zip of {@code manifest.json}, {@code world.glb} (glTF 2.0) and {@code assets/} (models made in
 * Blender, such as the ark). Meshing reads a private copy of the world, so building never holds the world
 * lock for long. The mesh is kept until a cube changes; the manifest is written fresh every time.
 */
@Service
public class WorldPackageService {

    public static final String FORMAT = "daedalus-world-package";
    public static final int VERSION = 1;

    /** 1980-01-01T00:00Z, the first moment a zip's DOS clock can say: a fixed time keeps packages repeatable. */
    private static final long ZIP_TIME = 315_532_800_000L;

    /** One world's built package. The bytes are copied in and out: nobody can change a cached mesh. */
    public record Built(long revision, WorldManifest manifest, byte[] glb, byte[] zip) {

        public Built {
            glb = glb.clone();
            zip = zip.clone();
        }

        @Override
        public byte[] glb() {
            return glb.clone();
        }

        @Override
        public byte[] zip() {
            return zip.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Built b && b.revision == revision && b.manifest.equals(manifest)
                    && java.util.Arrays.equals(b.glb, glb) && java.util.Arrays.equals(b.zip, zip);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(revision, manifest, java.util.Arrays.hashCode(glb), java.util.Arrays.hashCode(zip));
        }

        @Override
        public String toString() {
            return "Built[revision=" + revision + ", glb=" + glb.length + " bytes, zip=" + zip.length + " bytes]";
        }
    }

    private final WorldHub hub;
    private final ObjectProvider<WalletProperties> wallet;
    private final ObjectMapper json = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
    private final Map<String, Geometry> geometry = new ConcurrentHashMap<>();
    private final AtomicLong meshes = new AtomicLong();

    public WorldPackageService(WorldHub hub, ObjectProvider<WalletProperties> wallet) {
        this.hub = hub;
        this.wallet = wallet;
    }

    /** How many times a world has been meshed since start: a package request for an unchanged world adds none. */
    public long meshes() {
        return meshes.get();
    }

    /** The package of world {@code id}, built or reused; null when no such world is mounted. */
    public Built build(String id, String baseUrl) {
        WorldService w = hub.get(id);
        if (w == null) {
            return null;
        }
        long revision = w.revision(id);
        Geometry geo = geometry.get(id);
        if (geo == null || geo.revision != revision) {
            World copy = w.copy(id);
            revision = copy.revision().value();
            List<WorldMesher.ChunkMesh> chunks = WorldMesher.mesh(copy);
            long tris = 0;
            for (WorldMesher.ChunkMesh c : chunks) {
                tris += 2L * (c.opaque().faceCount() + c.translucent().faceCount());
            }
            geo = new Geometry(revision, Glb.write(chunks, "Daedalus World Package v" + VERSION), chunks.size(), tris);
            geometry.put(id, geo);
            meshes.incrementAndGet();
        }
        // Arks sail and gates open without touching a cube, so the manifest is always written fresh.
        WorldManifest manifest = manifest(id, w, geo.revision, geo.chunks, geo.triangles, baseUrl);
        return new Built(geo.revision, manifest, geo.glb, zip(manifest, geo.glb));
    }

    /** The meshed world at one revision: the expensive part, kept until a cube changes. Never leaves here. */
    private static final class Geometry {
        private final long revision;
        private final byte[] glb;
        private final int chunks;
        private final long triangles;

        Geometry(long revision, byte[] glb, int chunks, long triangles) {
            this.revision = revision;
            this.glb = glb;
            this.chunks = chunks;
            this.triangles = triangles;
        }
    }

    private WorldManifest manifest(String id, WorldService w, long revision, int chunks, long tris, String base) {
        WorldStyle style = hub.style(id);
        List<WorldManifest.Swatch> palette = new ArrayList<>();
        for (BlockType t : BlockType.values()) {
            if (t != BlockType.AIR) {
                palette.add(new WorldManifest.Swatch(t.ordinal(), t.name(),
                        String.format(Locale.ROOT, "#%06x", BlockColors.rgb(t)), BlockColors.translucent(t), t.seeThrough()));
            }
        }
        Map<Integer, WorldService.IslandClaim> claims = w.claims(id);
        List<WorldManifest.Island> islands = new ArrayList<>();
        for (WorldService.IslandEntry e : w.islands(id)) {
            BlockCoordinate o = e.origin();
            var t = e.traits();
            WorldService.IslandClaim c = claims.get(e.slot());
            islands.add(new WorldManifest.Island(e.slot(), e.seed(), e.radius(), xyz(o),
                    List.of(o.x() + t.dockX(), o.y() + t.dockY(), o.z() + t.dockZ()), c == null ? "" : c.owner()));
        }
        List<WorldManifest.Plot> plots = new ArrayList<>();
        if (w.isDistrict()) {
            for (DistrictOps.Plot p : DistrictOps.plan(seedOf(id)).plots()) {
                ParcelBounds b = p.bounds();
                WorldService.IslandClaim c = claims.get(p.n());
                plots.add(new WorldManifest.Plot(p.n(), List.of(b.minX(), b.minY(), b.minZ()),
                        List.of(b.maxX(), b.maxY(), b.maxZ()), p.show().name(), c == null ? "" : c.owner()));
            }
        }
        List<WorldManifest.Gate> gates = new ArrayList<>();
        for (WorldService.GateLink g : w.gates(id)) {
            gates.add(new WorldManifest.Gate(g.gate(), GateOps.slotOfGate(g.gate()), xyz(g.center()), xyz(g.berth()),
                    g.toWorld(), hub.title(g.toWorld()), g.toGate()));
        }
        List<WorldManifest.Ark> arks = new ArrayList<>();
        for (WorldService.ArkView v : w.arks(id)) {
            arks.add(new WorldManifest.Ark(v.ark().id(), v.ark().name(), v.ark().homeSlot(), v.ark().slot(),
                    xyz(v.ark().berth()), v.voyage() == null ? "MOORED" : "SAILING"));
        }
        Mount mount = Mount.of(style);
        WalletProperties wp = wallet.getIfAvailable();
        WorldManifest.Chain chain = wp != null && wp.enabled() && !wp.deedContract().isEmpty()
                ? new WorldManifest.Chain(wp.chainId(), wp.deedContract(), base + "/api/v1/world/" + id + "/tokens/")
                : null;
        return new WorldManifest(FORMAT, VERSION, "Daedalus " + engineVersion(),
                new WorldManifest.World(id, style.name(), hub.title(id), seedOf(id), revision),
                "1 cube = 1 metre", "glTF: +Y up, right-handed; these are the live API's coordinates",
                new WorldManifest.Geometry("world.glb", 16, chunks, tris, List.of("daedalus_opaque", "daedalus_translucent")),
                palette, islands, plots, gates, arks, new WorldManifest.Mount(mount.name(), mount.ready()),
                List.of(new WorldManifest.Asset("ark", "assets/ark.glb",
                        "one per ark at its berth: deck origin, bow +X, scale 0.6, side-on 9 m off the berth on +Z")),
                new WorldManifest.Live(base + "/api/v1/world/" + id, "/topic/world/" + id + "/{events,arks,ecology}"),
                chain);
    }

    private String engineVersion() {
        String v = getClass().getPackage().getImplementationVersion();
        return v == null ? "dev" : v;
    }

    private long seedOf(String id) {
        return hub.worlds().stream().filter(e -> e.id().equals(id)).findFirst().map(WorldHub.WorldEntry::seed).orElse(0L);
    }

    private byte[] zip(WorldManifest manifest, byte[] glb) {
        try (ByteArrayOutputStream out = new ByteArrayOutputStream(); ZipOutputStream z = new ZipOutputStream(out)) {
            put(z, "manifest.json", json.writeValueAsBytes(manifest));
            put(z, "world.glb", glb);
            try (InputStream ark = getClass().getResourceAsStream("/static/models/ark.glb")) {
                if (ark != null) {
                    put(z, "assets/ark.glb", ark.readAllBytes());
                }
            }
            put(z, "README.txt", ("Daedalus World Package v" + VERSION + " — " + manifest.world().title() + " ("
                    + manifest.world().id() + ") at revision " + manifest.world().revision() + ".\n"
                    + "world.glb: glTF 2.0, one node per 16-cube chunk, metres, +Y up. Import it into Blender, Unreal "
                    + "(Interchange), Godot or three.js as is.\nmanifest.json: islands, sky gates, arks, palette and "
                    + "where the live world is.\nMIT licensed, like Daedalus.\n").getBytes(StandardCharsets.UTF_8));
            z.finish();
            return out.toByteArray();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static void put(ZipOutputStream z, String name, byte[] bytes) throws IOException {
        ZipEntry e = new ZipEntry(name);
        e.setTime(ZIP_TIME);                         // the same world gives the same zip, byte for byte
        z.putNextEntry(e);
        z.write(bytes);
        z.closeEntry();
    }

    private static List<Integer> xyz(BlockCoordinate c) {
        return List.of(c.x(), c.y(), c.z());
    }
}
