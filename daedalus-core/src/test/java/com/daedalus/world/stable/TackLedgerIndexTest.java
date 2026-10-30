// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.TackLedgerIndex.Filing;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class TackLedgerIndexTest {

    @Test
    void bestMatchesBruteForceOverEveryTree() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 9);
            int[] f = TackLedgerIndex.frequencies(seed, n, 20);
            Filing b = TackLedgerIndex.best(f);
            long brute = Long.MAX_VALUE;
            for (int[] order : trees(0, n)) {
                brute = Math.min(brute, TackLedgerIndex.flips(f, order));
            }
            assertThat(b.flips()).as("seed %d", seed).isEqualTo(n == 0 ? 0 : brute);
            assertThat(TackLedgerIndex.flips(f, b.order())).isEqualTo(b.flips());
            assertThat(TackLedgerIndex.quest(f, b.order())).isTrue();
        }
    }

    @Test
    void mostAskedRootIsNeverBetterAndUsuallyWorse() {
        // Ten cards, frequencies 1-20: the habit flipped more cards on 273 of these 300 seeds when written.
        int worse = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] f = TackLedgerIndex.frequencies(seed, 10, 20);
            Filing g = TackLedgerIndex.mostAskedRoot(f);
            Filing b = TackLedgerIndex.best(f);
            assertThat(TackLedgerIndex.flips(f, g.order())).isEqualTo(g.flips());
            assertThat(g.flips()).isGreaterThanOrEqualTo(b.flips());
            if (g.flips() > b.flips()) {
                worse++;
            }
        }
        assertThat(worse).isGreaterThan(200);
    }

    @Test
    void slightlyBusiestCardMakesALopsidedLedger() {
        // Cards asked 3, 3, 4 times. The habit roots card 2 and hangs 0 then 1 below it: 4 + 6 + 9 = 19.
        // Rooting the middle card: 3 + 6 + 8 = 17.
        int[] f = {3, 3, 4};
        assertThat(TackLedgerIndex.mostAskedRoot(f)).isEqualTo(new Filing(19, new int[] {2, 0, 1}));
        assertThat(TackLedgerIndex.best(f)).isEqualTo(new Filing(17, new int[] {1, 0, 2}));
        assertThat(TackLedgerIndex.quest(f, new int[] {2, 0, 1})).isFalse();
        assertThat(TackLedgerIndex.quest(f, new int[] {1, 2, 0})).isTrue();
    }

    @Test
    void badFilingsAreInvalid() {
        int[] f = {1, 2, 3};
        assertThat(TackLedgerIndex.flips(f, new int[] {0, 1, 2})).isEqualTo(1 + 4 + 9);
        assertThat(TackLedgerIndex.flips(f, new int[] {0, 0, 1})).isEqualTo(TackLedgerIndex.INVALID);
        assertThat(TackLedgerIndex.flips(f, new int[] {0, 1})).isEqualTo(TackLedgerIndex.INVALID);
        assertThat(TackLedgerIndex.flips(f, new int[] {0, 1, 3})).isEqualTo(TackLedgerIndex.INVALID);
        assertThat(TackLedgerIndex.best(new int[0]).flips()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(TackLedgerIndex.frequencies(4, 9, 7)).containsExactly(TackLedgerIndex.frequencies(4, 9, 7));
        assertThat(TackLedgerIndex.QUEST_ID).isEqualTo("q_quick_ledger");
        assertThatThrownBy(() -> TackLedgerIndex.frequencies(1, -1, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TackLedgerIndex.best(new int[] {1, -2})).isInstanceOf(IllegalArgumentException.class);
    }

    /** Pre-orders of every binary search tree on cards lo..hi-1. */
    private static List<int[]> trees(int lo, int hi) {
        List<int[]> out = new ArrayList<>();
        if (lo >= hi) {
            out.add(new int[0]);
            return out;
        }
        for (int r = lo; r < hi; r++) {
            for (int[] left : trees(lo, r)) {
                for (int[] right : trees(r + 1, hi)) {
                    int[] t = new int[hi - lo];
                    t[0] = r;
                    System.arraycopy(left, 0, t, 1, left.length);
                    System.arraycopy(right, 0, t, 1 + left.length, right.length);
                    out.add(t);
                }
            }
        }
        return out;
    }
}
