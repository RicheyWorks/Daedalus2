// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class HullPiecesTest {

    @Test
    void piecesAreTheTwelveFreePentominoes() {
        int total = 0;
        int[] expected = {8, 2, 8, 8, 8, 4, 4, 4, 4, 1, 8, 4};
        for (int p = 0; p < 12; p++) {
            int[][][] os = HullPieces.orientations(p);
            assertThat(os.length).isEqualTo(expected[p]);
            int[][] asGrid = new int[5][];
            for (int i = 0; i < 5; i++) {
                asGrid[i] = new int[] {os[0][i][0], os[0][i][1]};
            }
            assertThat(DeckPatches.isPatch(asGrid)).isTrue();
            total += os.length;
        }
        assertThat(total).isEqualTo(63);
        assertThat(DeckPatches.freeCount(5)).isEqualTo(12);
        assertThat(DeckPatches.fixedCount(5)).isEqualTo(63);
    }

    @Test
    void knownRectangleCounts() {
        assertThat(HullPieces.quest(3, 20, 8)).isTrue();
        int tileable = 0;
        for (int a = 0; a < 12; a++) {
            for (int b = a + 1; b < 12; b++) {
                for (int c = b + 1; c < 12; c++) {
                    int[] set = {a, b, c};
                    long n = HullPieces.count(3, 5, set, 1000);
                    int[][] g = HullPieces.tile(3, 5, set);
                    assertThat(g.length > 0).isEqualTo(n > 0);
                    if (n > 0) {
                        tileable++;
                        int[] seen = new int[12];
                        for (int[] row : g) {
                            for (int v : row) {
                                seen[v]++;
                            }
                        }
                        assertThat(seen[a]).isEqualTo(5);
                        assertThat(seen[b]).isEqualTo(5);
                        assertThat(seen[c]).isEqualTo(5);
                    }
                }
            }
        }
        assertThat(tileable).isPositive();
        assertThat(HullPieces.count(1, 5, new int[] {1}, 10)).isEqualTo(1);
        assertThat(HullPieces.count(1, 5, new int[] {9}, 10)).isZero();
    }

    @Test
    void questAndGuards() {
        assertThat(HullPieces.QUEST_ID).isEqualTo("q_hull_pieces");
        assertThat(HullPieces.quest(3, 20, 9)).isFalse();
        assertThatThrownBy(() -> HullPieces.count(2, 2, new int[] {1}, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}