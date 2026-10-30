// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class MossDeckTest {

    @Test
    void blockStaysAndBlinkerFlips() {
        boolean[][] block = MossDeck.parse("....", ".##.", ".##.", "....");
        assertThat(MossDeck.step(block)).isDeepEqualTo(block);
        assertThat(MossDeck.cycle(block, 10)).isEqualTo(new MossDeck.Cycle(0, 1));
        boolean[][] h = MossDeck.parse(".....", ".....", ".###.", ".....", ".....");
        boolean[][] v = MossDeck.parse(".....", "..#..", "..#..", "..#..", ".....");
        assertThat(MossDeck.step(h)).isDeepEqualTo(v);
        assertThat(MossDeck.cycle(h, 10)).isEqualTo(new MossDeck.Cycle(0, 2));
        assertThat(MossDeck.after(h, 1_000_000_001L)).isDeepEqualTo(v);
    }

    @Test
    void gliderWrapsHomeOnTheDeck() {
        boolean[][] g = MossDeck.parse(".#....", "..#...", "###...", "......", "......", "......");
        // a glider moves one cell diagonally every 4 nights, so 6x6 wraps after 24
        assertThat(MossDeck.cycle(g, 100)).isEqualTo(new MossDeck.Cycle(0, 24));
        assertThat(MossDeck.moss(MossDeck.after(g, 7))).isEqualTo(5);
    }

    @Test
    void forecastMatchesNightByNight() {
        SplittableRandom rnd = new SplittableRandom(243);
        for (int t = 0; t < 30; t++) {
            int rows = 3 + rnd.nextInt(6);
            int cols = 3 + rnd.nextInt(6);
            boolean[][] d = new boolean[rows][cols];
            for (boolean[] row : d) {
                for (int c = 0; c < cols; c++) {
                    row[c] = rnd.nextInt(3) == 0;
                }
            }
            boolean[][] cur = d;
            for (int k = 0; k <= 300; k++) {
                if (k % 37 == 0) {
                    assertThat(MossDeck.after(d, k)).isDeepEqualTo(cur);
                }
                cur = MossDeck.step(cur);
            }
        }
    }

    @Test
    void questInputsAndEmptyDeck() {
        boolean[][] h = MossDeck.parse("...", "###", "...");
        boolean[][] copy = MossDeck.parse("...", "###", "...");
        assertThat(MossDeck.quest(h, 0, copy)).isTrue();
        assertThat(MossDeck.quest(h, 4, MossDeck.after(h, 4))).isTrue();
        assertThat(MossDeck.quest(h, 3, MossDeck.parse("#..", "...", "..."))).isFalse();
        MossDeck.after(h, 5);
        assertThat(h).isDeepEqualTo(copy);
        assertThat(MossDeck.QUEST_ID).isEqualTo("q_moss_deck");
        assertThat(MossDeck.cycle(new boolean[4][4], 3)).isEqualTo(new MossDeck.Cycle(0, 1));
        assertThatThrownBy(() -> MossDeck.after(h, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> MossDeck.step(new boolean[][] {{true}, {true, false}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
