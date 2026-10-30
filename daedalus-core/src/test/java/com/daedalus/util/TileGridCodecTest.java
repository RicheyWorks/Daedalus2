// SPDX-License-Identifier: MIT

package com.daedalus.util;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.TileType;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link TileGridCodec}. Round-tripping is the contract; the compression saving is real but
 * moderate, because a rendered maze alternates cell/wall at almost every column — the case
 * run-length coding handles worst.
 */
class TileGridCodecTest {

    private static char[][] glyphsOf(MazeGrid grid) {
        TileType[][] tiles = grid.toTileGrid();
        char[][] out = new char[tiles.length][tiles[0].length];
        for (int r = 0; r < tiles.length; r++) {
            for (int c = 0; c < tiles[r].length; c++) {
                out[r][c] = tiles[r][c].glyph();
            }
        }
        return out;
    }

    @Test
    void roundTripsRealMazes() {
        for (int size : new int[] {4, 16, 33}) {
            for (long seed = 1; seed <= 3; seed++) {
                char[][] original = glyphsOf(new RecursiveBacktrackerGenerator().generate(size, size, seed));

                char[][] restored = TileGridCodec.decode(TileGridCodec.encode(original));

                assertThat(restored).as("size %d seed %d", size, seed).isDeepEqualTo(original);
            }
        }
    }

    @Test
    void roundTripsEveryGlyph() {
        char[][] original = new char[2][TileType.values().length];
        for (int i = 0; i < TileType.values().length; i++) {
            original[0][i] = TileType.values()[i].glyph();
            original[1][i] = TileType.values()[TileType.values().length - 1 - i].glyph();
        }

        assertThat(TileGridCodec.decode(TileGridCodec.encode(original))).isDeepEqualTo(original);
    }

    @Test
    void collapsesLongRuns() {
        char[][] allWall = new char[3][10];
        for (char[] row : allWall) {
            java.util.Arrays.fill(row, '#');
        }

        // 30 identical cells become a single run.
        assertThat(TileGridCodec.encode(allWall)).isEqualTo("3x10:30#");
    }

    @Test
    void singleCellRoundTrips() {
        char[][] one = {{'S'}};

        assertThat(TileGridCodec.encode(one)).isEqualTo("1x1:S");
        assertThat(TileGridCodec.decode("1x1:S")).isDeepEqualTo(one);
    }

    @Test
    void savesSpaceOnRealMazes_withoutEverExpanding() {
        char[][] original = glyphsOf(new RecursiveBacktrackerGenerator().generate(64, 64, 42L));
        int raw = original.length * original[0].length;

        int encoded = TileGridCodec.encode(original).length();

        // Measured ~62-64% of raw across sizes 16-128; assert a conservative bound.
        assertThat(encoded).isLessThan((int) (raw * 0.80));
        // A run of one costs one character, so encoding can never blow the payload up.
        assertThat(encoded).isLessThan(raw + 32);
    }

    @Test
    void rejectsMalformedInput() {
        assertThatThrownBy(() -> TileGridCodec.decode("nonsense"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TileGridCodec.decode("2x2:#")) // too few cells
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TileGridCodec.decode("1x1:99#")) // overflows the grid
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TileGridCodec.decode("2x2:4")) // count with no glyph
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsRaggedGrids() {
        char[][] ragged = {{'#', '#'}, {'#'}};

        assertThatThrownBy(() -> TileGridCodec.encode(ragged))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("rectangular");
    }
}
