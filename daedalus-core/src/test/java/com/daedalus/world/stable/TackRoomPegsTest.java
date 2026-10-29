// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.TackRoomPegs.Room;

import org.junit.jupiter.api.Test;

class TackRoomPegsTest {

    @Test
    void bestMatchesBruteForceAndHangingIsLegal() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 8);
            int[] w = TackRoomPegs.weights(seed, n, 10);
            int[] f = TackRoomPegs.feuds(seed, n, 30);
            Room r = TackRoomPegs.best(w, f, 10);
            assertThat(r.pegs()).as("seed %d", seed).isEqualTo(brute(w, f, 10));
            assertThat(TackRoomPegs.hang(w, f, 10, r.pegOf())).isEqualTo(r.pegs());
            assertThat(TackRoomPegs.quest(w, f, 10, r.pegOf())).isTrue();
        }
    }

    @Test
    void firstFitIsLegalNeverBetterAndSometimesWorse() {
        boolean lost = false;
        for (long seed = 1; seed <= 300; seed++) {
            int[] w = TackRoomPegs.weights(seed, 11, 10);
            int[] f = TackRoomPegs.feuds(seed, 11, 25);
            Room ff = TackRoomPegs.firstFit(w, f, 10);
            Room b = TackRoomPegs.best(w, f, 10);
            assertThat(TackRoomPegs.hang(w, f, 10, ff.pegOf())).isEqualTo(ff.pegs());
            assertThat(ff.pegs()).isGreaterThanOrEqualTo(b.pegs());
            lost |= ff.pegs() > b.pegs();
        }
        assertThat(lost).isTrue();
    }

    @Test
    void feudSendsFirstFitToAnExtraPeg() {
        // Limit 4. The two light bridles (1, 2) hang together first; then the 2-weight bridle
        // feuds with bridle 2 and the 3-weight saddle feuds with the 4-weight one, so first fit
        // needs 5 pegs where {4} {1,2} {1,3} {4} takes 4.
        int[] w = {4, 1, 1, 3, 4, 2};
        int[] f = new int[6];
        feud(f, 2, 5);
        feud(f, 3, 4);
        assertThat(TackRoomPegs.firstFit(w, f, 4).pegs()).isEqualTo(5);
        assertThat(TackRoomPegs.best(w, f, 4).pegs()).isEqualTo(4);
        assertThat(TackRoomPegs.quest(w, f, 4, TackRoomPegs.firstFit(w, f, 4).pegOf())).isFalse();
        assertThat(TackRoomPegs.quest(w, f, 4, new int[] {0, 1, 2, 2, 3, 1})).isTrue();
    }

    @Test
    void illegalHangingsScoreMinusOne() {
        int[] w = {3, 3, 2};
        int[] f = new int[3];
        feud(f, 0, 2);
        assertThat(TackRoomPegs.hang(w, f, 5, new int[] {0, 0, 1})).isEqualTo(-1);
        assertThat(TackRoomPegs.hang(w, f, 5, new int[] {0, 1, 0})).isEqualTo(-1);
        assertThat(TackRoomPegs.hang(w, f, 5, new int[] {0, 1})).isEqualTo(-1);
        assertThat(TackRoomPegs.hang(w, f, 5, new int[] {0, 1, 1})).isEqualTo(2);
        assertThat(TackRoomPegs.best(new int[0], new int[0], 5).pegs()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(TackRoomPegs.weights(4, 9, 7)).containsExactly(TackRoomPegs.weights(4, 9, 7));
        assertThat(TackRoomPegs.feuds(4, 9, 40)).containsExactly(TackRoomPegs.feuds(4, 9, 40));
        assertThat(TackRoomPegs.QUEST_ID).isEqualTo("q_tidy_tack_room");
        assertThatThrownBy(() -> TackRoomPegs.weights(1, 15, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TackRoomPegs.best(new int[] {6}, new int[] {0}, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TackRoomPegs.best(new int[] {1, 1}, new int[] {2, 0}, 5)).isInstanceOf(IllegalArgumentException.class);
    }

    private static void feud(int[] f, int a, int b) {
        f[a] |= 1 << b;
        f[b] |= 1 << a;
    }

    private static int brute(int[] w, int[] f, int limit) {
        int n = w.length;
        if (n == 0) {
            return 0;
        }
        for (int k = 1; k <= n; k++) {
            if (fits(w, f, limit, new int[n], 0, k)) {
                return k;
            }
        }
        throw new IllegalStateException("unreachable");
    }

    private static boolean fits(int[] w, int[] f, int limit, int[] peg, int i, int k) {
        if (i == w.length) {
            return TackRoomPegs.hang(w, f, limit, peg) >= 0;
        }
        for (int p = 0; p < k; p++) {
            peg[i] = p;
            if (fits(w, f, limit, peg, i + 1, k)) {
                return true;
            }
        }
        return false;
    }
}
