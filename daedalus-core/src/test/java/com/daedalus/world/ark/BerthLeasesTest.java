// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BerthLeasesTest {

    /** Brute force: a plain list of {id, from, to}. */
    private static List<Integer> bruteStab(List<long[]> ls, long x) {
        List<Integer> out = new ArrayList<>();
        for (long[] l : ls) {
            if (l[1] <= x && x <= l[2]) {
                out.add((int) l[0]);
            }
        }
        out.sort(null);
        return out;
    }

    private static boolean bruteClash(List<long[]> ls, long f, long t) {
        for (long[] l : ls) {
            if (l[1] <= t && l[2] >= f) {
                return true;
            }
        }
        return false;
    }

    @Test
    void smallLedgerAnswersByHand() {
        BerthLeases b = new BerthLeases(1L);
        b.add(1, 0, 5);
        b.add(2, 3, 9);
        b.add(3, 10, 12);
        assertThat(b.stab(4)).containsExactly(1, 2);
        assertThat(b.quest(10)).isEqualTo(1);
        assertThat(b.clash(13, 20)).isEmpty();
        assertThat(b.clash(9, 10).isPresent()).isTrue();
        assertThat(b.remove(2, 3)).isTrue();
        assertThat(b.remove(2, 3)).isFalse();
        assertThat(b.stab(7)).isEmpty();
        assertThat(b.size()).isEqualTo(2);
    }

    @Test
    void randomOpsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(524L);
        for (int round = 0; round < 30; round++) {
            BerthLeases b = new BerthLeases(round);
            List<long[]> ls = new ArrayList<>();
            int next = 0;
            for (int op = 0; op < 400; op++) {
                int kind = r.nextInt(4);
                if (kind == 0 || ls.isEmpty()) {
                    long f = r.nextInt(60);
                    long t = f + r.nextInt(15);
                    b.add(next, f, t);
                    ls.add(new long[] {next, f, t});
                    next++;
                } else if (kind == 1) {
                    long[] l = ls.remove(r.nextInt(ls.size()));
                    assertThat(b.remove((int) l[0], l[1])).isTrue();
                } else if (kind == 2) {
                    long x = r.nextInt(80) - 5;
                    assertThat(b.stab(x)).isEqualTo(bruteStab(ls, x));
                } else {
                    long f = r.nextInt(80) - 5;
                    long t = f + r.nextInt(6);
                    var c = b.clash(f, t);
                    assertThat(c.isPresent()).isEqualTo(bruteClash(ls, f, t));
                    if (c.isPresent()) {
                        long[] hit = ls.stream().filter(l -> l[0] == c.getAsInt()).findFirst().orElseThrow();
                        assertThat(hit[1] <= t && hit[2] >= f).isTrue();
                    }
                }
                assertThat(b.size()).isEqualTo(ls.size());
            }
        }
    }

    @Test
    void largeLedgerStaysFast() {
        BerthLeases b = new BerthLeases(7L);
        int n = 200_000;
        for (int i = 0; i < n; i++) {
            b.add(i, 2L * i, 2L * i + 1);
        }
        assertThat(b.countAt(2L * 1234 + 1)).isEqualTo(1);
        assertThat(b.clash(-10, -1)).isEmpty();
        assertThat(b.clash(2L * n + 5, 2L * n + 9)).isEmpty();
        for (int i = 0; i < n; i += 2) {
            assertThat(b.remove(i, 2L * i)).isTrue();
        }
        assertThat(b.size()).isEqualTo(n / 2);
        assertThat(b.stab(0)).isEmpty();
        assertThat(b.stab(3)).containsExactly(1);
    }

    @Test
    void badInputIsRejected() {
        BerthLeases b = new BerthLeases(3L);
        b.add(5, 1, 1);
        assertThatThrownBy(() -> b.add(6, 4, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.add(5, 1, 9)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.clash(3, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThat(b.remove(5, 2)).isFalse();
        assertThat(b.stab(1)).containsExactly(5);
    }
}
