// SPDX-License-Identifier: MIT

package com.daedalus.world.art;

import org.junit.jupiter.api.Test;

import java.nio.ByteBuffer;
import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Maze art (ADR-035): a seed is a picture. The same seed draws the same maze the same way, byte for byte;
 * the nine generators all appear; the solution runs from corner to corner; the PNG is a real PNG.
 */
class MazeArtTest {

    @Test
    void aSeedIsAPicture() {
        MazeArt a = MazeArt.of(42);
        assertThat(MazeArt.of(42).png()).isEqualTo(a.png());
        assertThat(MazeArt.of(43).png()).isNotEqualTo(a.png());
        assertThat(a.title()).endsWith(" No. 42");
        byte[] png = a.png();
        assertThat(png[1]).isEqualTo((byte) 'P');
        ByteBuffer b = ByteBuffer.wrap(png);
        assertThat(b.getInt(16)).isEqualTo(MazeArt.SIZE);
        assertThat(b.getInt(20)).isEqualTo(MazeArt.SIZE);
    }

    @Test
    void everyGeneratorHangsSomewhereAndEverySolutionCrossesTheMaze() {
        Set<String> generators = new HashSet<>();
        for (long seed = 0; seed < 120; seed++) {
            MazeArt art = MazeArt.of(seed);
            generators.add(art.generator());
            // Corner to corner is at least 2 × 15 − 1 cells.
            assertThat(art.pathLength()).as("seed %d (%s)", seed, art.generator()).isGreaterThanOrEqualTo(29);
        }
        assertThat(generators).hasSize(9);
    }

    @Test
    void thePictureHasAWallAGroundAndARainbowPath() {
        MazeArt art = MazeArt.of(7);
        Set<Integer> colours = new HashSet<>();
        for (int y = 0; y < MazeArt.SIZE; y += 2) {
            for (int x = 0; x < MazeArt.SIZE; x += 2) {
                colours.add(art.rgbAt(x, y));
            }
        }
        assertThat(colours.size()).as("frame line, wall, ground and many path hues").isGreaterThan(20);
        assertThat(Png.encode(1, 1, new int[] {0xff0000})).hasSizeGreaterThan(40);
    }
}
