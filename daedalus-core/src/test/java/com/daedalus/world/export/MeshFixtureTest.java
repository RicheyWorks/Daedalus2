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
            }
        }
        for (WorldMesher.ChunkMesh m : WorldMesher.mesh(w)) {
            out.add("expect " + m.at().x() + " " + m.at().y() + " " + m.at().z() + " "
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
}
