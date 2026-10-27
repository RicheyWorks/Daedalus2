// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.goats;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.goats.GoatLeaps.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class GoatLeapsTest {
    /** Brute force: relax every knight leap from every standing ledge until nothing changes. */
    static int brute(GoatLeaps g) {
        int inf = Integer.MAX_VALUE / 2;
        int[][] d = new int[g.rows()][g.cols()];
        for (int[] row : d) {
            java.util.Arrays.fill(row, inf);
        }
        d[0][0] = 0;
        boolean changed = true;
        while (changed) {
            changed = false;
            for (int r = 0; r < g.rows(); r++) {
                for (int c = 0; c < g.cols(); c++) {
                    if (d[r][c] == inf) {
                        continue;
                    }
                    for (int[] l : GoatLeaps.LEAPS) {
                        int nr = r + l[0];
                        int nc = c + l[1];
                        if (nr >= 0 && nc >= 0 && nr < g.rows() && nc < g.cols() && !g.crumbled(nr, nc)
                                && d[r][c] + 1 < d[nr][nc]) {
                            d[nr][nc] = d[r][c] + 1;
                            changed = true;
                        }
                    }
                }
            }
        }
        int end = d[g.rows() - 1][g.cols() - 1];
        return end == inf ? -1 : end;
    }

    /** A 4 by 4 cliff with ledge (1, 2) crumbled: (0,0) to (2,1) to (3,3) is 2 leaps. */
    static GoatLeaps cliff() {
        boolean[][] g = new boolean[4][4];
        g[1][2] = true;
        return new GoatLeaps(g);
    }

    @Test
    void seededCliffIsDeterministic() {
        GoatLeaps a = GoatLeaps.seeded(4);
        GoatLeaps b = GoatLeaps.seeded(4);
        assertEquals(a.rows(), b.rows());
        assertEquals(a.fewest(), b.fewest());
        assertThrows(IllegalArgumentException.class, () -> new GoatLeaps(new boolean[][] {{true, false}}));
        assertEquals(-1, new GoatLeaps(new boolean[2][2]).fewest(), "no knight leap fits a 2 by 2 cliff");
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            GoatLeaps g = GoatLeaps.seeded(seed);
            assertEquals(brute(g), g.fewest(), "BFS == brute relaxation, seed " + seed);
        }
    }

    @Test
    void knownCliff() {
        assertEquals(2, cliff().fewest());
        assertEquals(4, new GoatLeaps(new boolean[3][3]).fewest(), "a 3 by 3 corner to corner takes 4");
    }

    @Test
    void crumbledLedgeEarnsNoCredit() {
        GoatLeaps g = cliff();
        g.spot("s");
        assertEquals(Outcome.FELL, g.leap("l1", List.of(new int[] {1, 2}, new int[] {3, 3})));
        assertEquals(KeeperGoatLines.FELL, g.talk("t1"));
        assertEquals("leap", g.quest().currentStep().type(), "no credit for a fall");
    }

    @Test
    void guards() {
        GoatLeaps g = cliff();
        assertEquals(Outcome.IGNORED, g.leap("", List.of()));
        assertEquals(Outcome.NOT_THERE, g.leap("e0", List.of(new int[] {1, 1})));
        assertEquals(Outcome.NOT_THERE, g.leap("e0", List.of(new int[] {-1, 2})));
        assertEquals(Outcome.STRAY, g.leap("e1", List.of(new int[] {2, 1})));
        assertEquals(KeeperGoatLines.STRAY, g.talk("t"));
        assertEquals(Outcome.DUPLICATE, g.leap("e1", List.of(new int[] {2, 1}, new int[] {3, 3})));
    }

    @Test
    void questLongThenWellThenKeeper() {
        GoatLeaps g = cliff();
        assertEquals(String.format(KeeperGoatLines.GREETING, 4, 4), g.talk("t0"));
        g.spot("s0");
        assertEquals(Outcome.LONG, g.leap("l1",
                List.of(new int[] {2, 1}, new int[] {0, 0}, new int[] {2, 1}, new int[] {3, 3})));
        assertEquals(String.format(KeeperGoatLines.LONG, 4, 2), g.talk("t1"));
        assertEquals(Outcome.WELL, g.leap("l2", List.of(new int[] {2, 1}, new int[] {3, 3})));
        assertEquals(KeeperGoatLines.THANKS, g.talk("t2"));
        assertNull(g.quest().currentStep());
        assertEquals(KeeperGoatLines.DONE, g.talk("t3"));
    }
}
