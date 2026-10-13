// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

/** The voxel isle (ADR-058): the same cubes as the Unreal plugin's C++ core, cube for cube. */
class VoxelIsleTest {

    /** Written by engines/unreal/core-test/voxel_isle_core_test.cpp --write. */
    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "voxel_isle_parity.txt");

    private static final class Summary {
        int columns;
        long cubes;
        final long[] layers = new long[VoxelIsle.Layer.values().length];
        long hash = 0xcbf29ce484222325L;
    }

    private static Summary run(VoxelIsle.Params p) {
        Summary s = new Summary();
        s.columns = VoxelIsle.build(p, (x, y, z, l) -> {
            s.cubes++;
            s.layers[l.ordinal()]++;
            for (int v : new int[] {x, y, z, l.ordinal()}) {
                s.hash ^= Integer.toUnsignedLong(v);
                s.hash *= 1099511628211L;
            }
        });
        return s;
    }

    @Test
    void matchesTheCppCoreCubeForCube() throws IOException {
        List<String> lines = new ArrayList<>();
        for (String line : Files.readAllLines(PARITY)) {
            if (!line.startsWith("#") && !line.isBlank()) {
                lines.add(line);
            }
        }
        assertThat(lines).hasSize(7);
        for (String line : lines) {
            String[] part = line.split("\\|");
            String[] a = part[0].trim().split(" ");
            VoxelIsle.Params p = new VoxelIsle.Params(Integer.parseInt(a[0]), Integer.parseInt(a[1]),
                    Integer.parseInt(a[2]), Integer.parseInt(a[3]), Integer.parseInt(a[4]), Integer.parseInt(a[5]),
                    Integer.parseInt(a[6]));
            String[] want = part[1].trim().split(" ");
            for (String col : part[2].trim().split(" ")) {
                String[] c = col.split(",");
                int x = Integer.parseInt(c[0]);
                int y = Integer.parseInt(c[1]);
                int top = VoxelIsle.columnTop(p, x, y);
                assertThat(top).as("top of %d,%d on seed %d", x, y, p.seed()).isEqualTo(Integer.parseInt(c[2]));
                if (top != VoxelIsle.OFF) {
                    assertThat(VoxelIsle.columnBottom(p, x, y)).as("bottom of %d,%d", x, y)
                            .isEqualTo(Integer.parseInt(c[3]));
                }
            }
            Summary s = run(p);
            String got = s.columns + " " + s.cubes + " " + s.layers[0] + " " + s.layers[1] + " " + s.layers[2] + " "
                    + s.layers[3] + " " + s.layers[4] + " " + s.layers[5] + " " + Long.toUnsignedString(s.hash);
            assertThat(got).as("seed %d radius %d", p.seed(), p.radius()).isEqualTo(String.join(" ", want));
        }
    }

    @Test
    void theOrreryReachHasFiveIslesAndClaudeIslandAtTheCentre() {
        List<VoxelIsle.Placed> reach = VoxelIsle.orreryReach();
        assertThat(reach).extracting(VoxelIsle.Placed::name)
                .containsExactly("Claude Island", "Bloomfields", "Tidewells", "Lens Forge", "Vault");
        assertThat(reach.get(0).dx()).isZero();
        // inside the unreal-team cell (+/-8 km around Claude Island's origin in Unreal units)
        assertThat(reach).allMatch(i -> Math.abs(i.dx()) < 800_000 && Math.abs(i.dy()) < 800_000);
    }

    @Test
    void columnsGridMatchesColumnTop() {
        VoxelIsle.Params p = new VoxelIsle.Params(53, 38, 14, 45, 0, 0, 0);
        int[][] g = VoxelIsle.columns(p);
        int n = p.radius() + 2;
        int w = 2 * n + 1;
        assertThat(g[0]).hasSize(w * w);
        assertThat(g[0][(0 + n) * w + (5 + n)]).isEqualTo(VoxelIsle.columnTop(p, 5, 0));
        assertThat(g[0][0]).isEqualTo(VoxelIsle.OFF);
    }

    @Test
    void refusesSillySettings() {
        assertThatThrownBy(() -> new VoxelIsle.Params(1, 2, 3, 4, 0, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new VoxelIsle.Params(1, 40, 3, 4, 0, 0, -1))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
