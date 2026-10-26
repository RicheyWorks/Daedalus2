// SPDX-License-Identifier: MIT

package com.daedalus.world.export;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.gate.GateOps;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandOps;
import org.junit.jupiter.api.Test;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The engine-independent export (ADR-032): the mesher draws exactly the faces the realm draws, splits
 * see-through cubes into their own part, keeps colours inside glTF's 0..1, and the GLB is a well-formed,
 * byte-for-byte repeatable glTF 2.0 binary with one node per non-empty chunk.
 */
class WorldMesherTest {

    private static World world() {
        return new World(new WorldId("export-test"));
    }

    private static int faces(List<WorldMesher.ChunkMesh> chunks) {
        return chunks.stream().mapToInt(c -> c.opaque().faceCount() + c.translucent().faceCount()).sum();
    }

    @Test
    void aLoneCubeIsSixFacesOfOneMetre() {
        World w = world();
        w.place(new BlockCoordinate(3, 4, 5), BlockType.STONE);
        List<WorldMesher.ChunkMesh> chunks = WorldMesher.mesh(w);
        assertThat(chunks).hasSize(1);
        WorldMesher.Part p = chunks.get(0).opaque();
        assertThat(p.faceCount()).isEqualTo(6);
        assertThat(p.vertexCount()).isEqualTo(24);
        assertThat(chunks.get(0).translucent().isEmpty()).isTrue();
        assertThat(p.min).containsExactly(3f, 4f, 5f);
        assertThat(p.max).containsExactly(4f, 5f, 6f);
    }

    @Test
    void touchingFacesAreCulledButGlassStillShowsWhatIsBehindIt() {
        World w = world();
        w.place(new BlockCoordinate(0, 0, 0), BlockType.STONE);
        w.place(new BlockCoordinate(1, 0, 0), BlockType.STONE);
        assertThat(faces(WorldMesher.mesh(w))).isEqualTo(10);

        w.place(new BlockCoordinate(1, 0, 0), BlockType.GLASS);
        List<WorldMesher.ChunkMesh> m = WorldMesher.mesh(w);
        // Stone keeps its face toward the glass; the glass hides its face against the stone.
        assertThat(m.get(0).opaque().faceCount()).isEqualTo(6);
        assertThat(m.get(0).translucent().faceCount()).isEqualTo(5);

        // Two panes of the same glass merge into one sheet, as in the realm.
        w.place(new BlockCoordinate(2, 0, 0), BlockType.GLASS);
        assertThat(WorldMesher.mesh(w).get(0).translucent().faceCount()).isEqualTo(5 + 5 - 1 - 0);
    }

    @Test
    void aCubeOnAChunkEdgeSeesItsNeighbourInTheNextChunk() {
        World w = world();
        w.place(new BlockCoordinate(15, 0, 0), BlockType.DIRT);
        w.place(new BlockCoordinate(16, 0, 0), BlockType.DIRT);
        List<WorldMesher.ChunkMesh> m = WorldMesher.mesh(w);
        assertThat(m).hasSize(2);
        assertThat(faces(m)).isEqualTo(10);
    }

    @Test
    void anIslandAndAGateMeshWithColoursInRangeAndUnitNormals() {
        World w = world();
        IslandOps.raise(w, IslandOps.slot(0), IslandGenerator.generate(11));
        GateOps.build(w, 0);
        List<WorldMesher.ChunkMesh> m = WorldMesher.mesh(w);
        assertThat(m).hasSize(w.chunkKeys().size());
        assertThat(m.stream().anyMatch(c -> !c.translucent().isEmpty())).as("rainbow and doorway blend").isTrue();
        for (WorldMesher.ChunkMesh c : m) {
            for (WorldMesher.Part p : List.of(c.opaque(), c.translucent())) {
                float[] col = p.colors.toArray();
                for (float v : col) {
                    assertThat(v).isBetween(0f, 1f);
                }
                float[] n = p.normals.toArray();
                for (int i = 0; i < n.length; i += 3) {
                    assertThat(Math.abs(n[i]) + Math.abs(n[i + 1]) + Math.abs(n[i + 2])).isEqualTo(1f);
                }
                assertThat(p.indices.size() % 6).isZero();
            }
        }
        assertThat(faces(m)).isEqualTo(faces(WorldMesher.mesh(World.from(w.snapshot()))));
    }

    @Test
    void theGlbIsWellFormedAndRepeatable() throws Exception {
        World w = world();
        IslandOps.raise(w, IslandOps.slot(0), IslandGenerator.generate(11));
        List<WorldMesher.ChunkMesh> m = WorldMesher.mesh(w);
        byte[] a = Glb.write(m, "test");
        byte[] b = Glb.write(WorldMesher.mesh(World.from(w.snapshot())), "test");
        assertThat(sha(a)).isEqualTo(sha(b));

        ByteBuffer bb = ByteBuffer.wrap(a).order(ByteOrder.LITTLE_ENDIAN);
        assertThat(bb.getInt(0)).isEqualTo(0x46546C67);           // "glTF"
        assertThat(bb.getInt(4)).isEqualTo(2);
        assertThat(bb.getInt(8)).isEqualTo(a.length);
        int jsonLen = bb.getInt(12);
        assertThat(bb.getInt(16)).isEqualTo(0x4E4F534A);          // "JSON"
        assertThat(jsonLen % 4).isZero();
        int binLen = bb.getInt(20 + jsonLen);
        assertThat(bb.getInt(24 + jsonLen)).isEqualTo(0x004E4942); // "BIN\0"
        assertThat(28 + jsonLen + binLen).isEqualTo(a.length);

        String json = new String(a, 20, jsonLen, StandardCharsets.UTF_8).trim();
        assertThat(json).contains("\"version\":\"2.0\"", "daedalus_opaque", "daedalus_translucent", "\"COLOR_0\"");
        assertThat(count(json, "\"name\":\"chunk_")).isEqualTo(2 * m.size()); // a mesh and a node each
        Matcher bl = Pattern.compile("\"buffers\":\\[\\{\"byteLength\":(\\d+)}]").matcher(json);
        assertThat(bl.find()).isTrue();
        assertThat(Integer.parseInt(bl.group(1))).isLessThanOrEqualTo(binLen).isGreaterThan(binLen - 4);
    }

    @Test
    void anEmptyWorldIsAnEmptyButValidScene() {
        byte[] glb = Glb.write(WorldMesher.mesh(world()), "empty");
        ByteBuffer bb = ByteBuffer.wrap(glb).order(ByteOrder.LITTLE_ENDIAN);
        assertThat(bb.getInt(0)).isEqualTo(0x46546C67);
        assertThat(bb.getInt(8)).isEqualTo(glb.length);
    }

    @Test
    void theSharedPaletteKeepsSeeThroughAndTranslucentInStep() {
        for (BlockType t : BlockType.values()) {
            if (BlockColors.translucent(t)) {
                assertThat(t.seeThrough()).as(t.name()).isTrue();
            }
            if (t != BlockType.AIR) {
                assertThat(BlockColors.rgb(t)).as(t.name()).isBetween(0, 0xFFFFFF);
            }
        }
        for (int i = 0; i < 1000; i++) {
            assertThat(BlockColors.jitter(i, i * 7, -i)).isBetween(0.94, 1.06);
        }
    }

    private static int count(String s, String needle) {
        int n = 0;
        for (int i = s.indexOf(needle); i >= 0; i = s.indexOf(needle, i + 1)) {
            n++;
        }
        return n;
    }

    private static String sha(byte[] b) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b));
    }
}
