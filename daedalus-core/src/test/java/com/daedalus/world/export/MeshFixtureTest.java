// SPDX-License-Identifier: MIT

package com.daedalus.world.export;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandOps;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The parity fixture between the Java mesher and the Unreal plugin's engine-free C++ mesher (ADR-032).
 * The fixture holds a small island plus one of every see-through cube, the palette, and what the Java
 * mesher makes of each chunk; {@code engines/unreal/core-test} feeds the same cubes to
 * {@code DaedalusMeshCore.h} and must get the same faces, positions, normals and colours. If the Java
 * mesher changes, this test fails until the fixture is rewritten with {@code -Ddaedalus.fixtures.write=true}
 * — and then the C++ test says whether Unreal still agrees.
 */
class MeshFixtureTest {

    static final Path FIXTURE = Path.of("..", "engines", "unreal", "core-test", "isle8.mesh.txt");

    static World fixtureWorld() {
        World w = new World(new WorldId("fixture"));
        IslandOps.raise(w, IslandOps.slot(0), IslandGenerator.generate(11, IslandGenerator.MIN_RADIUS));
        // One of every see-through kind, touching each other and the stone, above the island.
        int x = 0;
        for (BlockType t : BlockType.values()) {
            if (t != BlockType.AIR) {
                w.place(new BlockCoordinate(x, 70, -100), t);
                w.place(new BlockCoordinate(x, 71, -100), t.seeThrough() ? BlockType.STONE : BlockType.GLASS);
                x++;
            }
        }
        return w;
    }

    static String render(World w) {
        List<String> out = new ArrayList<>();
        out.add("daedalus-mesh-fixture 1");
        for (BlockType t : BlockType.values()) {
            out.add(String.format(Locale.ROOT, "type %d %s %06x %d %d", t.ordinal(), t.name(),
                    t == BlockType.AIR ? 0 : BlockColors.rgb(t), BlockColors.translucent(t) ? 1 : 0, t.seeThrough() ? 1 : 0));
        }
        List<ChunkCoordinate> keys = new ArrayList<>(w.chunkKeys());
        keys.sort((a, b) -> a.y() != b.y() ? Integer.compare(a.y(), b.y())
                : a.z() != b.z() ? Integer.compare(a.z(), b.z()) : Integer.compare(a.x(), b.x()));
        for (ChunkCoordinate cc : keys) {
            Chunk c = w.chunk(cc);
            if (c != null && !c.isEmpty()) {
                out.add("chunk " + cc.x() + " " + cc.y() + " " + cc.z() + " "
                        + Base64.getEncoder().encodeToString(c.ordinals()));
                // the batch endpoint's run-length form of the same cubes: DaedalusMeshCore.h DecodeRuns must agree
                out.add("runs " + cc.x() + " " + cc.y() + " " + cc.z() + " "
                        + Base64.getEncoder().encodeToString(c.runs()));
            }
        }
        for (WorldMesher.ChunkMesh m : WorldMesher.mesh(w)) {
            out.add("expect " + m.at().x() + " " + m.at().y() + " " + m.at().z() + " "
                    + sums(m.opaque()) + " " + sums(m.translucent()));
        }
        // the greedy mesh (ADR-064): DaedalusMeshCore.h's MeshChunkGreedy must match these too
        for (WorldMesher.ChunkMesh m : WorldMesher.meshGreedy(w)) {
            out.add("greedy " + m.at().x() + " " + m.at().y() + " " + m.at().z() + " "
                    + sums(m.opaque()) + " " + sums(m.translucent()));
        }
        return String.join("\n", out) + "\n";
    }

    /**
     * faces, then the sums a second mesher must match: positions, normals·position, colours ×10⁴ rounded,
     * and the index order (so a mesher that winds faces the other way round is caught).
     */
    static String sums(WorldMesher.Part p) {
        float[] pos = p.positions.toArray();
        float[] nrm = p.normals.toArray();
        float[] col = p.colors.toArray();
        long ps = 0;
        long np = 0;
        long cs = 0;
        for (int i = 0; i < pos.length; i++) {
            ps += (long) pos[i] * (i % 3 + 1);
            np += (long) (nrm[i] * pos[i]);
            cs += Math.round(col[i] * 10_000.0);
        }
        long ix = 0;
        for (int i = 0; i < p.indices.size(); i++) {
            ix += (long) p.indices.get(i) * (i % 6 + 1);
        }
        return p.faceCount() + " " + ps + " " + np + " " + cs + " " + ix;
    }

    @Test
    void theCommittedFixtureIsWhatTheJavaMesherMakesToday() throws Exception {
        String now = render(fixtureWorld());
        if (Boolean.getBoolean("daedalus.fixtures.write")) {
            Files.writeString(FIXTURE, now, StandardCharsets.UTF_8);
        }
        assertThat(Files.exists(FIXTURE)).as(FIXTURE.toAbsolutePath().toString()).isTrue();
        assertThat(Files.readString(FIXTURE, StandardCharsets.UTF_8)).isEqualTo(now);
    }

    /** Every unit face a quad covers, as "x y z nx ny nz" (the face's cell and direction). */
    private static java.util.Set<String> unitFaces(WorldMesher.Part p, boolean greedy) {
        float[] pos = p.positions.toArray();
        float[] nrm = p.normals.toArray();
        java.util.Set<String> out = new java.util.HashSet<>();
        for (int q = 0; q < p.vertexCount() / 4; q++) {
            int[] lo = {Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE};
            int[] hi = {Integer.MIN_VALUE, Integer.MIN_VALUE, Integer.MIN_VALUE};
            for (int c = 0; c < 4; c++) {
                for (int a = 0; a < 3; a++) {
                    int v = (int) pos[(q * 4 + c) * 3 + a];
                    lo[a] = Math.min(lo[a], v);
                    hi[a] = Math.max(hi[a], v);
                }
            }
            int[] n = {(int) nrm[q * 12], (int) nrm[q * 12 + 1], (int) nrm[q * 12 + 2]};
            int d = n[0] != 0 ? 0 : n[1] != 0 ? 1 : 2;
            // the cube behind the face: on a + face the plane is the cube's far side
            int plane = lo[d] - (n[d] > 0 ? 1 : 0);
            int[] from = lo.clone();
            int[] to = hi.clone();
            from[d] = plane;
            to[d] = plane + 1;
            int count = 0;
            for (int x = from[0]; x < to[0]; x++) {
                for (int y = from[1]; y < to[1]; y++) {
                    for (int z = from[2]; z < to[2]; z++) {
                        assertThat(out.add(x + " " + y + " " + z + " " + n[0] + " " + n[1] + " " + n[2]))
                                .as("a face covered twice").isTrue();
                        count++;
                    }
                }
            }
            if (!greedy) {
                assertThat(count).isEqualTo(1);
            }
        }
        return out;
    }

    @Test
    void theGreedyMeshCoversExactlyTheSameFacesWithFarFewerQuads() {
        World w = fixtureWorld();
        java.util.Map<ChunkCoordinate, WorldMesher.ChunkMesh> plain = new java.util.HashMap<>();
        for (WorldMesher.ChunkMesh m : WorldMesher.mesh(w)) {
            plain.put(m.at(), m);
        }
        long before = 0;
        long after = 0;
        for (WorldMesher.ChunkMesh g : WorldMesher.meshGreedy(w)) {
            WorldMesher.ChunkMesh p = plain.get(g.at());
            assertThat(unitFaces(g.opaque(), true)).as("opaque faces of " + g.at()).isEqualTo(unitFaces(p.opaque(), false));
            assertThat(unitFaces(g.translucent(), true)).as("translucent faces of " + g.at())
                    .isEqualTo(unitFaces(p.translucent(), false));
            before += p.opaque().faceCount() + p.translucent().faceCount();
            after += g.opaque().faceCount() + g.translucent().faceCount();
        }
        assertThat(WorldMesher.meshGreedy(w)).hasSameSizeAs(plain.values());
        assertThat(after * 2).as("%d quads vs %d faces", after, before).isLessThan(before);
    }
}
