// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class TallyBoardTest {

    private static int naiveFirst(long[] a, long target) {
        if (target <= 0) {
            return 0;
        }
        long s = 0;
        for (int i = 0; i < a.length; i++) {
            s += a[i];
            if (s >= target) {
                return i;
            }
        }
        return -1;
    }

    @Test
    void matchesNaiveUnderRandomOps() {
        SplittableRandom rnd = new SplittableRandom(279);
        for (int round = 0; round < 200; round++) {
            int n = rnd.nextInt(1, 70);
            long[] a = new long[n];
            for (int i = 0; i < n; i++) {
                a[i] = rnd.nextInt(0, 50);
            }
            TallyBoard b = rnd.nextBoolean() ? TallyBoard.of(a) : fromAdds(a);
            for (int op = 0; op < 300; op++) {
                int i = rnd.nextInt(n);
                long d = rnd.nextInt(-a[i] > -20 ? (int) -a[i] : -20, 21);
                b.add(i, d);
                a[i] += d;
                int lo = rnd.nextInt(n + 1);
                int hi = rnd.nextInt(lo, n + 1);
                long s = 0;
                for (int k = lo; k < hi; k++) {
                    s += a[k];
                }
                assertThat(b.range(lo, hi)).isEqualTo(s);
                long target = rnd.nextLong(-2, b.total() + 5);
                assertThat(b.firstReaching(target)).as("target=%d", target).isEqualTo(naiveFirst(a, target));
                assertThat(b.get(i)).isEqualTo(a[i]);
            }
        }
    }

    private static TallyBoard fromAdds(long[] a) {
        TallyBoard b = new TallyBoard(a.length);
        for (int i = 0; i < a.length; i++) {
            b.add(i, a[i]);
        }
        return b;
    }

    @Test
    void questAndSmallCases() {
        long[] stores = {3, 0, 4, 1, 0, 5};
        assertThat(TallyBoard.quest(stores, 7, 2)).isTrue();
        assertThat(TallyBoard.quest(stores, 8, 3)).isTrue();
        assertThat(TallyBoard.quest(stores, 8, 4)).isFalse();
        assertThat(TallyBoard.of(stores).firstReaching(14)).isEqualTo(-1);
        assertThat(TallyBoard.of(stores).total()).isEqualTo(13);
        assertThat(TallyBoard.QUEST_ID).isEqualTo("q_tally_board");
    }

    @Test
    void bounds() {
        TallyBoard b = TallyBoard.of(new long[] {1, 2});
        assertThatThrownBy(() -> new TallyBoard(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.add(0, -2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.add(2, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.prefix(3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.range(2, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TallyBoard.of(new long[] {1, -1})).isInstanceOf(IllegalArgumentException.class);
    }
}